"""
Chạy indexing cho các file .md đã bóc từ PDF.

Cấu trúc thư mục (giống build_all_contexts): <root>/<doc_type>/*.md
  doc_type = tên thư mục: cv | jd | company | policy | knowledge
Bỏ qua file bắt đầu bằng 'context_' (output của context_builder).
Kết quả: <out>/<doc_type>/<tên file>.json

  python run_indexing.py [root] [--out DIR]
  python run_indexing.py [root] --out DIR --local

Chế độ mặc định dùng LLM để tạo metadata; --local tạo chunks/keywords xác định,
không gọi LLM hay embedding.
"""

from collections import Counter
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
import sys


HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agents.rag_agent.chunking_agent import ChunkingConfig, index_file
from core.state_indexing import DOC_TYPES, Chunk, IndexedDocument
from core.llm_adapter import make_llm_call



def index_file_local(
    path: Path,
    doc_type: str,
    *,
    max_words_per_chunk: int = 250,
) -> IndexedDocument:
    """Create deterministic, lexical-only chunks without an LLM or embedding call."""
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type không hợp lệ: {doc_type}. Chọn một trong {DOC_TYPES}")
    if max_words_per_chunk <= 0:
        raise ValueError("max_words_per_chunk phải lớn hơn 0")

    content = path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    if not any(line.strip() for line in lines):
        raise ValueError(f"Tài liệu '{path}' rỗng, không có gì để chia chunk.")

    chunks: list[Chunk] = []
    current_lines: list[tuple[int, str]] = []
    current_words = 0
    heading_stack: list[tuple[int, str]] = []

    def flush() -> None:
        nonlocal current_lines, current_words
        if not current_lines:
            return
        text = "\n".join(line for _, line in current_lines).strip()
        if text:
            tokens = Counter(re.findall(r"[a-z0-9_]{3,}", text.lower()))
            heading_path = [title for _, title in heading_stack]
            title = heading_path[-1] if heading_path else None
            chunks.append(
                Chunk(
                    chunk_id=f"{path.stem}#c{len(chunks) + 1:03d}",
                    doc_id=path.stem,
                    doc_type=doc_type,
                    start_line=current_lines[0][0],
                    end_line=current_lines[-1][0],
                    heading_path=heading_path,
                    text=text,
                    metadata={
                        "title": title,
                        "topics": [],
                        "keywords": [token for token, _ in tokens.most_common(12)],
                        "summary": None,
                    },
                )
            )
        current_lines = []
        current_words = 0

    for line_number, line in enumerate(lines, start=1):
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            heading_stack = [
                (existing_level, title)
                for existing_level, title in heading_stack
                if existing_level < level
            ]
            heading_stack.append((level, heading.group(2).strip()))

        line_words = len(line.split())
        previous_line_is_heading = bool(
            current_lines
            and re.match(r"^\s{0,3}#{1,6}\s+", current_lines[-1][1])
        )
        if (
            current_lines
            and current_words + line_words > max_words_per_chunk
            and not previous_line_is_heading
        ):
            flush()
        current_lines.append((line_number, line))
        current_words += line_words
    flush()

    if not chunks:
        raise ValueError(f"Tài liệu '{path}' không có nội dung để chia chunk.")

    return IndexedDocument(
        doc_id=path.stem,
        doc_type=doc_type,
        source_file=str(path),
        metadata={"language": "und", "indexing_mode": "local_lexical"},
        chunks=chunks,
        warnings=["Local lexical indexing: summaries and semantic metadata were not generated."],
    )


def main():
    default_root = HERE.parent / "documents" / "data_parser"
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=str(default_root))
    ap.add_argument("--out", default=None, help="Thư mục kết quả (mặc định <root>/../indexed)")
    ap.add_argument(
        "--local",
        action="store_true",
        help="Tạo chunks và metadata từ Markdown mà không gọi LLM.",
    )
    ap.add_argument(
        "--chunk-words",
        type=int,
        default=250,
        help="Giới hạn từ mỗi chunk ở chế độ --local (mặc định 250).",
    )
    args = ap.parse_args()

    root = Path(args.root)
    out_root = Path(args.out) if args.out else root.parent / "indexed"
    if not args.local:
        llm_call = make_llm_call()
        cfg = ChunkingConfig()

    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        doc_type = folder.name.lower()
        if doc_type not in DOC_TYPES:
            print(f"[SKIP] thư mục '{folder.name}' không phải doc_type hợp lệ {DOC_TYPES}")
            continue
        for md in sorted(folder.glob("*.md")):
            if md.name.startswith("context_"):
                continue
            try:
                if args.local:
                    doc = index_file_local(md, doc_type, max_words_per_chunk=args.chunk_words)
                else:
                    doc = index_file(str(md), doc_type, llm_call, cfg)
            except Exception as e:
                print(f"[ERR] {doc_type}/{md.name}: {e}")
                continue
            out = out_root / doc_type / f"{md.stem}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            print(f"[OK] {doc_type}/{md.name}: {len(doc.chunks)} chunk, {len(doc.warnings)} cảnh báo -> {out}")


if __name__ == "__main__":
    main()
