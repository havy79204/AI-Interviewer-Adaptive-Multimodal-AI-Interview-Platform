import os
import re
from pathlib import Path


# ==============================================================================
# 1. HÀM ĐỌC NỘI DUNG (GIỮ NGUYÊN SỐ TRANG & CẤU TRÚC GỐC)
# ==============================================================================
def read_content_preserve_structure(file_path: Path) -> str:
    """Đọc file DOCX, PDF, MD mà KHÔNG làm mất ký tự Markdown (#, **),

    đồng thời gắn thẻ số trang rõ ràng đối với PDF.
    """
    suffix = file_path.suffix.lower()

    if suffix in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif suffix == ".docx":
        try:
            import docx

            doc = docx.Document(file_path)
            full_blocks = []

            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue

                style_name = p.style.name.lower() if p.style else ""
                if "heading 1" in style_name:
                    full_blocks.append(f"\n# {text}\n")
                elif "heading 2" in style_name:
                    full_blocks.append(f"\n## {text}\n")
                elif "heading 3" in style_name:
                    full_blocks.append(f"\n### {text}\n")
                else:
                    full_blocks.append(text)

            for table in doc.tables:
                table_lines = []
                for row_idx, row in enumerate(table.rows):
                    row_cells = [
                        cell.text.strip().replace("\n", " ") for cell in row.cells
                    ]
                    line = "| " + " | ".join(row_cells) + " |"
                    table_lines.append(line)
                    if row_idx == 0:
                        separator = (
                            "| " + " | ".join(["---"] * len(row_cells)) + " |"
                        )
                        table_lines.append(separator)
                if table_lines:
                    full_blocks.append("\n" + "\n".join(table_lines) + "\n")

            return "\n\n".join(full_blocks)

        except ImportError:
            raise ImportError(
                "Thiếu thư viện python-docx! Chạy: pip install python-docx"
            )

    elif suffix == ".pdf":
        try:
            import pdfplumber

            pages_content = []
            with pdfplumber.open(str(file_path)) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(
                        layout=False, x_tolerance=2, y_tolerance=2
                    )
                    if text and text.strip():
                        page_block = (
                            f"\n\n<!-- Page {idx} -->\n\n{text.strip()}"
                        )
                        pages_content.append(page_block)

            return "\n\n".join(pages_content)

        except ImportError:
            raise ImportError(
                "Thiếu thư viện pdfplumber! Chạy: pip install pdfplumber"
            )

    else:
        raise ValueError(f"Định dạng chưa hỗ trợ: {suffix}")


def clean_filename(text: str) -> str:
    """Làm sạch ký tự cấm trên Windows, giữ Unicode tiếng Việt chuẩn."""
    text = re.sub(r'[\\/*?:"<>|#\n\r]', "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:80]


# ==============================================================================
# 2. HÀM CHUẨN HÓA VÀ TÁI CÂN BẰNG CẤP BẬC HEADING (# -> ## -> ###)
# ==============================================================================
ROOT_SECTIONS = [
    # CV
    "tóm tắt",
    "mục tiêu",
    "kinh nghiệm",
    "học vấn",
    "kỹ năng",
    "dự án",
    "chứng chỉ",
    "thành tích",
    "giải thưởng",
    "hoạt động",
    "summary",
    "objective",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
    # JD
    "mô tả công việc",
    "yêu cầu",
    "quyền lợi",
    "phúc lợi",
    "trách nhiệm",
    "responsibilities",
    "requirements",
    "qualifications",
    "benefits",
    # Knowledge / Company
    "định vị",
    "hệ sinh thái",
    "nhiệm vụ",
    "quy chế",
    "điều",
    "mục",
    "phần",
]


def clean_heading_text(line: str) -> str:
    """Lấy nội dung chữ thuần của heading, bỏ hết # và ** thừa."""
    text = re.sub(r"^#+\s*", "", line)
    text = re.sub(r"^\*\*|\*\*$", "", text)
    return text.strip()


def repair_and_balance_headings(md_content: str, doc_type: str = "cv") -> str:
    """Chuẩn hóa cấp bậc heading:

    - Tiêu đề file/tên ứng viên/mã -> # (H1)
    - Mục lớn (Kinh nghiệm, Yêu cầu...) -> ## (H2)
    - Tiểu mục (Công ty, Dự án, Nhóm kỹ năng...) -> ### (H3)
    - Tự động sửa lỗi nhảy cóc level (ví dụ H1 nhảy thẳng xuống H4).
    """
    lines = md_content.split("\n")
    fixed_lines = []

    current_level = 0
    has_h1 = False

    for line in lines:
        stripped = line.strip()

        # Giữ nguyên comment số trang, bảng, danh sách bullet, code block
        if (
            not stripped
            or stripped.startswith(("<!-- Page", "```", "|", "*", "-", "+"))
        ):
            fixed_lines.append(line)
            continue

        is_explicit_heading = stripped.startswith("#")
        core_text = clean_heading_text(stripped)
        core_clean = re.sub(r"[^\w\s]", "", core_text.lower()).strip()

        target_level = None

        # 1. H1 (#): Tiêu đề đầu tiên hoặc chứa mã [CV, [JD, [TÀI LIỆU, [DOC
        if not has_h1 and (
            re.search(r"\[(CV|JD|TÀI LIỆU|DOC)", core_text, re.I)
            or (is_explicit_heading and current_level == 0)
        ):
            target_level = 1
            has_h1 = True

        # 2. H2 (##): Mục lớn khớp từ khóa
        elif (
            any(kw in core_clean for kw in ROOT_SECTIONS)
            and len(core_text.split()) <= 8
        ):
            target_level = 2

        # 3. H2 (##): Có tiền tố La Mã (I., II.), Điều, Mục, Emoji
        elif re.match(
            r"^((\d+[\.\/])|([IVXLCDM]+[\.\:])|((Điều|Mục|Phần)\s+\d+[\.\:]?)|[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf])\s*",
            core_text,
            re.IGNORECASE,
        ):
            target_level = 2

        # 4. H3 (###): Đã có dấu # trước đó hoặc là dòng in đậm ngắn độc lập
        elif is_explicit_heading:
            raw_level = len(re.match(r"^#+", stripped).group(0))
            target_level = 2 if (raw_level == 1 and has_h1) else raw_level
        elif (
            stripped.startswith("**")
            and stripped.endswith("**")
            and len(core_text.split()) <= 10
            and not core_text.endswith((".", ";"))
        ):
            target_level = 3
        elif (
            core_text.isupper()
            and len(core_text.split()) <= 7
            and not core_text.endswith((".", ";"))
        ):
            target_level = 3

        # Áp dụng quy tắc chống nhảy cóc (Hierarchy Re-balancing)
        if target_level is not None:
            if target_level > current_level + 1 and current_level > 0:
                target_level = current_level + 1

            current_level = target_level
            heading_prefix = "#" * target_level
            fixed_lines.append(f"\n{heading_prefix} {core_text}\n")
        else:
            fixed_lines.append(line)

    result = "\n".join(fixed_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ==============================================================================
# 3. TÁCH FILE VÀ LƯU VÀO THƯ MỤC CHUẨN RAG
# ==============================================================================
def split_composite_file(
    input_file_path: str,
    output_dir: str,
    tag_prefix: str,
    doc_type: str,
    extension: str = "md",
):
    input_path = Path(input_file_path)
    output_path = Path(output_dir)

    if not input_path.exists():
        print(f"❌ Không tìm thấy file: {input_path}")
        return []

    output_path.mkdir(parents=True, exist_ok=True)

    # Đọc file bảo tồn định dạng và trang
    raw_content = read_content_preserve_structure(input_path)

    # Tách đoạn theo tag mở đầu
    split_pattern = rf"(?m)(?=^[#*\-\s]*{tag_prefix})"
    chunks = re.split(split_pattern, raw_content)

    created_files = []
    index = 1

    for chunk in chunks:
        chunk = chunk.strip()
        if not re.search(tag_prefix, chunk, re.IGNORECASE):
            continue

        # Chuẩn hóa lại toàn bộ heading (#, ##, ###)
        formatted_md = repair_and_balance_headings(chunk, doc_type=doc_type)

        filename = ""

        # --- Đặt tên file theo loại ---
        if doc_type == "cv":
            name_match = re.search(
                r"\*\*(?:ỨNG VIÊN:?\s*)?([^*]+)\*\*", formatted_md
            )
            if not name_match:
                lines = [
                    l.strip() for l in formatted_md.split("\n") if l.strip()
                ]
                for l in lines[:7]:
                    l_clean = clean_heading_text(l)
                    if (
                        re.search(r"^[A-ZÀ-Ỹ\s]{4,}$", l_clean)
                        and "ỨNG TUYỂN" not in l_clean
                    ):
                        name_match = re.search(r"^([A-ZÀ-Ỹ\s]+)$", l_clean)
                        break

            if name_match:
                cand_name = clean_filename(name_match.group(1))
                filename = f"CV_{cand_name}.{extension}"
            else:
                tag_match = re.search(r"\[CV\s*(\d+)\]", chunk[:120], re.I)
                num = tag_match.group(1) if tag_match else str(index)
                filename = f"CV_UNG_VIEN_{num}.{extension}"

        elif doc_type == "jd":
            first_line = [l for l in formatted_md.split("\n") if l.strip()][0]
            clean_title = re.sub(
                r"^[#*\-\s]*\[JD\s*(\d+)\]\s*:?", r"JD_\1_", first_line, flags=re.I
            )
            clean_title = clean_filename(clean_title)
            filename = (
                f"{clean_title}.{extension}" if clean_title else f"JD_{index}.{extension}"
            )

        elif doc_type == "knowledge":
            first_line = [l for l in formatted_md.split("\n") if l.strip()][0]
            clean_title = re.sub(
                r"^[#*\-\s]*\[TÀI LIỆU\s*(\d+)\]\s*:?",
                r"KNOWLEDGE_\1_",
                first_line,
                flags=re.I,
            )
            clean_title = clean_filename(clean_title)
            filename = (
                f"{clean_title}.{extension}"
                if clean_title
                else f"KNOWLEDGE_{index}.{extension}"
            )

        elif doc_type == "company":
            first_line = [l for l in formatted_md.split("\n") if l.strip()][0]
            clean_title = re.sub(
                r"^[#*\-\s]*\[DOC\s*(\d+)\]\s*:?",
                r"COMPANY_\1_",
                first_line,
                flags=re.I,
            )
            clean_title = clean_filename(clean_title)
            filename = (
                f"{clean_title}.{extension}"
                if clean_title
                else f"COMPANY_{index}.{extension}"
            )

        dest_file = output_path / filename
        with open(dest_file, "w", encoding="utf-8") as f_out:
            f_out.write(formatted_md)

        created_files.append(filename)
        index += 1

    return created_files


def process_all_splits(paths_config: dict, file_extension: str = "md"):
    print("=" * 75)
    print("🚀 BẮT ĐẦU CHIA TÀI LIỆU VÀ CHUẨN HÓA CẤU TRÚC MARKDOWN")
    print("=" * 75)

    summary = {}
    for doc_type, cfg in paths_config.items():
        print(f"\n⏳ Đang xử lý [{doc_type.upper()}] từ file: {cfg['input_file']}")
        files = split_composite_file(
            input_file_path=cfg["input_file"],
            output_dir=cfg["output_folder"],
            tag_prefix=cfg["tag_prefix"],
            doc_type=doc_type,
            extension=file_extension,
        )
        summary[doc_type] = {
            "folder": cfg["output_folder"],
            "count": len(files),
            "sample": files[:3] if files else [],
        }
        print(f"   -> Đã trích xuất {len(files)} files vào: {cfg['output_folder']}")

    print("\n" + "=" * 75)
    print("📊 BÁO CÁO TỔNG KẾT SAU KHI TÁCH")
    print("=" * 75)
    grand_total = 0
    for doc_type, data in summary.items():
        print(f"\n📂 Mục: {doc_type.upper()}")
        print(f"   • Thư mục đích : {data['folder']}")
        print(f"   • Số lượng file: {data['count']}")
        if data["sample"]:
            print(f"   • File mẫu     : {', '.join(data['sample'])}...")
        grand_total += data["count"]

    print("\n" + "-" * 75)
    print(f"✅ TỔNG CỘNG: {grand_total} files Markdown đã được tạo chuẩn xác!")
    print("-" * 75)


# ==============================================================================
# 4. KHỐI CẤU HÌNH PATHS CỦA BẠN
# ==============================================================================
if __name__ == "__main__":
    CONFIG = {
        "cv": {
            "input_file": r"c:\Users\phuoc.mai\Downloads\cv.pdf",
            "output_folder": r"D:\PHUOC\RAI_LLM\RAT_INTERVIEW\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform\rag\indexing\sample_data\cv",
            "tag_prefix": r"\[CV",
        },
        "jd": {
            "input_file": r"c:\Users\phuoc.mai\Downloads\jd.docx",
            "output_folder": r"D:\PHUOC\RAI_LLM\RAT_INTERVIEW\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform\rag\indexing\sample_data\jd",
            "tag_prefix": r"\[JD",
        },
        "knowledge": {
            "input_file": r"c:\Users\phuoc.mai\Downloads\knowledge.pdf",
            "output_folder": r"D:\PHUOC\RAI_LLM\RAT_INTERVIEW\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform\rag\indexing\sample_data\knowledge",
            "tag_prefix": r"\[TÀI LIỆU",
        },
        "company": {
            "input_file": r"c:\Users\phuoc.mai\Downloads\company.docx",
            "output_folder": r"D:\PHUOC\RAI_LLM\RAT_INTERVIEW\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform\rag\indexing\sample_data\company",
            "tag_prefix": r"\[DOC",
        },
    }

    process_all_splits(CONFIG, file_extension="md")