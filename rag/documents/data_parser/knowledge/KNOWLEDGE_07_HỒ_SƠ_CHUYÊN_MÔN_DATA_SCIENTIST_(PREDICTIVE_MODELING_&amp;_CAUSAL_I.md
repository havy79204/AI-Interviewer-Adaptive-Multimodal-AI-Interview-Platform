## [TÀI LIỆU 07] HỒ SƠ CHUYÊN MÔN: DATA SCIENTIST (PREDICTIVE MODELING &amp; CAUSAL INFERENCE)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Data Scientist / Machine Learning Scientist.
- Domain ứng dụng: Fintech (Chấm điểm tín dụng, Phát hiện gian lận), E-commerce (Dynamic Pricing, Recommendation Engine), Proptech (Mô hình thẩm định giá tự động - AVM).
- Mục tiêu then chốt của vị trí: Chuyển hóa dữ liệu kinh doanh phi cấu trúc hoặc chuỗi thời gian thành các mô hình toán học có khả năng khái quát hóa cao; phân định rõ ràng giữa mối tương quan (Correlation) và quan hệ nhân quả (Causation) để tối ưu quyết định vận hành.
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn (Upstream): Nhận dữ liệu sạch, feature store từ Data Engineer; tiếp nhận bài toán định lượng và ràng buộc từ Product Owner / Business Lead.
- Hạ nguồn (Downstream): Bàn giao trọng số mô hình, pipeline feature extraction và inference logic cho MLOps / Backend Engineer để đóng gói API; cung cấp giải thích mô hình (SHAP/LIME) cho Risk &amp; Compliance Team.
- Giao tiếp ngang: Phối hợp cùng UI/UX Designer và Growth Team thiết kế thử nghiệm A/B Testing có phân tầng người dùng (Stratified Sampling).
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi
- Model Engine: LightGBM, CatBoost, XGBoost (dành cho Tabular data); PyTorch (Deep Learning cho chuỗi dữ liệu phức tạp).
- Feature &amp; Experiment Tracking: MLflow, Weights &amp; Biases, Feast, Optuna (Bayesian Hyperparameter Optimization).
- Dữ liệu lớn &amp; Truy vấn: DuckDB (xử lý cục bộ tốc độ cao), Polars, Google BigQuery / Snowflake SQL, PySpark.
- Định lượng &amp; Kiểm định: Causal Inference (DoWhy, CausalML), A/B Testing framework (Cuped - Variance Reduction), SHAP (Shapley Additive Explanations).
4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành
- Data Leakage &amp; Train-Test Contamination:
- Vấn đề: Mô hình đạt độ chính xác trong quá trình thử nghiệm 𝐴𝑈𝐶 = 0. 98 nhưng sụt giảm nghiêm trọng khi chạy môi trường thực tế (Production).
- Bản chất kỹ thuật: Rò rỉ thông tin tương lai vào tập huấn luyện (Lookahead bias trong Time-series), hoặc tính toán các biến tổng hợp (Target Encoding, Normalization) trên toàn bộ dataset trước khi chia tập Train/Test.
- Giải pháp: Thiết lập chặt chẽ Time-based Split; đóng gói toàn bộ quy trình tiền xử lý vào sklearn.pipeline.Pipeline để ngăn ngừa rò rỉ dữ liệu ngoài fold.
- Hiện tượng Data Drift &amp; Concept Drift:
- Vấn đề: Hành vi người dùng thay đổi sau một chiến dịch quảng cáo lớn hoặc biến động kinh tế vĩ mô, khiến phân phối đầu vào hoặc xác suất điều kiện 𝑃(𝑋) $P(Y\vert{}X)$ bị biến đổi.
- Giải pháp: Triển khai thuật toán kiểm định thống kê KS-Test (Kolmogorov-Smirnov) hoặc chỉ số PSI (Population Stability Index) trên các biến đầu vào; thiết lập ngưỡng cảnh báo tự động để kích hoạt quy trình tái huấn luyện (Re-training loop).
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Phản biện bài toán kinh doanh vs. Chỉ số mô hình:
- Tình huống: Đội ngũ Kinh doanh yêu cầu mô hình phát hiện gian lận đạt độ chính xác Precision 99%, nhưng điều này dẫn đến Recall chỉ đạt 20% (bỏ sót phần lớn gian lận).
- Luận điểm xử lý: Chuyển đổi bài toán tối ưu F1-score/Accuracy sang Cost Matrix Optimization (Định lượng chi phí tổn thất của một ca False Negative so với chi phí chăm sóc khách hàng của một ca False Positive) để tìm ngưỡng cắt xác suất (Optimal Threshold Cutoff) tối đa hóa lợi nhuận tài chính ròng.
6. Môi trường tác nghiệp &amp; Công cụ thực tế
- Hạ tầng làm việc: Cụm GPU đám mây (JupyterHub / Databricks workspace), máy trạm chuyên dụng màn hình kép (1 màn hình hiển thị biểu đồ phân phối dữ liệu, 1 màn hình theo dõi log huấn luyện Optuna).
- Trực quan hóa: Streamlit / Dash phục vụ bản demo nội bộ cho các bên liên quan; theo dõi trực tiếp các đường cong ROC-PR và Confusion Matrix trên Grafana.