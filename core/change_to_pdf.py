"""Chuyển file văn bản/bảng/slide (docx, doc, xlsx, pptx, odt, rtf, txt...) sang PDF.
Nhận path -> trả về path file PDF."""
import os
import shutil
import subprocess

SUPPORTED_EXTS = {
    ".doc", ".docx", ".odt", ".rtf", ".txt",
    ".xls", ".xlsx", ".xlsm", ".ods", ".csv",
    ".ppt", ".pptx", ".odp",
}

_WIN_SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for p in _WIN_SOFFICE_PATHS:
        if os.path.exists(p):
            return p
    return None


def _convert_with_libreoffice(src: str, out_dir: str) -> None:
    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError("Không tìm thấy LibreOffice (soffice).")
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, src],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice lỗi: {result.stderr or result.stdout}")


def _convert_with_word(src: str, dst: str) -> None:
    from docx2pdf import convert  # chỉ chạy được trên máy có Microsoft Word
    convert(src, dst)


def convert_to_pdf(input_path: str, output_dir: str | None = None) -> str:
    """
    Chuyển file sang PDF, trả về đường dẫn file PDF.
    - output_dir=None: lưu cạnh file gốc (VD: D:\\jd.docx -> D:\\jd.pdf).
    - File đã là .pdf: trả về nguyên path, không làm gì.
    """
    input_path = os.path.abspath(input_path)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Không tìm thấy file: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".pdf":
        return input_path
    if ext not in SUPPORTED_EXTS:
        raise ValueError(f"Định dạng '{ext}' chưa hỗ trợ. Hỗ trợ: {sorted(SUPPORTED_EXTS)}")

    out_dir = os.path.abspath(output_dir or os.path.dirname(input_path))
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, os.path.splitext(os.path.basename(input_path))[0] + ".pdf")

    errors = []
    try:
        _convert_with_libreoffice(input_path, out_dir)
    except Exception as e:
        errors.append(f"LibreOffice: {e}")
        # Fallback: Word (chỉ cho doc/docx)
        if ext in (".doc", ".docx"):
            try:
                _convert_with_word(input_path, pdf_path)
            except Exception as e2:
                errors.append(f"docx2pdf/Word: {e2}")

    if not os.path.exists(pdf_path):
        raise RuntimeError("Chuyển PDF thất bại:\n" + "\n".join(errors))
    return pdf_path


if __name__ == "__main__":
    print(convert_to_pdf(r"D:\jd.docx"))