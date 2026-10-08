"""
State + schema cho ChunkingAgent (indexing CV / JD / Company / Policy / Knowledge).

MỘT lượt LLM cho mỗi phần (part) context ĐÃ RÚT GỌN:
  vị trí chunk (start_line/end_line/heading_path) + metadata của từng chunk
  -> PART_RESULT_MODELS[doc_type]

Docstring + Field(description=...) của các class LLM-output là NỘI DUNG HƯỚNG DẪN
cho LLM: describe_schema() render chúng thành text để nhúng vào prompt, nên viết
kỹ như viết prompt. Các field đánh dấu [TRÍCH] là lấy nguyên văn từ text nhìn thấy;
[SINH] là do LLM tổng hợp.

Metadata 2 cấp:
  - Tài liệu (gộp bằng code): CommonDocFields + <Type>DocFields
  - Chunk (mỗi chunk): ChunkMetadataBase + <Type>ChunkFields
Các trường tham khảo do bạn cung cấp là nguồn chọn trường, không bắt buộc.
"""
import inspect
import types
from typing import Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field, create_model

DocType = Literal["cv", "jd", "company", "policy", "knowledge"]
DOC_TYPES = ("cv", "jd", "company", "policy", "knowledge")


# ---------------------------------------------------------------------------
# Heading + ranh giới chunk (một phần của output LLM)
# ---------------------------------------------------------------------------

class HeadingNode(BaseModel):
    """Một dòng bạn xác định là HEADING (tiêu đề mục) trong khối [NỘI DUNG CẦN CHIA CHUNK]."""
    line: int = Field(description="Số dòng gốc (chỉ lấy số, bỏ chữ L và số 0 đầu). Phải là số có trong input.")
    level: int = Field(ge=1, le=6, description="Cấp heading: 1 = cao nhất. Theo quan hệ lồng nhau thực tế trong tài liệu, không theo ký hiệu tuyệt đối.")
    title: str = Field(description="Văn bản heading như thấy trong input, bỏ tiền tố [Lxxx]. Không viết lại.")


class ChunkSpan(BaseModel):
    """Ranh giới của MỘT chunk. Chunk = heading lá (cấp sâu nhất) + nội dung của nó."""
    start_line: int = Field(description="Số dòng gốc đầu tiên của chunk (bao gồm dòng heading của chunk).")
    end_line: int = Field(description="Số dòng gốc cuối cùng của chunk. Phải có mặt trong khối cần chia chunk.")
    heading_path: list[str] = Field(
        default_factory=list,
        description="Chuỗi heading từ cha đến con chứa chunk này, ví dụ ['I. KINH NGHIỆM', '1. Công ty ABC']. "
                    "Để [] nếu chunk nằm trước heading đầu tiên của tài liệu.",
    )
    continues_previous_part: bool = Field(
        default=False,
        description="True CHỈ KHI đây là chunk đầu tiên và nó là phần tiếp nối của chunk đang mở từ phần trước.",
    )
    continues_next_part: bool = Field(
        default=False,
        description="True CHỈ KHI đây là chunk cuối cùng và nội dung của nó chưa kết thúc ở cuối phần này.",
    )


# ---------------------------------------------------------------------------
# Metadata (một phần của output LLM)
# ---------------------------------------------------------------------------

class CommonDocFields(BaseModel):
    """Trường cấp TÀI LIỆU dùng chung mọi loại. Chỉ điền nếu THẤY trong text của chunk này; không thấy thì null."""
    title: Optional[str] = Field(default=None, description="[TRÍCH] Tiêu đề của cả tài liệu (ví dụ heading cấp 1 đầu file). null nếu chunk này không chứa.")
    created_date: Optional[str] = Field(default=None, description="[TRÍCH] Ngày tạo/ban hành, giữ nguyên định dạng trong text. Không tự suy luận.")
    updated_date: Optional[str] = Field(default=None, description="[TRÍCH] Ngày cập nhật gần nhất, giữ nguyên định dạng trong text.")
    language: Optional[str] = Field(default=None, description="[SINH] Mã ngôn ngữ chính của chunk (ISO 639-1: vi, en, ja...).")


class ChunkMetadataBase(BaseModel):
    """Metadata cấp CHUNK dùng chung mọi loại tài liệu. Chỉ dựa trên text của chunk được cung cấp."""
    title: Optional[str] = Field(default=None, description="Tên ngắn của mục/chunk. Ưu tiên heading cuối của heading_path; nếu không có heading thì tự đặt ngắn gọn (<= 8 từ) theo nội dung.")
    topics: list[str] = Field(default_factory=list, description="[SINH] 1-5 chủ đề chính của chunk, mỗi chủ đề 1-4 từ.")
    keywords: list[str] = Field(default_factory=list, description="[SINH] 3-10 từ khóa xuất hiện hoặc thể hiện rõ trong chunk.")
    summary: Optional[str] = Field(default=None, description="[SINH] Tóm tắt 1-3 câu cùng ngôn ngữ tài liệu, chỉ dùng thông tin có trong chunk.")


# ---- CV ----

class CVDocFields(CommonDocFields):
    """Trường cấp tài liệu của CV. Mọi trường [TRÍCH]: chỉ điền khi text chunk này ghi rõ."""
    candidate_name: Optional[str] = Field(default=None, description="[TRÍCH] Họ tên ứng viên.")
    email: Optional[str] = Field(default=None, description="[TRÍCH] Email, nguyên văn.")
    phone: Optional[str] = Field(default=None, description="[TRÍCH] Số điện thoại, nguyên văn.")
    location: Optional[str] = Field(default=None, description="[TRÍCH] Nơi ở/địa chỉ/thành phố của ứng viên.")
    current_title: Optional[str] = Field(default=None, description="[TRÍCH] Chức danh hiện tại/mục tiêu ghi trên CV.")
    experience_years: Optional[float] = Field(default=None, description="[TRÍCH] Số năm kinh nghiệm CHỈ KHI text ghi rõ (ví dụ '5 năm kinh nghiệm'). KHÔNG tự cộng từ các mốc thời gian.")


class CVChunkFields(BaseModel):
    """Trường danh sách cấp chunk của CV."""
    skills: list[str] = Field(default_factory=list, description="[TRÍCH] Kỹ năng/công nghệ được nêu trong chunk.")
    education: list[str] = Field(default_factory=list, description="[TRÍCH] Mỗi mục 1 chuỗi: trường - ngành - (thời gian) nếu có.")
    certifications: list[str] = Field(default_factory=list, description="[TRÍCH] Chứng chỉ/giải thưởng được nêu tên trong chunk.")


class CVChunkOutput(ChunkMetadataBase):
    """Metadata của 1 chunk CV."""
    doc_fields: CVDocFields = Field(default_factory=CVDocFields, description="Trường cấp tài liệu tìm thấy TRONG chunk này.")
    type_fields: CVChunkFields = Field(default_factory=CVChunkFields, description="Trường riêng của CV ở cấp chunk.")


# ---- JD ----

class JDDocFields(CommonDocFields):
    """Trường cấp tài liệu của JD (mô tả công việc)."""
    company_name: Optional[str] = Field(default=None, description="[TRÍCH] Tên công ty tuyển dụng.")
    job_title: Optional[str] = Field(default=None, description="[TRÍCH] Tên vị trí tuyển dụng.")
    department: Optional[str] = Field(default=None, description="[TRÍCH] Phòng ban/bộ phận.")
    location: Optional[str] = Field(default=None, description="[TRÍCH] Địa điểm làm việc.")
    employment_type: Optional[str] = Field(default=None, description="[TRÍCH] Hình thức làm việc (full-time, part-time...) CHỈ KHI text ghi.")
    salary_range: Optional[str] = Field(default=None, description="[TRÍCH] Mức lương nguyên văn CHỈ KHI text ghi.")


class JDChunkFields(BaseModel):
    """Trường danh sách cấp chunk của JD."""
    required_skills: list[str] = Field(default_factory=list, description="[TRÍCH] Kỹ năng/yêu cầu BẮT BUỘC nêu trong chunk.")
    preferred_skills: list[str] = Field(default_factory=list, description="[TRÍCH] Kỹ năng/yêu cầu ƯU TIÊN/điểm cộng nêu trong chunk.")


class JDChunkOutput(ChunkMetadataBase):
    """Metadata của 1 chunk JD."""
    doc_fields: JDDocFields = Field(default_factory=JDDocFields, description="Trường cấp tài liệu tìm thấy TRONG chunk này.")
    type_fields: JDChunkFields = Field(default_factory=JDChunkFields, description="Trường riêng của JD ở cấp chunk.")


# ---- Company ----

class CompanyDocFields(CommonDocFields):
    """Trường cấp tài liệu của tài liệu giới thiệu công ty."""
    company_name: Optional[str] = Field(default=None, description="[TRÍCH] Tên công ty.")
    industry: Optional[str] = Field(default=None, description="[TRÍCH] Lĩnh vực hoạt động.")
    headquarters: Optional[str] = Field(default=None, description="[TRÍCH] Trụ sở chính.")
    company_size: Optional[str] = Field(default=None, description="[TRÍCH] Quy mô (số nhân viên...) CHỈ KHI text ghi.")


class CompanyChunkFields(BaseModel):
    """Trường danh sách cấp chunk của tài liệu công ty."""
    services: list[str] = Field(default_factory=list, description="[TRÍCH] Dịch vụ được nêu tên trong chunk.")
    products: list[str] = Field(default_factory=list, description="[TRÍCH] Sản phẩm được nêu tên trong chunk.")
    departments: list[str] = Field(default_factory=list, description="[TRÍCH] Phòng ban/bộ phận được nêu tên trong chunk.")


class CompanyChunkOutput(ChunkMetadataBase):
    """Metadata của 1 chunk tài liệu công ty."""
    doc_fields: CompanyDocFields = Field(default_factory=CompanyDocFields, description="Trường cấp tài liệu tìm thấy TRONG chunk này.")
    type_fields: CompanyChunkFields = Field(default_factory=CompanyChunkFields, description="Trường riêng của tài liệu công ty ở cấp chunk.")


# ---- Policy ----

class PolicyDocFields(CommonDocFields):
    """Trường cấp tài liệu của chính sách/quy định."""
    policy_name: Optional[str] = Field(default=None, description="[TRÍCH] Tên chính sách/quy định.")
    policy_code: Optional[str] = Field(default=None, description="[TRÍCH] Mã số văn bản, nguyên văn.")
    owner_department: Optional[str] = Field(default=None, description="[TRÍCH] Đơn vị ban hành/chịu trách nhiệm.")
    effective_date: Optional[str] = Field(default=None, description="[TRÍCH] Ngày có hiệu lực, giữ nguyên định dạng trong text.")
    target_audience: Optional[str] = Field(default=None, description="[TRÍCH] Đối tượng áp dụng nếu text nêu rõ.")


class PolicyChunkFields(BaseModel):
    """Trường danh sách cấp chunk của chính sách."""
    compliance_topics: list[str] = Field(default_factory=list, description="[SINH] Chủ đề tuân thủ mà chunk đề cập, dựa trên nội dung chunk.")


class PolicyChunkOutput(ChunkMetadataBase):
    """Metadata của 1 chunk chính sách."""
    doc_fields: PolicyDocFields = Field(default_factory=PolicyDocFields, description="Trường cấp tài liệu tìm thấy TRONG chunk này.")
    type_fields: PolicyChunkFields = Field(default_factory=PolicyChunkFields, description="Trường riêng của chính sách ở cấp chunk.")


# ---- Knowledge ----

class KnowledgeDocFields(CommonDocFields):
    """Trường cấp tài liệu của tài liệu kiến thức."""
    domain: Optional[str] = Field(default=None, description="[TRÍCH/SINH] Lĩnh vực chính của tài liệu nếu thể hiện rõ.")
    difficulty: Optional[str] = Field(default=None, description="[TRÍCH] Độ khó CHỈ KHI tài liệu tự nêu. Không tự đánh giá.")


class KnowledgeChunkFields(BaseModel):
    """Trường danh sách cấp chunk của tài liệu kiến thức."""
    sub_domains: list[str] = Field(default_factory=list, description="[SINH] Lĩnh vực con mà chunk đề cập.")
    concepts: list[str] = Field(default_factory=list, description="[TRÍCH] Khái niệm được định nghĩa/giải thích trong chunk.")
    technologies: list[str] = Field(default_factory=list, description="[TRÍCH] Công nghệ/công cụ được nhắc tên trong chunk.")


class KnowledgeChunkOutput(ChunkMetadataBase):
    """Metadata của 1 chunk tài liệu kiến thức."""
    doc_fields: KnowledgeDocFields = Field(default_factory=KnowledgeDocFields, description="Trường cấp tài liệu tìm thấy TRONG chunk này.")
    type_fields: KnowledgeChunkFields = Field(default_factory=KnowledgeChunkFields, description="Trường riêng của tài liệu kiến thức ở cấp chunk.")


CHUNK_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "cv": CVChunkOutput,
    "jd": JDChunkOutput,
    "company": CompanyChunkOutput,
    "policy": PolicyChunkOutput,
    "knowledge": KnowledgeChunkOutput,
}


def _build_part_result_models() -> dict:
    """Với mỗi loại tài liệu: chunk = ChunkSpan + metadata; kết quả 1 phần = headings + chunks."""
    models = {}
    for doc_type, meta_model in CHUNK_OUTPUT_MODELS.items():
        label = doc_type.upper()
        chunk_model = create_model(
            f"{label}Chunk",
            __base__=(ChunkSpan, meta_model),
            __doc__="Một chunk: ranh giới (start_line, end_line, heading_path, cờ nối phần) "
                    "KÈM metadata của chính chunk đó.",
        )
        models[doc_type] = create_model(
            f"{label}PartResult",
            __doc__="Kết quả cho MỘT phần context. Các chunk phải phủ KÍN mọi dòng trong khối "
                    "[NỘI DUNG CẦN CHIA CHUNK], không chồng lấn, theo đúng thứ tự; mỗi chunk kèm metadata.",
            headings=(list[HeadingNode], Field(
                default_factory=list,
                description="Các dòng bạn xác định là heading trong phần này, theo thứ tự xuất hiện.")),
            chunks=(list[chunk_model], Field(
                description="Các chunk theo thứ tự, phủ kín khối cần chia chunk, mỗi chunk kèm metadata.")),
        )
    return models


PART_RESULT_MODELS: dict[str, type[BaseModel]] = _build_part_result_models()


# ---------------------------------------------------------------------------
# KẾT QUẢ CUỐI (code dùng, không phải output LLM)
# ---------------------------------------------------------------------------

class Chunk(BaseModel):
    """1 chunk đã hoàn chỉnh: TEXT GỐC (code cắt theo số dòng) + metadata cấp chunk."""
    chunk_id: str
    doc_id: str
    doc_type: DocType
    start_line: int
    end_line: int
    heading_path: list[str] = Field(default_factory=list)
    text: str
    metadata: dict = Field(default_factory=dict)


class IndexedDocument(BaseModel):
    """Kết quả indexing 1 tài liệu."""
    doc_id: str
    doc_type: DocType
    source_file: Optional[str] = None
    metadata: dict = Field(default_factory=dict)   # cấp tài liệu
    chunks: list[Chunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChunkingState(BaseModel):
    """State chuyển qua các phần (part) của cùng 1 tài liệu ở lượt 1."""
    doc_id: str
    doc_type: DocType
    total_parts: int
    part_index: int = 0
    spans: list = Field(default_factory=list)   # các chunk (ChunkSpan + metadata) theo thứ tự
    doc_observations: list = Field(default_factory=list)  # doc_fields (dict) quan sát được ở từng chunk
    warnings: list[str] = Field(default_factory=list)

    def open_chunk(self):
        """Chunk đang dở ở cuối phần trước (nếu có)."""
        if self.spans and self.spans[-1].continues_next_part:
            return self.spans[-1]
        return None

    def last_heading_path(self) -> list[str]:
        return list(self.spans[-1].heading_path) if self.spans else []


# ---------------------------------------------------------------------------
# Render docstring + description của schema thành text để đưa vào prompt
# ---------------------------------------------------------------------------

def _nested_model(annotation) -> Optional[type[BaseModel]]:
    """Lấy class BaseModel từ annotation, kể cả bọc trong list[...] hoặc Optional[...]."""
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return annotation
    origin = get_origin(annotation)
    if origin is list or origin is Union or origin is getattr(types, "UnionType", None):
        for arg in get_args(annotation):
            found = _nested_model(arg)
            if found:
                return found
    return None


def _type_name(annotation) -> str:
    name = getattr(annotation, "__name__", None)
    if name and not getattr(annotation, "__args__", None):
        return name
    return str(annotation).replace("typing.", "").replace("state.", "")


def describe_schema(model: type[BaseModel], indent: int = 0) -> str:
    """Render docstring + mỗi field (kiểu, mô tả) của model, đệ quy cho model lồng nhau."""
    pad = "  " * indent
    lines = []
    doc = inspect.cleandoc(model.__doc__) if model.__doc__ else ""
    lines.append(f"{pad}{model.__name__}: {doc}")
    for name, info in model.model_fields.items():
        lines.append(f"{pad}- {name} ({_type_name(info.annotation)}): {info.description or ''}")
        nested = _nested_model(info.annotation)
        if nested:
            lines.append(describe_schema(nested, indent + 1))
    return "\n".join(lines)