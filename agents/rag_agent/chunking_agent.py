"""
ChunkingAgent - indexing tài liệu (cv / jd / company / policy / knowledge).

Một lượt LLM cho mỗi phần context (đã rút gọn, có số dòng gốc [Lxxx]):
  0. Code : build_numbered_lines -> split_into_parts (cắt ở cuối đoạn / trước heading)
  1. LLM  : mỗi phần -> headings + chunks (start/end line + metadata từng chunk)
  2. Code : kiểm tra (phủ kín, không chồng lấn, cờ nối phần). Sai thì gọi lại kèm
            lỗi cụ thể (reflection nhẹ bằng code, không tốn thêm lần gọi LLM phê bình).
            Nối chunk dang dở qua ranh giới phần.
  3. Code : gộp chunk quá ngắn, cắt TEXT GỐC theo start_line/end_line, gộp metadata
            cấp tài liệu, ghép IndexedDocument.

LLM được tiêm vào qua `llm_call(system_prompt, user_prompt, schema) -> instance của schema`
(xem llm_adapter.make_llm_call để dùng LLMClient của core/llm.py).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from pydantic import BaseModel

from prompts.indexing.chunking_prompts import build_system_prompt, build_user_prompt
from rag.chunking.context_builder import ContextPart, build_numbered_lines, split_into_parts
from core.state_indexing import (
    DOC_TYPES,
    PART_RESULT_MODELS,
    Chunk,
    ChunkingState,
    IndexedDocument,
)

LLMCall = Callable[[str, str, type], BaseModel]


class ChunkingError(RuntimeError):
    pass


@dataclass
class ChunkingConfig:
    max_words_per_part: int = 1200   # ngân sách MỀM mỗi phần; phần có thể dài tới (1+slack) lần để cắt ở cuối đoạn
    slack: float = 0.3
    overlap_lines: int = 5           # số dòng cuối phần trước đưa sang làm tham khảo
    min_chunk_words: int = 30        # chunk (text gốc) ngắn hơn bị gộp vào chunk liền kề (0 = tắt)
    max_retries: int = 1             # số lần gọi lại một phần khi kết quả không hợp lệ


# ---------------------------------------------------------------------------
# Kiểm tra kết quả của một phần
# ---------------------------------------------------------------------------

def _ranges(numbers: list) -> str:
    out, start, prev = [], None, None
    for n in numbers:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"L{start}-L{prev}" if start != prev else f"L{start}")
            start = prev = n
    if start is not None:
        out.append(f"L{start}-L{prev}" if start != prev else f"L{start}")
    return ", ".join(out)


def validate_part(result, part: ContextPart, state: ChunkingState, is_last: bool) -> list:
    """Trả về danh sách lỗi (rỗng = hợp lệ)."""
    chunks = result.chunks
    if not chunks:
        return ["chunks đang rỗng, phải phủ kín khối cần chia chunk"]

    errors = []
    valid = part.line_numbers
    covered, prev_end = set(), None
    for i, c in enumerate(chunks, start=1):
        if c.start_line not in valid:
            errors.append(f"chunk {i}: start_line L{c.start_line} không thuộc khối cần chia chunk")
        if c.end_line not in valid:
            errors.append(f"chunk {i}: end_line L{c.end_line} không thuộc khối cần chia chunk")
        if c.end_line < c.start_line:
            errors.append(f"chunk {i}: end_line L{c.end_line} nhỏ hơn start_line L{c.start_line}")
        if prev_end is not None and c.start_line <= prev_end:
            errors.append(f"chunk {i}: chồng lấn hoặc sai thứ tự (start_line L{c.start_line} <= end_line chunk trước L{prev_end})")
        prev_end = c.end_line
        covered |= {n for n in valid if c.start_line <= n <= c.end_line}
        if i > 1 and c.continues_previous_part:
            errors.append(f"chunk {i}: continues_previous_part chỉ được true ở chunk đầu tiên")
        if i < len(chunks) and c.continues_next_part:
            errors.append(f"chunk {i}: continues_next_part chỉ được true ở chunk cuối cùng")

    missing = sorted(valid - covered)
    if missing:
        errors.append(f"các dòng chưa thuộc chunk nào: {_ranges(missing)}")
    if chunks[0].continues_previous_part and state.open_chunk() is None:
        errors.append("chunk đầu có continues_previous_part = true nhưng không có chunk đang mở từ phần trước")
    if is_last and chunks[-1].continues_next_part:
        errors.append("đây là phần cuối, continues_next_part của chunk cuối phải là false")
    return errors


# ---------------------------------------------------------------------------
# Gộp metadata
# ---------------------------------------------------------------------------

def _union(values: list) -> list:
    seen, out = set(), []
    for v in values:
        key = str(v).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(str(v).strip())
    return out


def _empty(value) -> bool:
    return value in (None, "", [])


def _absorb(target, other) -> None:
    """Gộp metadata của chunk `other` vào chunk `target` (dùng khi nối phần / gộp chunk ngắn).
    Giữ title, summary của target (nếu target thiếu thì lấy của other); danh sách thì hợp nhất."""
    target.topics = _union(list(target.topics) + list(other.topics))
    target.keywords = _union(list(target.keywords) + list(other.keywords))
    if _empty(target.summary) and not _empty(other.summary):
        target.summary = other.summary
    for name in type(target.type_fields).model_fields:
        merged = _union(list(getattr(target.type_fields, name)) + list(getattr(other.type_fields, name)))
        setattr(target.type_fields, name, merged)
    for name in type(target.doc_fields).model_fields:
        if _empty(getattr(target.doc_fields, name)) and not _empty(getattr(other.doc_fields, name)):
            setattr(target.doc_fields, name, getattr(other.doc_fields, name))


def _merge_part(state: ChunkingState, result) -> None:
    for i, c in enumerate(result.chunks):
        c = c.model_copy(deep=True)
        state.doc_observations.append(c.doc_fields.model_dump())
        open_chunk = state.open_chunk() if i == 0 else None
        if i == 0 and c.continues_previous_part and open_chunk is not None:
            open_chunk.end_line = c.end_line
            open_chunk.continues_next_part = c.continues_next_part
            _absorb(open_chunk, c)
            continue
        c.continues_previous_part = False
        state.spans.append(c)


def run_chunking_pass(parts: list, state: ChunkingState, llm_call: LLMCall, cfg: ChunkingConfig) -> None:
    system = build_system_prompt(state.doc_type)
    schema = PART_RESULT_MODELS[state.doc_type]
    for part in parts:
        state.part_index = part.index
        is_last = part.index == len(parts) - 1
        error = ""
        for _attempt in range(cfg.max_retries + 1):
            user = build_user_prompt(
                state.doc_type, state.doc_id, part.index, len(parts), part.render(),
                open_chunk=state.open_chunk(),
                last_heading_path=state.last_heading_path(),
                retry_error=error,
            )
            result = llm_call(system, user, schema)
            errors = validate_part(result, part, state, is_last)
            if not errors:
                break
            error = "; ".join(errors)
        else:
            raise ChunkingError(
                f"Phần {part.index + 1}/{len(parts)} của '{state.doc_id}' không hợp lệ sau "
                f"{cfg.max_retries + 1} lần thử: {error}"
            )
        _merge_part(state, result)
    for span in state.spans:
        span.continues_previous_part = False
        span.continues_next_part = False


# ---------------------------------------------------------------------------
# Cắt text gốc + gộp chunk ngắn
# ---------------------------------------------------------------------------

def cut_text(raw_lines: list, span) -> str:
    return "\n".join(raw_lines[span.start_line - 1:span.end_line]).strip()


def merge_short_spans(spans: list, raw_lines: list, min_words: int) -> list:
    """Gộp chunk có text gốc ngắn hơn min_words vào chunk liền trước (chunk đầu ngắn thì vào chunk sau)."""
    if min_words <= 0 or len(spans) < 2:
        return spans

    def words(s) -> int:
        return len(cut_text(raw_lines, s).split())

    out = []
    for s in spans:
        if out and words(s) < min_words:
            out[-1].end_line = s.end_line
            _absorb(out[-1], s)
            continue
        out.append(s)
    if len(out) > 1 and words(out[0]) < min_words:
        first = out.pop(0)
        out[0].start_line = first.start_line
        _absorb(out[0], first)
    return out


# ---------------------------------------------------------------------------
# Ghép kết quả cuối
# ---------------------------------------------------------------------------

def assemble(state: ChunkingState, spans: list, raw_lines: list, doc_type: str, doc_id: str):
    """Trả về (chunks, doc_metadata)."""
    model = PART_RESULT_MODELS[doc_type]
    chunk_model = model.model_fields["chunks"].annotation.__args__[0]
    doc_field_names = list(chunk_model.model_fields["doc_fields"].annotation.model_fields)
    type_field_names = list(chunk_model.model_fields["type_fields"].annotation.model_fields)

    chunks = []
    for idx, span in enumerate(spans, start=1):
        title = span.title or (span.heading_path[-1] if span.heading_path else None)
        meta = {"title": title, "topics": list(span.topics), "keywords": list(span.keywords), "summary": span.summary}
        meta.update(span.type_fields.model_dump())
        chunks.append(Chunk(
            chunk_id=f"{doc_id}#c{idx:03d}", doc_id=doc_id, doc_type=doc_type,
            start_line=span.start_line, end_line=span.end_line,
            heading_path=list(span.heading_path), text=cut_text(raw_lines, span), metadata=meta,
        ))

    scalars = {}
    for obs_idx, obs in enumerate(state.doc_observations, start=1):
        for name, value in obs.items():
            if _empty(value):
                continue
            if name not in scalars:
                scalars[name] = value
            elif scalars[name] != value:
                state.warnings.append(
                    f"Trường tài liệu '{name}' có giá trị khác nhau giữa các chunk: giữ '{scalars[name]}', "
                    f"bỏ '{value}' (chunk quan sát thứ {obs_idx})."
                )
    doc_meta = {"document_type": doc_type}
    for name in doc_field_names:
        doc_meta[name] = scalars.get(name)
    doc_meta["topics"] = _union([t for s in spans for t in s.topics])
    doc_meta["keywords"] = _union([k for s in spans for k in s.keywords])
    for name in type_field_names:
        doc_meta[name] = _union([v for s in spans for v in getattr(s.type_fields, name)])
    return chunks, doc_meta


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def index_document(content: str, doc_type: str, doc_id: str, llm_call: LLMCall,
                   source_file: Optional[str] = None,
                   config: Optional[ChunkingConfig] = None) -> IndexedDocument:
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type không hợp lệ: {doc_type}. Chọn một trong {DOC_TYPES}")
    cfg = config or ChunkingConfig()

    raw_lines = content.splitlines()
    numbered = build_numbered_lines(content)
    parts = split_into_parts(numbered, max_words=cfg.max_words_per_part,
                             overlap_lines=cfg.overlap_lines, raw_lines=raw_lines, slack=cfg.slack)
    if not parts:
        raise ChunkingError(f"Tài liệu '{doc_id}' rỗng, không có gì để chia chunk.")

    state = ChunkingState(doc_id=doc_id, doc_type=doc_type, total_parts=len(parts))
    run_chunking_pass(parts, state, llm_call, cfg)

    spans = merge_short_spans(state.spans, raw_lines, cfg.min_chunk_words)
    chunks, doc_meta = assemble(state, spans, raw_lines, doc_type, doc_id)

    return IndexedDocument(doc_id=doc_id, doc_type=doc_type, source_file=source_file,
                           metadata=doc_meta, chunks=chunks, warnings=state.warnings)


def index_file(path: str, doc_type: str, llm_call: LLMCall,
               config: Optional[ChunkingConfig] = None) -> IndexedDocument:
    p = Path(path)
    content = p.read_text(encoding="utf-8", errors="ignore")
    return index_document(content, doc_type, doc_id=p.stem, llm_call=llm_call,
                          source_file=str(p), config=config)
