import time
import re
from pathlib import Path

def test_marker(input_path: str, output_md_path: str):
    file_path = Path(input_path)
    if not file_path.exists():
        print(f"❌ Không tìm thấy file: {file_path}")
        return

    if file_path.suffix.lower() != ".pdf":
        print(f"⚠️ Marker được thiết kế tối ưu cho PDF. File đầu vào: {file_path.suffix}")

    print("=" * 60)
    print(f"🚀 [MARKER] Bắt đầu xử lý: {file_path.name}")
    print("=" * 60)

    start_time = time.time()

    # 1. Load các model của Marker
    print("⏳ Đang load model Marker (Surya layout, OCR, text detector)...")
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser

    # Khởi tạo converter với config mặc định
    config_parser = ConfigParser({"output_format": "markdown"})
    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer()
    )

    # 2. Xử lý file PDF
    print("⏳ Đang tiến hành bóc tách tài liệu...")
    rendered = converter(str(file_path))
    md_content, _, images = rendered.markdown, rendered.metadata, rendered.images

    elapsed_time = time.time() - start_time

    # 3. Ghi file kết quả
    out_path = Path(output_md_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 4. Đánh giá thống kê nhanh
    h1_count = len(re.findall(r"^#\s+", md_content, re.M))
    h2_count = len(re.findall(r"^##\s+", md_content, re.M))
    h3_count = len(re.findall(r"^###\s+", md_content, re.M))
    table_rows = len(re.findall(r"^\|.*\|$", md_content, re.M))

    print(f"\n✅ [MARKER] Hoàn thành trong: {elapsed_time:.2f} giây")
    print(f"📁 File kết quả lưu tại: {out_path.resolve()}")
    print("-" * 60)
    print("📊 THỐNG KÊ CẤU TRÚC TRÍCH XUẤT:")
    print(f"   • Heading 1 (#)   : {h1_count}")
    print(f"   • Heading 2 (##)  : {h2_count}")
    print(f"   • Heading 3 (###) : {h3_count}")
    print(f"   • Dòng bảng biểu  : {table_rows} (ước tính ~ {table_rows // 3} bảng)")
    print(f"   • Ảnh trích xuất : {len(images)} ảnh")
    print("=" * 60)

if __name__ == "__main__":
    # Thay đường dẫn file cần test vào đây (Chỉ nhận PDF)
    INPUT_FILE = r"C:/Users/phuoc.mai/Downloads/jd.pdf"
    OUTPUT_FILE = r"C:/Users/phuoc.mai/Downloads/output_marker.md"
    
    test_marker(INPUT_FILE, OUTPUT_FILE)