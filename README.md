# OCR Agent with RAG

PDF 文件 OCR 分析 + RAG 向量搜尋問答系統

使用 GCP Vertex AI Gemini 進行 PDF 文件分析，自動儲存到 PostgreSQL + pgvector，支援向量搜尋問答。

---

## 功能特色

- ✅ PDF 文件 OCR（支援中英文）
- ✅ 自動偵測文件類型
- ✅ 圖片、表格、印章等視覺元素辨識
- ✅ 大型 PDF 分批處理（自動分頁）
- ✅ 自動生成文字向量（Embedding）
- ✅ RAG 向量搜尋問答
- ✅ 九宮格分區定位

---

## 系統架構
```
                                    ┌─────────────────────────────────────┐
                                    │           GCP Cloud SQL             │
                                    │         (PostgreSQL 15)             │
                                    │                                     │
                                    │  ┌─────────────────────────────┐   │
                                    │  │  documents    (文件主表)     │   │
                                    │  │  blocks       (區塊+向量)    │   │
                                    │  │  key_values   (鍵值對)       │   │
                                    │  │  images       (圖片+向量)    │   │
                                    │  └─────────────────────────────┘   │
                                    │           + pgvector                │
                                    └──────────────┬──────────────────────┘
                                                   │ 私人 IP 連線
┌──────────────┐    HTTP     ┌─────────────────────┴─────────────────────┐
│              │   :8000     │              GCP Compute Engine            │
│    User      │◄───────────►│              (ocr-agent VM)                │
│              │             │                                            │
└──────────────┘             │  ┌────────────────────────────────────┐   │
                             │  │            api.py                   │   │
                             │  │         (FastAPI 服務)              │   │
                             │  │                                     │   │
                             │  │  • POST /ocr/upload  - OCR 上傳     │   │
                             │  │  • GET  /documents   - 文件列表     │   │
                             │  │  • GET  /documents/{id} - 文件詳情  │   │
                             │  │  • POST /ask         - RAG 問答     │   │
                             │  └─────────────┬──────────────────────┘   │
                             │                │                           │
                             │    ┌───────────┴───────────┐              │
                             │    ▼                       ▼              │
                             │  ┌──────────────┐  ┌──────────────┐       │
                             │  │ ocr_agent.py │  │ database.py  │       │
                             │  │  (OCR 分析)  │  │  (DB 操作)   │       │
                             │  └──────┬───────┘  └──────────────┘       │
                             │         │                                  │
                             │         ▼                                  │
                             │  ┌──────────────┐  ┌──────────────┐       │
                             │  │ embedding.py │  │Vertex AI     │       │
                             │  │ (向量生成)   │──│Gemini 2.0    │       │
                             │  └──────────────┘  └──────────────┘       │
                             └────────────────────────────────────────────┘
```

---

## 專案結構
```
ocr-agent/
├── api.py                  # FastAPI 主程式，處理所有 HTTP 請求
├── ocr_agent.py            # OCR 核心模組，呼叫 Gemini 分析 PDF
├── database.py             # 資料庫 CRUD 操作
├── embedding.py            # 使用 Vertex AI 生成文字向量
├── update_embeddings.py    # 批次更新 Embedding 工具
├── requirements.txt        # Python 套件依賴
├── .env.example            # 環境變數範本
└── README.md               # 專案說明文件
```

### 檔案說明

| 檔案 | 功能 |
|------|------|
| `api.py` | FastAPI 主程式，定義所有 API 端點 |
| `ocr_agent.py` | OCR 核心，呼叫 Gemini 分析 PDF，支援分頁處理 |
| `database.py` | PostgreSQL 資料庫操作，包含向量搜尋 |
| `embedding.py` | 使用 Vertex AI text-embedding-004 生成向量 |
| `update_embeddings.py` | 批次工具，為舊資料補上 embedding |

---

## API 端點

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/` | GET | 健康檢查 | - |
| `/health` | GET | 健康檢查 | - |
| `/ocr/upload` | POST | 上傳 PDF 進行 OCR | `file`: PDF 檔案, `save_to_db`: bool |
| `/documents` | GET | 列出所有文件 | `limit`: int |
| `/documents/{id}` | GET | 取得文件詳情 | `doc_id`: UUID |
| `/ask` | POST | RAG 問答 | `question`: str, `top_k`: int |

### 範例請求

#### 上傳 PDF
```bash
curl -X POST "http://localhost:8000/ocr/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

#### RAG 問答
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "這份文件的主要內容是什麼？", "top_k": 5}'
```

---

## 資料庫結構

### documents（文件主表）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| filename | VARCHAR | 檔案名稱 |
| detected_type | VARCHAR | 文件類型 |
| language | VARCHAR | 語言 |
| total_pages | INT | 總頁數 |
| upload_time | TIMESTAMP | 上傳時間 |
| processing_time_seconds | FLOAT | 處理時間 |
| summary | TEXT | 摘要 |
| metadata | JSONB | 其他資訊 |

### blocks（區塊表，含向量）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| document_id | UUID | 關聯文件 |
| block_id | VARCHAR | 區塊編號 |
| block_type | VARCHAR | 類型（text/photo/table...） |
| page | INT | 頁碼 |
| region | VARCHAR | 位置（左上/中央...） |
| content | TEXT | 內容 |
| confidence | FLOAT | 信心度 |
| embedding | vector(768) | 向量（用於 RAG 搜尋） |

### key_values（鍵值對表）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| document_id | UUID | 關聯文件 |
| key | VARCHAR | 鍵 |
| value | TEXT | 值 |
| page | INT | 頁碼 |

### images（圖片表）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| document_id | UUID | 關聯文件 |
| image_type | VARCHAR | 圖片類型 |
| page | INT | 頁碼 |
| region | VARCHAR | 位置 |
| description | TEXT | 描述 |
| embedding | vector(768) | 向量 |

---

## 資料流程

### 1. 上傳 PDF 流程
```
User 上傳 PDF
      │
      ▼
┌─────────────────┐
│  api.py         │
│  /ocr/upload    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ocr_agent.py   │  ──► Vertex AI Gemini 2.0
│  分頁處理 PDF    │      (每批 5-10 頁)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  ──► Cloud SQL PostgreSQL
│  儲存結果       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  embedding.py   │  ──► Vertex AI Embeddings
│  生成向量       │      (text-embedding-004)
└────────┬────────┘
         │
         ▼
    更新 DB 中的
    embedding 欄位
```

### 2. RAG 問答流程
```
User 提問
      │
      ▼
┌─────────────────┐
│  api.py         │
│  /ask           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  embedding.py   │  ──► 問題轉向量
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  ──► pgvector 向量搜尋
│  search_blocks  │      (Cosine Similarity)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini 2.0     │  ──► 組合 context + 問題
│  生成回答       │      生成自然語言回答
└────────┬────────┘
         │
         ▼
    回傳答案 + 來源
```

---

## OCR 輸出格式

### Block 類型

| 類型 | 說明 |
|------|------|
| **視覺元素** | |
| `photo` | 人物照片 |
| `logo` | Logo、商標 |
| `chart` | 數據圖表 |
| `diagram` | 流程圖、示意圖 |
| `icon` | 小圖示 |
| `stamp` | 印章 |
| `signature` | 簽名 |
| `barcode` | 條碼、QR Code |
| `figure` | 其他圖片 |
| **文字元素** | |
| `header` | 頁首、文件標題 |
| `section_title` | 章節標題 |
| `text` | 正文段落 |
| `list` | 列表 |
| `table` | 表格 |
| `form_field` | 表單欄位 |
| `footer` | 頁尾 |
| `page_number` | 頁碼 |

### 九宮格分區
```
┌─────────┬─────────┬─────────┐
│  左上   │  中上   │  右上   │
├─────────┼─────────┼─────────┤
│  左中   │  中央   │  右中   │
├─────────┼─────────┼─────────┤
│  左下   │  中下   │  右下   │
└─────────┴─────────┴─────────┘
```

### 分頁處理策略

| PDF 頁數 | 每批頁數 |
|---------|---------|
| 1-10 頁 | 全部一次處理 |
| 11-30 頁 | 每批 5 頁 |
| 31-100 頁 | 每批 8 頁 |
| 100+ 頁 | 每批 10 頁 |

---

## 環境變數
```bash
# GCP 設定
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1

# 資料庫設定
DB_HOST=cloud-sql-private-ip
DB_PORT=5432
DB_NAME=ocr_rag
DB_USER=postgres
DB_PASSWORD=your-password
```

---

## 安裝與部署

### 本地開發
```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝套件
pip install -r requirements.txt

# 設定環境變數
export GCP_PROJECT_ID="your-project-id"
export GCP_LOCATION="us-central1"
export DB_HOST="your-db-host"
export DB_PASSWORD="your-password"

# 啟動服務
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Systemd 服務（正式環境）
```bash
# 啟動
sudo systemctl start ocr-agent

# 停止
sudo systemctl stop ocr-agent

# 重啟
sudo systemctl restart ocr-agent

# 查看狀態
sudo systemctl status ocr-agent

# 查看 log
sudo journalctl -u ocr-agent -f
```

---

## 技術棧

| 項目 | 技術 |
|------|------|
| **OCR 模型** | Vertex AI Gemini 2.0 Flash |
| **Embedding 模型** | Vertex AI text-embedding-004 |
| **資料庫** | Cloud SQL PostgreSQL 15 |
| **向量搜尋** | pgvector |
| **API 框架** | FastAPI |
| **PDF 處理** | PyMuPDF |
| **雲端平台** | Google Cloud Platform |

---

## 成本估算

| 項目 | 預估月費 (USD) |
|------|---------------|
| Compute Engine (e2-medium) | ~$25 |
| Cloud SQL (db-f1-micro) | ~$10 |
| Vertex AI Gemini API | 依用量 |
| Vertex AI Embedding API | 依用量 |

---

## License

MIT License
