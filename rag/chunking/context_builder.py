import re
from dataclasses import dataclass, field
from pathlib import Path

PREVIEW_WORDS = 7

# =====================================================
# STRUCTURE PATTERNS
# =====================================================

KEEP_PATTERNS = [
    r"^\s*#{1,6}\s*",      # # ##
    r"^\s*\d+\.",          # 1. 2. 3.
    r"^\s*\d+\)",          # 1) 2) 3)
    r"^\s*[a-z]\.",        # a. b. c.
    r"^\s*[a-z]\)",        # a) b) c)
    r"^\s*[A-Z]\.",        # A. B. C.
    r"^\s*[A-Z]\)",        # A) B) C.
    r"^\s*[IVXLCDM]+\.",   # I. II. III.
    r"^\s*[IVXLCDM]+\)",   # I) II) III)
]

# KEEP_PREFIXES = (
#     "📌", "🎯", "💼", "🛠️", "📍", "📚", "⚙️"
# )


#delete file context temp
from pathlib import Path

def cleanup_context_files(root_dir: str) -> None:

    root = Path(root_dir)

    deleted = 0

    for file_path in root.rglob("context_*"):

        if file_path.is_file():
            file_path.unlink()
            deleted += 1

    print(f"Deleted {deleted} context files")

# =====================================================
# FILE IO
# =====================================================

def read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_md(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


# =====================================================
# DETECT STRUCTURE
# =====================================================

def is_structure_line(line: str) -> bool:
    text = line.strip()

    if not text:
        return False

    # if text.startswith(KEEP_PREFIXES):
    #     return True

    if "|" in text:
        return True

    for pattern in KEEP_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    return False



# =====================================================
# SPLIT SENTENCES
# =====================================================

def split_content(content: str) -> list[str]:

    content = re.sub(
        r"(?<!\d)([.;!?])\s+",
        r"\1\n",
        content
    )

    lines = []

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        if re.match(r"^\d+\.\s+", line):

            parts = line.split()

            if len(parts) > 15:
                line = " ".join(parts[:15]) + " ..."

        lines.append(line)

    return lines


# =====================================================
# COMPRESS
# =====================================================

def compress_line(line: str) -> str:

    words = line.split()

    if len(words) <= PREVIEW_WORDS:
        return line

    return " ".join(words[:PREVIEW_WORDS]) + " ..."


# =====================================================
# BUILD CONTEXT
# =====================================================

def build_context(content: str) -> str:

    result = []

    lines = split_content(content)

    for line in lines:

        if is_structure_line(line):
            result.append(line)
            continue

        result.append(
            compress_line(line)
        )

    return "\n".join(result)


# =====================================================
# PROCESS FILE
# =====================================================

def process_file(file_path: Path):

    raw_content = read_md(file_path)

    context = build_context(raw_content)

    output_file = (
        file_path.parent
        / f"context_{file_path.stem}.md"
    )

    write_md(output_file, context)

    return {
        "file_name": file_path.name,
        "context": context,
        "output": str(output_file)
    }


# =====================================================
# PROCESS ALL FOLDERS
# =====================================================

def build_all_contexts(root_dir: str):

    root = Path(root_dir)

    contexts = {}

    for folder in root.iterdir():

        if not folder.is_dir():
            continue

        doc_type = folder.name.lower()
        if doc_type != "cv":
            continue

        contexts[doc_type] = []

        for md_file in folder.glob("*.md"):

            if md_file.stem.endswith("_context"):
                continue

            item = process_file(md_file)

            contexts[doc_type].append(item)

            print(f"[OK] {doc_type}/{md_file.name}")

    return contexts


# =====================================================
# NUMBERED CONTEXT + SPLIT INTO PARTS (dung cho ChunkingAgent)
# =====================================================
# Cac ham o tren (build_context, process_file, ...) GIU NGUYEN.
# Phan nay them 2 viec:
#   1. Gan so dong GOC [Lxxx] vao moi dong da rut gon, de LLM tra ve
#      start_line / end_line va code cat lai TEXT GOC theo so dong do.
#   2. Chia context thanh nhieu phan (theo ngan sach tu) de khong qua dai.
#
# QUAN TRONG: so dong dua tren content.splitlines(). Khi cat text goc phai
# dung dung content.splitlines() cua CUNG chuoi content do.

NumberedLine = tuple  # (so_dong_goc: int, text_da_rut_gon: str)


def build_numbered_lines(content: str) -> list:
    """Rut gon content nhu build_context nhung GIU so dong goc (bat dau tu 1).

    - Dong trong bi bo (so dong co the nhay).
    - Dong bang (co "|") giu nguyen, khong tach cau.
    - Moi dong goc -> dung 1 dong ket qua (cac cau tach boi split_content duoc
      noi lai bang dau cach) de so dong luon khop voi file goc.
    """
    result = []
    for line_no, raw in enumerate(content.splitlines(), start=1):
        text = raw.strip()
        if not text:
            continue
        if "|" in text:
            result.append((line_no, text))
            continue
        kept = []
        for piece in split_content(text):
            kept.append(piece if is_structure_line(piece) else compress_line(piece))
        if kept:
            result.append((line_no, " ".join(kept)))
    return result


def format_numbered_line(line_no: int, text: str) -> str:
    return f"[L{line_no:03d}] {text}"


@dataclass
class ContextPart:
    """Mot phan cua context. `body` la phan LLM phai chia chunk; `reference`
    la vai dong cuoi cua phan truoc, chi de LLM hieu mach van."""
    index: int
    body: list
    reference: list = field(default_factory=list)

    @property
    def first_line(self) -> int:
        return self.body[0][0]

    @property
    def last_line(self) -> int:
        return self.body[-1][0]

    @property
    def line_numbers(self) -> set:
        return {no for no, _ in self.body}

    def render(self) -> str:
        out = []
        if self.reference:
            out.append("[THAM KHẢO - KHÔNG TẠO CHUNK]")
            out.extend(format_numbered_line(no, t) for no, t in self.reference)
            out.append("[HẾT THAM KHẢO]")
            out.append("")
        out.append("[NỘI DUNG CẦN CHIA CHUNK]")
        out.extend(format_numbered_line(no, t) for no, t in self.body)
        return "\n".join(out)


def _word_count(text: str) -> int:
    return len(text.split()) + 1  # +1 cho tien to [Lxxx]


def _is_table_line(text: str) -> bool:
    return "|" in text


def _is_heading_like(text: str) -> bool:
    return is_structure_line(text) and not _is_table_line(text)


_SENTENCE_END = (".", "!", "?", ";", ":", "。", "！", "？", "…")


def _ends_cleanly(raw_text: str) -> bool:
    """Dong nay co ket thuc 'tron cau/tron y' khong? (de khong cat giua cau khi
    PDF xuong dong giua cau). Dong ngan, dong cau truc, dong bang coi la tron."""
    t = raw_text.rstrip()
    if not t:
        return True
    if t[-1] in _SENTENCE_END:
        return True
    return len(t.split()) <= PREVIEW_WORDS or is_structure_line(t)


def _cut_rank(lines: list, i: int, raw_lines=None):
    """Diem cat TRUOC lines[i]. Tra ve None neu khong an toan, nguoc lai:
    2 = ngay truoc heading, 1 = het doan (co dong trong), 0 = het cau."""
    prev_no, prev_text = lines[i - 1]
    no, text = lines[i]
    if _is_table_line(prev_text) and _is_table_line(text):
        return None                      # khong cat giua bang
    if _is_heading_like(text):
        return 2
    if no - prev_no > 1:
        return 1                         # co dong trong giua 2 dong -> het doan
    prev_raw = raw_lines[prev_no - 1] if raw_lines else prev_text
    return 0 if _ends_cleanly(prev_raw) else None


def split_into_parts(lines: list, max_words: int = 1200, overlap_lines: int = 5,
                     raw_lines=None, slack: float = 0.3) -> list:
    """Chia thanh cac ContextPart. max_words la ngan sach MEM: phan co the dai toi
    max_words * (1 + slack) de cat o cho het doan / truoc heading, thay vi cat
    cung theo so tu. Khong bao gio cat giua bang, khong cat giua cau (neu co
    raw_lines de kiem tra dong ket thuc).

    Uu tien diem cat: truoc heading (2) > het doan (1) > het cau (0); cung hang
    thi chon diem gan ngan sach nhat. Neu khong co diem cat hop le (VD: bang rat dai)
    thi keo dai toi da 2x ngan sach, het cach moi cat cung tai ngan sach."""
    n = len(lines)
    wc = [_word_count(t) for _, t in lines]
    parts = []
    start = 0
    while start < n:
        end, words = start, 0
        while end < n and (end == start or words + wc[end] <= max_words):
            words += wc[end]
            end += 1

        cut = end
        if end < n:
            hard, w = end, words
            while hard < n and w + wc[hard] <= max_words * (1 + slack):
                w += wc[hard]
                hard += 1
            if hard >= n:
                cut = n                  # phan con lai vua trong gioi han mem
            else:
                floor = start + max(1, (end - start) // 2)
                best = None
                for i in range(floor, hard + 1):
                    if i >= n:
                        break
                    rank = _cut_rank(lines, i, raw_lines)
                    if rank is None:
                        continue
                    key = (rank, -abs(i - end))
                    if best is None or key > best[0]:
                        best = (key, i)
                if best is not None:
                    cut = best[1]
                else:
                    # Dang o giua bang dai (hoac khong co diem cat hop le trong cua so):
                    # keo dai ra phia sau toi diem cat an toan dau tien, toi da 2x ngan sach.
                    w2 = w
                    for i in range(hard + 1, n + 1):
                        w2 += wc[i - 1]
                        if w2 > max_words * 2:
                            break
                        if i == n or _cut_rank(lines, i, raw_lines) is not None:
                            cut = i
                            break

        reference = lines[max(0, start - overlap_lines):start] if parts else []
        parts.append(ContextPart(index=len(parts), body=lines[start:cut], reference=reference))
        start = cut
    return parts


# =====================================================
# TEST
# =====================================================

# if __name__ == "__main__":



#     ROOT = (
#         Path(__file__)
#         .resolve()
#         .parents[1]
#         / "documents"
#         / "data_parser"
#     )
#     cleanup_context_files(str(ROOT))

#     print( "root : ", ROOT)
#     data = build_all_contexts(str(ROOT))

#     print("\n========== SUMMARY ==========")

#     for k, v in data.items():
#         print(f"{k}: {len(v)} files")