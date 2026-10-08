# Chunking Analyze Agent System V1

## 1. Mục tiêu

Chunking Analyze Agent là hệ thống Agent chịu trách nhiệm xử lý toàn bộ tài liệu đầu vào trước khi lưu vào Vector Database hoặc Database.

Khác với các hệ thống RAG truyền thống chỉ thực hiện:

```text
Document
→ Split Chunk
→ Embedding
→ Vector Store
```

hệ thống này tập trung vào việc:

* Hiểu cấu trúc tài liệu
* Phát hiện các Heading và Subheading
* Chuẩn hóa cấu trúc tài liệu
* Chia Chunk theo ngữ nghĩa
* Sinh Metadata chuẩn
* Kiểm tra chất lượng Chunk
* Tự sửa Chunk nếu chưa đạt yêu cầu
* Lựa chọn kho lưu trữ phù hợp

Mục tiêu cuối cùng là tạo ra các Chunk có chất lượng cao, có cấu trúc rõ ràng và dễ dàng truy xuất trong quá trình phỏng vấn.

---

# 2. Vai trò người dùng

Người dùng sẽ chủ động xác định loại tài liệu trước khi thực hiện Indexing.

Ví dụ:

* CV
* JD
* Knowledge
* Rubric
* Policy
* Question Bank

Người dùng xác nhận loại tài liệu trước khi hệ thống bắt đầu xử lý.

Điều này giúp giảm sai sót và tránh việc LLM phải tự suy đoán loại tài liệu.

---

# 3. Kiến trúc tổng thể

```text
User Upload File
        │
        ▼

Parser Analyze Agent
        │
        ▼

Chunk Planning Agent
        │
        ▼

Chunk Validation Agent
        │
        ▼

Storage Routing Agent
        │
        ▼

Qdrant / SQL Database
```

---

# 4. Parser Analyze Agent

## Mục tiêu

Đây là Agent chịu trách nhiệm hiểu cấu trúc tài liệu.

---

## Nhiệm vụ

### 4.1 Trích xuất dữ liệu

Agent đọc:

* PDF
* DOCX
* XLSX
* PPTX
* Image OCR

và tạo ra văn bản sạch nhất có thể.

Nguyên tắc:

* Không làm mất dữ liệu
* Không tóm tắt dữ liệu
* Không viết lại dữ liệu

---

### 4.2 Phát hiện cấu trúc

Agent xác định:

* Heading Level 1
* Heading Level 2
* Heading Level 3
* Heading Level 4
* Danh sách
* Bảng biểu
* Section
* Subsection

Ví dụ:

```text
EDUCATION

University of Danang

EXPERIENCE

AI Intern
```

Agent nhận diện:

```json
{
  "education": "...",
  "experience": "..."
}
```

---

### 4.3 Chuẩn hóa Heading

Các tiêu đề đồng nghĩa sẽ được đưa về một chuẩn chung.

Ví dụ:

```text
Học vấn
Education
Academic Background
Quá trình học tập
```

↓

```text
education
```

Ví dụ:

```text
Mô tả công việc
Nhiệm vụ
Responsibilities
Job Description
```

↓

```text
job_details
```

Agent chỉ chuẩn hóa tên mục.

Không thay đổi nội dung bên trong mục.

---

### Output

```json
{
  "document_type": "cv",
  "sections": [
    {
      "canonical_name": "education",
      "content": "..."
    },
    {
      "canonical_name": "experience",
      "content": "..."
    }
  ]
}
```

---

# 5. Chunk Planning Agent

## Mục tiêu

Tạo các Chunk có cấu trúc và ngữ nghĩa tốt.

---

## Nguyên tắc Chunking

Không chia Chunk theo:

* Ký tự
* Dòng
* Số lượng từ

Nếu làm mất cấu trúc ngữ nghĩa.

---

Chunk được ưu tiên tách theo:

1. Section
2. Subsection
3. Semantic Boundary
4. Token Constraint

---

Ví dụ:

```text
Experience

Company A
...
Company B
...
Company C
...
```

Chunk lý tưởng:

```text
Chunk 1 → Company A

Chunk 2 → Company B

Chunk 3 → Company C
```

Không nên:

```text
Chunk 1 → Company A + nửa Company B
```

---

## Metadata Generation

Agent sẽ sinh Metadata cho từng Chunk.

Metadata sử dụng mô hình:

### Core Metadata Schema

Mọi loại tài liệu đều phải có.

```json
{
  "document_id": "",
  "document_type": "",
  "source_file": "",
  "chunk_id": "",
  "chunk_order": 0,
  "section_name": "",
  "subsection_name": "",
  "token_count": 0,
  "created_at": ""
}
```

---

### Extended Metadata

Tùy từng loại tài liệu.

Ví dụ:

CV:

```json
{
  "candidate_name": "",
  "position": "",
  "skills": []
}
```

JD:

```json
{
  "position": "",
  "level": "",
  "required_skills": []
}
```

Knowledge:

```json
{
  "topic": "",
  "subtopic": "",
  "keywords": []
}
```

Rubric:

```json
{
  "position": "",
  "level": "",
  "evaluation_category": ""
}
```

---

# 6. Chunk Validation Agent

## Mục tiêu

Đảm bảo Chunk đạt chất lượng trước khi lưu trữ.

---

## Validation Trước Khi Chunk

Kiểm tra:

* Heading hợp lệ
* Section hợp lệ
* Mapping chuẩn hóa hợp lệ
* Nội dung không rỗng

---

## Validation Sau Khi Chunk

Kiểm tra:

* Metadata đầy đủ
* Chunk không trùng lặp
* Chunk không bị cắt giữa bảng
* Chunk không bị cắt giữa section
* Chunk không bị cắt giữa câu
* Chunk đúng giới hạn token

---

## Token Constraint

Mỗi Embedding Model có Context Window riêng.

Ví dụ:

```text
Embedding Context Window = 256 Tokens
```

Thiết lập:

```text
MIN_CHUNK_SIZE     = 200 Tokens

TARGET_CHUNK_SIZE  = 250 Tokens

MAX_CHUNK_SIZE     = 350 Tokens
```

Quy tắc:

```text
Chunk < 200
→ Merge
```

```text
Chunk > 350
→ Split
```

Không cho phép lưu Chunk vượt quá ngưỡng tối đa.

---

## Self Repair

Nếu Chunk không đạt:

```text
Validation
↓
Fail
↓
Rebuild Chunk
↓
Validation
↓
Pass
```

Agent sẽ tự điều chỉnh cho đến khi đạt tiêu chuẩn.

---

# 7. Storage Routing Agent

## Mục tiêu

Lựa chọn nơi lưu trữ phù hợp.

---

Knowledge:

```text
Qdrant
```

---

CV:

```text
Qdrant + SQL
```

---

JD:

```text
Qdrant + SQL
```

---

Rubric:

```text
Qdrant + SQL
```

---

## Output

Sau khi hoàn thành:

* Tổng số tài liệu xử lý
* Tổng số Chunk sinh ra
* Tổng số Chunk hợp lệ
* Tổng số Chunk bị sửa
* Tổng số Chunk lỗi
* Trạng thái lưu trữ

Ví dụ:

```text
Files Processed : 12

Chunks Created  : 458

Chunks Passed   : 452

Chunks Repaired : 6

Chunks Failed   : 0

Status          : Success
```

---

# 8. Nguyên tắc cốt lõi

Agent không được phép:

* Tóm tắt tài liệu
* Viết lại tài liệu
* Thay đổi tri thức gốc
* Sinh nội dung mới

Agent chỉ được phép:

* Hiểu cấu trúc
* Chuẩn hóa Heading
* Chia Chunk
* Sinh Metadata
* Đánh giá Chunk
* Chọn nơi lưu trữ

Toàn bộ dữ liệu được lưu trữ và Embedding vẫn là dữ liệu gốc đã được trích xuất từ tài liệu đầu vào.
