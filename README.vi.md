# HistoriAI Agent 📜

> **Hệ thống Agentic RAG Học thuật Nghiên cứu Tài liệu Lịch sử Việt Nam (1945–1975)**

[![Language](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Langfuse Tracing](https://img.shields.io/badge/LLM_Tracing-Langfuse-orange.svg)](https://cloud.langfuse.com)

HistoriAI là một hệ thống AI học thuật nghiên cứu theo mô hình **Agentic RAG** phục vụ cho việc tra cứu và đối chiếu tư liệu lịch sử Việt Nam giai đoạn 1945–1975. Hệ thống tích hợp các kỹ thuật truy xuất nâng cao và quy trình kiểm chứng trích dẫn tự động để giải quyết triệt để vấn đề hallucination (ảo tưởng thông tin) đối với các sự kiện lịch sử nhạy cảm.

---

## ⚡ Các Điểm Nhấn Công Nghệ Cốt Lõi

*   **Bộ máy Tìm kiếm Lai (Hybrid Retrieval Engine)**: Kết hợp tìm kiếm lexical chính xác qua Meilisearch (BM25) và tìm kiếm semantic ngữ nghĩa qua Qdrant (Dense Vectors). Kết quả được hợp nhất bằng thuật toán **Reciprocal Rank Fusion (RRF)** đảm bảo độ phủ thông tin tối đa.
*   **Điều phối RAG theo mô hình Agentic (LangGraph)**: Sử dụng LangGraph để phân loại độ phức tạp của câu hỏi (Complexity Classifier), phân loại chủ đề (Domain Classifier) và tự động mở rộng truy vấn (Query Expander/HyDE) trước khi tìm kiếm.
*   **Quy trình Kiểm chứng Trích dẫn (Grounded Citation Pipeline)**: Sử dụng các mô hình NLI (Natural Language Inference) để kiểm chứng chéo câu trả lời của LLM với tài liệu gốc, loại bỏ hoàn toàn các trích dẫn giả mạo và thông tin thiếu căn cứ.
*   **Hạ tầng Đầy đủ (Full-Stack & Observability)**: UI React + Vite trực quan, Backend FastAPI hiệu năng cao kèm hệ thống Worker nền (RQ + Redis) xử lý nạp tài liệu bất đồng bộ. Tích hợp sẵn Langfuse để trace LLM và Grafana để giám sát hệ thống.

---

## 🚀 Khởi Động Nhanh (Docker Compose)

Nếu bạn chỉ muốn thử nghiệm hoặc chạy demo nhanh toàn bộ hệ thống mà không cần cài đặt môi trường cục bộ:

```bash
# 1. Clone dự án và truy cập thư mục
git clone <repo-url> Vie_history
cd Vie_history

# 2. Tạo cấu hình môi trường từ mẫu
cp .env.example .env
# Chỉnh sửa .env để điền LLM API Key (ví dụ: OPENAI_API_KEY)

# 3. Tạo mạng Docker và khởi động dịch vụ
docker network create historiai-network 2>/dev/null || true
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build
```

Ứng dụng web sẽ khả dụng tại: `http://localhost:12702`

---

## 🛠️ Quy Trình Cài Đặt Phát Triển (Local Setup)

### Bước 1: Khởi động các Dịch vụ Docker Core

```bash
docker network create historiai-network 2>/dev/null || true
docker compose up -d
```

### Bước 2: Cài đặt Backend API

```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
ALEMBIC_AUTOCOMMIT=true alembic upgrade head
```

### Bước 3: Cài đặt Frontend

```bash
cd apps/web
npm install
```

---

## ⚙️ Chạy Môi Trường Phát Triển

Mở **3 cửa sổ Terminal** riêng biệt và chạy các lệnh sau:

*   **Terminal 1 (Backend API)**:
    ```bash
    cd apps/api && source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
    ```
*   **Terminal 2 (Background Worker)**:
    ```bash
    cd apps/api && source venv/bin/activate
    rq worker ingest-queue --url redis://localhost:12704/0
    ```
*   **Terminal 3 (Frontend Web)**:
    ```bash
    cd apps/web
    npm run dev
    ```

---

## 🗺️ Bản Đồ Kiến Trúc Hệ Thống

```
                     ┌───────────────────────────────────┐
                     │          React + Vite UI          │
                     │       http://localhost:12702      │
                     └─────────────────┬─────────────────┘
                                       │ HTTP / SSE
                     ┌─────────────────▼─────────────────┐
                     │          FastAPI Backend          │
                     │       http://localhost:12701      │
                     └─────────────────┬─────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            │                                                     │
 ┌──────────▼──────────┐                               ┌──────────▼──────────┐
 │   Qdrant Vector     │                               │ Meilisearch (BM25)  │
 │ (Dense Embeddings)  │                               │  (Lexical Search)   │
 └─────────────────────┘                               └─────────────────────┘
```

Quy trình xử lý Query:
```
Query ──► Complexity/Domain Classifier ──► Query Expander (HyDE)
      ──► Hybrid Retrieval (Dense & BM25) ──► RRF Fusion 
      ──► Cross-Encoder Reranker ──► Guarded Synthesizer
      ──► Citation Verifier (NLI check) ──► SSE Stream Response
```

---

## 📊 Đánh Giá & Kiểm Thử (Evaluation)

Dự án sử dụng bộ dataset chuẩn gồm 50 câu hỏi vàng (Golden Dataset) để đánh giá học thuật thông qua framework RAGAS:

```bash
cd evals
source ../apps/api/venv/bin/activate

# Chạy đánh giá RAGAS đầy đủ
python run_ragas.py

# Đánh giá hiệu năng bộ truy xuất (MRR, Hit@k, NDCG)
python eval_retrieval.py
```

### Chỉ số mục tiêu đạt được:
| Chỉ số (Metric) | Giá trị Mục tiêu |
|---|---|
| RAGAS Faithfulness | > 0.85 |
| Citation Precision | > 0.80 |
| Citation Recall | > 0.80 |
| Wilcoxon p-value | < 0.05 |

---

## 📋 Tra Cứu Lệnh Nhanh (Makefile Reference)

| Lệnh (Command) | Chức năng (Function) |
|---|---|
| `make dev-api` | Khởi động máy chủ backend API |
| `make dev-web` | Khởi động máy chủ frontend React |
| `make test-api` | Chạy toàn bộ suite kiểm thử backend pytest |
| `make db-migrate` | Cập nhật database schema thông qua Alembic |
| `make lint-api` | Kiểm tra định dạng code backend bằng Ruff |
| `make fmt-api` | Tự động sửa định dạng code backend bằng Ruff |
| `make clean` | Dọn dẹp cache, log và file rác phát sinh |

---

## 🔌 Danh Sách Các Cổng Dịch Vụ (Ports)

*   **FastAPI API**: `12701`
*   **React Frontend**: `12702`
*   **PostgreSQL**: `12703`
*   **Redis**: `12704`
*   **Qdrant**: `12705` (REST) | `12706` (gRPC)
*   **Meilisearch**: `12707`
*   **Langfuse**: `12708`
*   **Grafana**: `13000` (Tài khoản: `admin` / Mật khẩu: `historiai`)
*   **Prometheus**: `9090`

---

## 📄 Bản Quyền & Đóng Góp
Dự án được phân phối dưới giấy phép **MIT License**. Mọi đóng góp phát triển vui lòng tham khảo file `CONTRIBUTING.md`.
