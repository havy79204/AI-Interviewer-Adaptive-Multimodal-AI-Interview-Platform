## [CV 21] ỨNG TUYỂN: SENIOR DEVOPS ENGINEER (JD 01)

Plaintext [HOST: vulam-core-ops] ~ $ whoami NAME : Vũ Hoàng Lâm ROLE : Lead Site Reliability &amp; DevOps Specialist LOCATION : Tây Hồ, Hà Nội CONTACT : lam.vuhoang.ops@proton.me | +84 904 551 299 REPOSITORIES: github.com/vhlam-infra | blog.vhlam.io STATUS : Ready for High-Scale Production Operations (Multi-Region / High Availability)

## 01 // CORE COMPETENCY MATRIX

- Container Ecosystem: Kube-bench, Cilium (eBPF), Envoy Gateway, Argo Rollouts, Keda, Helm 3.
- IaC &amp; Automation: Terraform Module Authoring, Terragrunt, Ansible Automation Platform, Python/Bash.
- Observability Architecture: OpenTelemetry Collector, Thanos + Prometheus, Grafana Tempo, Loki.
- Security &amp; Hardening: HashiCorp Vault (AppRole, PKI Secrets Engine), Cosign, Trivy in-pipeline.
- Cloud Infrastructure: AWS (EKS, VPC Peering, Transit Gateway, CloudFront, Aurora Global).

## 02 // RECENT PRODUCTION INCIDENTS &amp; DELIVERABLES

## SRE / DevOps Lead | FinBridge Global Ltd. (11/2023 - Hiện tại | Hà Nội)

- Zero-Downtime EKS Upgrade: Thiết kế kịch bản nâng cấp cụm Kubernetes từ v1.26 lên v1.30 cho 120+ microservices sử dụng kỹ thuật Canary Deployment và Argo Rollouts, tỷ lệ gián đoạn giao dịch thực tế là 0%.
- Kiến trúc eBPF &amp; Observability: Thay thế kube-proxy bằng Cilium eBPF, cải thiện thông lượng mạng nội bộ 22% và giảm tải CPU của các node trung tâm.
- Xử lý sự cố Out-Of-Memory (OOMKilled) diện rộng: Tìm ra nguyên nhân gốc rễ (RCA) của hiện tượng memory leak âm ỉ trong cụm pod xử lý thanh toán, thiết lập giới hạn QoS Pod và Horizontal Pod Autoscaler dựa trên custom metrics.
- Chính sách DevSecOps: Chặn 100% các container image không có chữ ký số (unsigned images) hoặc có lỗ hổng CVE Critical trước khi được nạp vào Kubernetes Cluster.

## Cloud Operations Engineer | SmartLog Tech (03/2021 - 10/2023 | Hà Nội)

- Tự động hóa toàn bộ việc provisioning hệ thống staging/production cho 8 dự án logistics bằng Terraform.
- Thiết lập quy trình luân chuyển khóa bí mật (Secrets Rotation) tự động qua Vault Agent.

## 03 // CREDENTIALS &amp; LICENSES

- Certified Kubernetes Security Specialist (CKS) - Linux Foundation (2025)
- AWS Certified DevOps Engineer - Professional (DOP-C02) (2024)
- Kỹ sư Điện tử Viễn thông - Học viện Công nghệ Bưu chính Viễn thông (PTIT) (2016 - 2021)