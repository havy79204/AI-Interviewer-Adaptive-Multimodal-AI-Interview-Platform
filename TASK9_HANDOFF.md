# AI Interview Platform — Handoff & Progress Snapshot

**Mục đích:** Lưu trạng thái dự án trước khi đổi tài khoản GitHub Copilot trong VS Code.  
**Ngày snapshot:** 2026-10-14  
**Lưu ý quan trọng:** Nội dung này được tổng hợp từ báo cáo Copilot và thông tin đã trao đổi; trợ lý ChatGPT chưa trực tiếp mở hoặc chạy repo trên máy của bạn.

## 1. Repo và môi trường

- Repo: `AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform`
- Đường dẫn local:
  `C:\Users\vy.vo\Downloads\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform`
- Branch: `ha-vy`
- Không commit nếu chưa được yêu cầu.
- User muốn làm từng task, xác minh bằng dữ liệu mẫu/thật có kiểm soát, không audit quá rộng.
- Thư mục workspace cha:
  `C:\Users\vy.vo\Downloads\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform`

## 2. Mục tiêu sản phẩm

1. Chuẩn bị dữ liệu từ JD, CV, tài liệu công ty và tài liệu kiến thức; extract/chunk/index.
2. RAG truy xuất đúng nguồn.
3. Interview Planning Agent lập 10 câu hỏi chính kèm competency/objective/rubric.
4. Thực hiện phỏng vấn, lưu câu hỏi/trả lời/trạng thái; text trước, voice/STT/TTS sau.
5. Đánh giá câu trả lời thích ứng và đặt tối đa một câu follow-up cho mỗi câu chính khi cần.
6. Tạo báo cáo HR.

Demo hiện tại: text + voice; video để sau. Chạy local.

## 3. Các file/vị trí mã chính theo báo cáo Copilot

- API entry: `apps/api/main.py`
- Interview route: `apps/api/v1/routes/interview.py`
- Interview service: `services/interview_service.py`
- Interview agent graph: `agents/interview_agent/graph/__init__.py`
- LLM provider: `integrations/llm_providers/provider.py`
- RAG service: `rag/service.py`
- RAG ingestion: `rag/ingest.py`, `rag/corpus_loader.py`
- Indexing: `rag/chunking/run_indexing.py`, `rag/chunking/extract_with_docling.py`
- Voice session: `voice/session.py`
- Database: `services/database.py`
- HR report: `services/report_service.py`
- Web UI: `apps/web/src/index.html`

## 4. Trạng thái Task 1–7 (theo báo cáo Copilot)

Các kết quả sau là báo cáo đã nhận, không phải ChatGPT tự chạy lại:

- **Task 1 — Data preparation:** Docling lazy import; indexing hỗ trợ các loại tài liệu liên quan. Có báo cáo 24 PASS, 1 SKIP (live OpenAI embedding).
- **Task 2 — RAG ingestion/retrieval:** lexical/sample retrieval, lọc source, truy vấn không liên quan trả rỗng. Có báo cáo 27 PASS, 1 SKIP.
- **Task 3 — Interview planner:** RAG lấy CV/JD/company/knowledge riêng; tạo 10 câu hỏi có competency/objective/rubric. Có báo cáo 52 PASS, 1 SKIP.
- **Runtime integration/idempotency:** plan lưu trong `interviews.state_json`; request có trường JD/CV tùy chọn; idempotency và migration; có báo cáo 44 PASS. Rủi ro đã biết: reservation có thể mắc sau crash và gây 409 sau 60 giây.
- **Task 4 — Interview execution:** kiểm tra plan, câu trả lời/thứ tự session, retry idempotency, kết thúc sau 10 câu. Có báo cáo 45 PASS.
- **Task 5 — Adaptive evaluation:** rubric/evidence text, tối đa một follow-up/câu chính, persistence, retry idempotency; không suy luận tính cách/cảm xúc từ video. Có báo cáo 53 PASS.
- **Task 6 — HR report:** JSON/TXT. Có báo cáo 24 PASS.
- **Task 7 — Integrated sample pipeline:** `tests/integration/test_task1_to_task6_sample_pipeline.py`; mocked extraction/indexing → JSON → SQLite ingestion → RAG → 10-question plan → interview/follow-up/retry → HR report. Có báo cáo 38 PASS, 0 FAIL, 0 SKIP trong lần chạy được ghi nhận. Chỉ dùng mock/sample; chưa xác minh PDF thật, LLM thật, embedding thật, Redis, STT/TTS. Startup auto-ingestion không được xác minh.

## 5. Task 8 — dữ liệu CV/JD thật và RAG

### Tài liệu đầu vào
Trong repo có `cv.pdf` và `jd.pdf`; mỗi PDF gộp nhiều hồ sơ:
- CV PDF: 40 CV; chọn CV #1.
- JD PDF: 20 JD; chọn JD #1.
- CV #1 có tên ứng viên Vũ Đình Long.
- JD #1: Senior DevOps Engineer (Cloud Infrastructure).

Tài liệu được trích xuất bằng Docling. Kích thước Markdown báo cáo:
- CV khoảng 3,287 ký tự.
- JD khoảng 2,434 ký tự.

Các nhóm kỹ năng giao nhau được báo cáo:
- Cloud/Kubernetes: AWS/GCP, EKS, Kubernetes đa vùng, 800+ nodes.
- IaC: Terraform, Terragrunt, Ansible.
- CI/CD/GitOps: GitLab CI, ArgoCD, Jenkins, GitHub Actions.
- Observability: Prometheus, Grafana, Datadog, OpenTelemetry.
- DevSecOps/security: Trivy, SonarQube, Vault, PCI-DSS.

### Local indexing / Qwen embeddings
- Local indexing bổ sung trong `rag/chunking/run_indexing.py` theo báo cáo Copilot; tạo chunk/metadata từ Markdown mà không gọi LLM bên ngoài.
- `rag/ingest.py` có `include_demo=False`, `lexical_only=True`; mặc định hiện hữu không đổi.
- Model embedding local: `Qwen/Qwen3-Embedding-0.6B`
- Revision: `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`
- Model ~1.19 GB, 1024 chiều, chạy CPU; báo cáo đã load offline, output hữu hạn và normalized. Thời gian chạy benchmark khoảng 108.62 giây, peak working set khoảng 1.7 GB, không có CUDA.
- Provider `qwen_local` được thêm theo báo cáo; default provider không đổi.
- Semantic benchmark cho truy vấn phù hợp trả các chunk CV/JD có liên quan; truy vấn không liên quan vẫn có điểm semantic thấp khoảng 0.2067–0.2123, chưa chốt threshold. Lexical retrieval trả 0 kết quả cho truy vấn không liên quan.

### Runtime DB đã ingest dữ liệu thật
Runtime DB đã xác định theo báo cáo Copilot:
`storage\ai_interviewer.db`

Đây là DB runtime của API. Không nhầm với pilot DB `qwen3-semantic-temp.db` (pilot chỉ có bảng RAG).

Các JSON selected ban đầu nằm trong thư mục session Copilot ngoài repo:
- `C:\Users\vy.vo\.copilot\session-state\e65c4252-66f0-4198-9642-03a6bbda76f4\files\task8-local-run\indexed\cv\selected_cv.json`
- `C:\Users\vy.vo\.copilot\session-state\e65c4252-66f0-4198-9642-03a6bbda76f4\files\task8-local-run\indexed\jd\selected_jd.json`

Sau đó Copilot báo đã tìm, extract, local-index và ingest thêm `company.pdf`, `knowledge.pdf`:
- Company: 10 Markdown + 10 JSON; 100 chunks.
- Knowledge: 25 Markdown + 25 JSON; 117 chunks.
- Tổng 217 chunks company/knowledge được ingest; không dùng demo corpus.
- Tổng active chunks trong runtime DB:
  - CV: 8
  - JD: 4
  - Company: 100
  - Knowledge: 117
  - **Tổng: 229**
- Báo cáo: 0 vectors (runtime ingestion lexical-only), không có duplicate document keys.
- RAG retrieval với filter và attribution có kết quả cho cả 4 loại nguồn: CV=4, JD=3, company=5, knowledge=5.
- Query không liên quan (quasar/exoplanet/neutrino) trả 0 kết quả.
- `ingest_runtime_corpus()` được gọi thủ công; startup của API không tự gọi hàm này theo kiểm tra đã báo cáo.
- Không sửa file PDF gốc; không commit.

### Kiểm thử Task 8 (theo báo cáo)
- Các lần chạy có kết quả 25 PASS, 1 SKIP; 30 PASS, 1 SKIP; và các bộ regression khác PASS.
- `git diff --check` PASS.
- Có lỗi encoding khi in tên file tiếng Việt trong lần indexing đầu; đã chạy lại indexing từ Markdown đã lưu và loader xác nhận dữ liệu. Cần quan sát encoding khi tiếp tục làm việc.

## 6. Môi trường local / Docker / Ollama

- Docker Desktop per-user:
  `C:\Users\vy.vo\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe`
- Docker CLI ở:
  `...\resources\bin\docker.exe`
- Docker version báo cáo: 29.8.2.
- WSL đã được cập nhật; Docker server hoạt động.
- Redis container đã được chạy bằng `docker compose up -d redis`; `redis-cli ping` trả `PONG`.
- Không chạy API trong Docker đồng thời với host API nếu chúng cùng trỏ đến dữ liệu không mong muốn.
- Host API được khởi chạy bằng Python cài tại:
  `C:\Users\vy.vo\AppData\Local\Programs\Python\Python312\python.exe`
  (không phải `.venv\Scripts\python.exe` trong repo).
- Python 3.12.10; PyTorch 2.14.1+cpu; Transformers 5.19.0 theo báo cáo.
- Ollama version báo cáo: 0.40.4.
- Ollama model: `qwen2.5:3b`, khoảng 1.9 GB, chạy CPU.
- Cấu hình môi trường dùng khi host API được khởi chạy:
  ```powershell
  $env:LLM_PROVIDER = "openai"
  $env:OPENAI_BASE_URL = "http://localhost:11434/v1"
  $env:OPENAI_MODEL = "qwen2.5:3b"
  $env:OPENAI_API_KEY = "ollama-local"
  $env:EMBEDDING_PROVIDER = "none"
  python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
  ```
- Uvicorn PID được báo cáo: 8724; port 8000; health endpoint từng trả 200.
- Settings timeout LLM được resolve là `LLM_TIMEOUT_SECONDS=20.0` theo giá trị mặc định, không có biến môi trường override và không có `.env` ở repo root.
- `provider_from_settings()` chỉ tạo OpenAI-compatible provider nếu `LLM_PROVIDER=="openai"` và `OPENAI_API_KEY` không rỗng.
- `InterviewService()` được khởi tạo khi module load; đổi biến môi trường thường cần restart API.

## 7. Task 9 — auth và lỗi HTTP 503 (đang dở)

### Auth
- Swagger UI: `http://127.0.0.1:8000/docs`
- Candidate ID:
  `8b5ede69-8448-48d4-88ea-68cd50546109`
- Candidate demo name: `Vy Demo`
- Email demo: `vy.123@example.com`
- `GET /api/v1/auth/me` đã trả HTTP 200 và xác nhận role candidate.
- Mật khẩu demo từng được dùng khi đăng ký: `Vydemo123!`. Chỉ dùng cho môi trường local demo; đổi nếu cần.
- **Không lưu JWT bearer token trong file này.** Token từng được dán trong chat; không nên sao chép hoặc chia sẻ lại. Nếu nghi ngờ token bị lộ, đăng xuất/đăng nhập lại hoặc làm mới token theo luồng auth hiện có.

### Request tạo interview đã lỗi
Endpoint:
`POST http://127.0.0.1:8000/api/v1/interview/start`

Body đã gửi:
```json
{
  "candidate_id": "8b5ede69-8448-48d4-88ea-68cd50546109",
  "position": "Senior DevOps Engineer (Cloud Infrastructure)",
  "mode": "text",
  "job_description": "Senior DevOps Engineer (Cloud Infrastructure). Responsibilities include designing and operating cloud infrastructure, managing Kubernetes clusters and multi-region deployments, implementing Infrastructure as Code with Terraform and Terragrunt, automating CI/CD and GitOps workflows, improving observability with Prometheus, Grafana, Datadog and OpenTelemetry, and implementing DevSecOps practices. Relevant technologies include AWS, GCP, EKS, Kubernetes, Terraform, Terragrunt, Ansible, GitLab CI, ArgoCD, Jenkins, GitHub Actions, Trivy, SonarQube and Vault. Experience with production-scale infrastructure, reliability, security and PCI-DSS compliance is valuable.",
  "candidate_resume": "Candidate profile for Senior DevOps Engineer. Skills reported in the selected Task 8 CV include Python, AWS, Kubernetes, multi-region Kubernetes operations, EKS, infrastructure at scale, Terraform, Terragrunt, Ansible, GitLab CI, ArgoCD, Jenkins, GitHub Actions, Prometheus, Grafana, Datadog, OpenTelemetry, Trivy, SonarQube, Vault and PCI-DSS security practices. This summary is based on previously reported extracted skills and is not the full original CV.",
  "idempotency_key": "vy-qwen-devops-test-001"
}
```

Kết quả:
```json
{"detail":"Interview question planning is temporarily unavailable"}
```
HTTP 503, ngày ghi nhận 14 Oct 2026. DB sau request báo cáo có 0 interviews và 0 idempotency rows, phù hợp với reservation được giải phóng sau lỗi; đây không phải bằng chứng tuyệt đối về nguyên nhân.

### Điều đã biết về 503
- Route bắt `QuestionPlanningError` và trả HTTP 503 với thông báo trên.
- Planner lấy RAG context theo 4 loại `cv`, `jd`, `company`, `knowledge`; nếu thiếu nguồn hoặc thiếu attribution marker thì có thể raise `QuestionPlanningError`.
- Retrieval độc lập trên runtime DB đã tìm được context có attribution cho cả 4 nguồn; tuy nhiên chưa xác nhận context đúng chính xác cho request gây lỗi.
- Provider tạo JSON bằng cách chèn schema instructions vào prompt và parse kết quả bằng `schema.model_validate_json(raw)`; không dùng `response_format` chuyên biệt.
- Schema yêu cầu đủ 10 câu hỏi, mỗi câu có competency/objective/rubric hợp lệ.
- Timeout hiệu lực là 20 giây.
- Các lần benchmark độc lập với `qwen2.5:3b` trên CPU cho thấy JSON schema ngắn chạy được khoảng 3.63 giây, nhưng full `InterviewQuestionPlan` schema generation timeout sau khoảng 22 giây và trong lần thử khác sau 90 giây.
- Điều này khiến timeout/structured generation là **giả thuyết mạnh**, nhưng **chưa xác nhận nguyên nhân chính xác của request 503** vì chưa có traceback/log của đúng request.
- Copilot không đọc được scrollback của terminal đang chạy Uvicorn và chưa tìm thấy traceback trong log file.
- Unit tests offline báo cáo:
  - `test_provider_timeout_is_normalized` PASS
  - `test_structured_output_invalid_after_bounded_retry_is_rejected` PASS
  - `test_question_plan_fails_when_any_required_rag_source_is_missing` PASS
  - `test_malformed_structured_llm_output_is_reported` PASS
  - `tests/unit/test_api_interview.py::test_start_interview_maps_question_planning_error_to_503` PASS
- Test route thêm mới được báo cáo: `tests/unit/test_api_interview.py` +23 dòng, không sửa production code. Các test dùng provider fake/mock và DB test tách biệt.
- Một số bộ test/regression gần đây báo cáo PASS; không nên coi chúng là chứng minh LLM local có thể tạo full plan trong thời gian chấp nhận được.

### Bước kế tiếp Task 9
Chưa thay đổi production code để tăng timeout hoặc rút gọn prompt một cách mù quáng. Cần:
1. Chạy một harness/test cô lập gọi planner với cùng cấu hình Ollama và cùng context, đo thời gian, ghi kết quả timeout/JSON/schema, tuyệt đối không tạo interview hoặc ghi runtime DB.
2. Nếu harness không an toàn hoặc vẫn quá lâu, chỉ báo cáo điều kiện và đề xuất, không chạy request thật.
3. Nếu xác nhận timeout/structured output, cải thiện prompt/output size và timeout có giới hạn; retry phải bounded. Không để request treo vô hạn.
4. Chỉ lưu interview sau khi plan hợp lệ đủ 10 câu; reservation/idempotency phải được giải phóng đúng cách khi lỗi.
5. Sau khi sửa, test bằng DB cô lập và mới thử một request runtime có chủ đích.
6. Không commit nếu chưa được user yêu cầu.

## 8. Copilot credits / đổi tài khoản GitHub

Người dùng có ảnh chụp panel Copilot Free:
- Credits: 98% used; resets Nov 1 at 7:00 AM.
- Inline Suggestions: 5% used; resets Nov 1 at 7:00 AM.
- Inline Suggestions enabled; Ghost text suggestions và Next edit suggestions bật.
- Codebase Semantic Index: Not indexed.
- Session Sync: Not enabled.

Giải thích đã cung cấp:
- Credits 98% used nghĩa là gần hết quota AI chính, còn khoảng 2%.
- Inline Suggestions 5% used là quota riêng cho gợi ý code inline, còn khoảng 95% quota riêng đó.
- Không thể chuyển quota Inline Suggestions sang Chat/Agent; hai quota khác nhau. Khi AI credits hết, inline suggestions có thể vẫn dùng được; khi inline quota hết, chat có thể vẫn dùng được tùy giới hạn plan.
- Đổi tài khoản GitHub Copilot thường không ảnh hưởng đến cuộc chat ChatGPT này, nhưng lịch sử Copilot Chat trong VS Code có thể gắn với tài khoản cũ.
- Trước khi đổi account: lưu file code, sao chép prompt/kết quả Copilot quan trọng vào file trong repo, chụp/copy cuộc chat đang dở.
- Sau khi đổi account, repo local và các file đã lưu thường còn nguyên; lịch sử Copilot Chat không được đảm bảo.

## 9. Quy tắc làm việc cho phiên tiếp theo

- Trả lời tiếng Việt, gọn và rõ.
- Làm từng task, không mở rộng sang audit tổng thể nếu chưa được yêu cầu.
- Phân biệt rõ: điều đã kiểm chứng bằng output, điều chỉ là báo cáo Copilot, và giả thuyết.
- Không tuyên bố đã trực tiếp chạy/kiểm tra repo trên máy người dùng.
- Không ghi token/JWT vào file hoặc prompt; người dùng từng dán bearer token trong chat.
- Không commit, không sửa production code hoặc runtime DB nếu chưa được user đồng ý.
- Với Copilot, prompt nên yêu cầu rõ: phạm vi, điều cấm (không ghi runtime DB/không tạo interview/không sửa code), tiêu chí hoàn thành và báo cáo kết quả ngắn.
- Nếu Copilot credits hết, có thể tiếp tục chuẩn bị prompt và phân tích trong ChatGPT, sau đó gửi prompt cho Copilot khi quota khả dụng.

## 10. Prompt ngắn để tiếp tục sau khi đổi tài khoản

Dán prompt này vào Copilot Chat/Agent sau khi đăng nhập tài khoản mới:

> Đọc file `TASK9_HANDOFF.md` (hoặc file handoff đã lưu) và kiểm tra trạng thái repo hiện tại trước khi làm gì. Không commit. Không ghi runtime DB, không tạo interview thật, không thay đổi production code. Tiếp tục đúng mục “Bước kế tiếp Task 9”: thiết kế/chạy harness cô lập cho planner dùng Ollama `qwen2.5:3b` và dữ liệu RAG hiện tại, đo thời gian và xác định nguyên nhân HTTP 503. Nếu không thể bảo đảm không ghi runtime DB thì dừng và báo lại. Phân biệt rõ kết quả đã xác minh với giả thuyết. Chỉ đề xuất thay đổi sau khi có bằng chứng; không tăng timeout vô hạn.
