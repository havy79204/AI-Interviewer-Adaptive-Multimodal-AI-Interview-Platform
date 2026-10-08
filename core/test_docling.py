import time
import re
from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

def test_docling(input_path: str, output_md_path: str):
    file_path = Path(input_path)
    if not file_path.exists():
        print(f"❌ Không tìm thấy file: {file_path}")
        return

    print("=" * 60)
    print(f"🚀 [DOCLING] Bắt đầu xử lý: {file_path.name}")
    print("=" * 60)

    start_time = time.time()
    
    # 1. Khởi tạo DocumentConverter
    # Docling tự động nhận diện cả .pdf lẫn .docx
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # Tắt OCR vì tài liệu đã có sẵn text layer

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
        
    # 2. Thực hiện convert
    print("⏳ Đang phân tích layout, bảng biểu và heading...")
    result = converter.convert(str(file_path))
    
    # 3. Xuất ra định dạng Markdown
    md_content = result.document.export_to_markdown()
    
    elapsed_time = time.time() - start_time
    
    # 4. Ghi file kết quả
    out_path = Path(output_md_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 5. Đánh giá thống kê nhanh
    h1_count = len(re.findall(r"^#\s+", md_content, re.M))
    h2_count = len(re.findall(r"^##\s+", md_content, re.M))
    h3_count = len(re.findall(r"^###\s+", md_content, re.M))
    table_rows = len(re.findall(r"^\|.*\|$", md_content, re.M))

    print(f"\n✅ [DOCLING] Hoàn thành trong: {elapsed_time:.2f} giây")
    print(f"📁 File kết quả lưu tại: {out_path.resolve()}")
    print("-" * 60)
    print("📊 THỐNG KÊ CẤU TRÚC TRÍCH XUẤT:")
    print(f"   • Heading 1 (#)   : {h1_count}")
    print(f"   • Heading 2 (##)  : {h2_count}")
    print(f"   • Heading 3 (###) : {h3_count}")
    print(f"   • Dòng bảng biểu  : {table_rows} (ước tính ~ {table_rows // 3} bảng)")
    print("=" * 60)

if __name__ == "__main__":
    # Thay đường dẫn file cần test vào đây (PDF hoặc DOCX)
    INPUT_FILE = r"C:/Users/phuoc.mai/Downloads/knowledge.pdf"
    OUTPUT_FILE = r"C:/Users/phuoc.mai/Downloads/output_docling_knowledge.md"
    
    test_docling(INPUT_FILE, OUTPUT_FILE)