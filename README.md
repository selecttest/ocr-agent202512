# OCR Agent with RAG

PDF 文件 OCR 分析 + RAG 向量搜尋問答系統

使用 GCP Vertex AI Gemini 進行 PDF 文件分析，自動儲存到 PostgreSQL + pgvector，支援向量搜尋問答。

---

## 功能特色

### OCR 辨識
- ✅ PDF 文件 OCR（支援中英文）
- ✅ 自動偵測文件類型
- ✅ 圖片、表格、印章等視覺元素辨識
- ✅ 大型 PDF 分批處理（自動分頁，每批 3 頁）
- ✅ 即時進度顯示（百分比、頁數、批次資訊）
- ✅ 支援取消辨識（可中斷處理）
- ✅ 頁碼自動修正（確保正確對應原始 PDF）

### 向量搜尋與問答
- ✅ 自動生成文字向量（Embedding，批次處理優化）
- ✅ RAG 向量搜尋問答
- ✅ 關鍵字搜索（key_values 表）
- ✅ 語義搜索（blocks 向量搜尋）
- ✅ 多文件選擇問答
- ✅ 參考來源顯示（含相似度分數）
- ✅ 查詢記錄與統計

### 使用者介面
- ✅ 響應式設計（RWD，支援手機、平板、桌面）
- ✅ 深色模式支援
- ✅ 檔案庫快速瀏覽
- ✅ 上傳進度條與取消功能
- ✅ 文件列表與詳情頁面
- ✅ AI 問答對話介面（固定視窗、可捲動）

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
                                    │  │  query_logs   (查詢記錄)     │   │
                                    │  └─────────────────────────────┘   │
                                    │           + pgvector                │
                                    └──────────────┬──────────────────────┘
                                                   │ 私人 IP 連線
┌──────────────┐    HTTP     ┌─────────────────────┴─────────────────────┐
│              │   :3000     │              GCP Compute Engine            │
│    User      │◄───────────►│              (ocr-agent VM)                │
│  Browser     │             │                                            │
└──────────────┘             │  ┌────────────────────────────────────┐   │
                             │  │         Frontend (Nuxt.js)          │   │
                             │  │                                     │   │
                             │  │  • pages/upload  - 上傳頁面         │   │
                             │  │  • pages/ask     - 問答頁面         │   │
                             │  │  • pages/documents - 文件列表        │   │
                             │  │  • composables/useApi - API 層     │   │
                             │  └─────────────┬──────────────────────┘   │
                             │                │ HTTP :8000                │
                             │                ▼                           │
                             │  ┌────────────────────────────────────┐   │
                             │  │         Backend (FastAPI)           │   │
                             │  │            api.py                   │   │
                             │  │                                     │   │
                             │  │  • POST /ocr/upload-stream         │   │
                             │  │  • GET  /documents                 │   │
                             │  │  • POST /ask                       │   │
                             │  │  • DELETE /documents/{id}          │   │
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
                             │  │ (向量生成)   │──│Gemini 2.5    │       │
                             │  │ (批次處理)   │  │Flash         │       │
                             │  └──────────────┘  └──────────────┘       │
                             └────────────────────────────────────────────┘
```

---

## 專案結構
```
ocr-agent202512/
├── backend/                    # 後端 API 服務
│   ├── api.py                  # FastAPI 主程式，處理所有 HTTP 請求
│   ├── ocr_agent.py            # OCR 核心模組，呼叫 Gemini 分析 PDF
│   ├── database.py             # 資料庫 CRUD 操作（含向量搜尋）
│   ├── embedding.py            # 使用 Vertex AI 生成文字向量（批次處理）
│   ├── update_embeddings.py    # 批次更新 Embedding 工具
│   ├── requirements.txt        # Python 套件依賴
│   └── venv/                   # Python 虛擬環境
│
├── frontend/                    # 前端 Web 應用
│   ├── app/
│   │   ├── app.vue             # 主應用程式佈局（含導航、檔案庫）
│   │   ├── app.config.ts       # 應用程式設定
│   │   ├── assets/
│   │   │   └── css/
│   │   │       └── main.css     # 全域樣式
│   │   ├── composables/
│   │   │   └── useApi.ts       # API 服務層（含進度追蹤）
│   │   └── pages/
│   │       ├── index.vue        # 首頁（功能介紹）
│   │       ├── upload/
│   │       │   └── index.vue    # 上傳頁面（含進度條、取消功能）
│   │       ├── ask/
│   │       │   └── index.vue    # AI 問答頁面（多文件選擇）
│   │       └── documents/
│   │           ├── index.vue    # 文件列表
│   │           └── [id].vue     # 文件詳情頁
│   ├── nuxt.config.ts          # Nuxt.js 設定
│   ├── package.json            # Node.js 套件依賴
│   └── tsconfig.json           # TypeScript 設定
│
└── README.md                   # 專案說明文件
```

### 後端檔案說明

| 檔案 | 功能 |
|------|------|
| `api.py` | FastAPI 主程式，定義所有 API 端點（含串流進度、取消功能） |
| `ocr_agent.py` | OCR 核心，呼叫 Gemini 分析 PDF，支援分頁處理與頁碼修正 |
| `database.py` | PostgreSQL 資料庫操作，包含向量搜尋、key_values 搜索 |
| `embedding.py` | 使用 Vertex AI text-embedding-004 批次生成向量（優化版） |
| `update_embeddings.py` | 批次工具，為舊資料補上 embedding（批次處理優化） |

### 前端檔案說明

| 檔案 | 功能 |
|------|------|
| `app.vue` | 主應用程式佈局，包含導航選單、檔案庫 Modal、主題切換 |
| `pages/index.vue` | 首頁，展示功能特色與使用流程 |
| `pages/upload/index.vue` | PDF 上傳頁面，含進度條、取消功能、辨識結果展示 |
| `pages/ask/index.vue` | AI 問答頁面，支援多文件選擇、參考數量設定 |
| `pages/documents/index.vue` | 文件列表頁面 |
| `pages/documents/[id].vue` | 文件詳情頁面，展示所有辨識內容 |
| `composables/useApi.ts` | API 服務層，封裝所有後端 API 呼叫（含串流進度） |

---

## API 端點

### 基本端點

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/` | GET | 健康檢查 | - |
| `/health` | GET | 健康檢查 | - |

### OCR 處理

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/ocr/upload` | POST | 上傳 PDF 進行 OCR（同步） | `file`: PDF 檔案, `save_to_db`: bool |
| `/ocr/upload-stream` | POST | 上傳 PDF 進行 OCR（串流進度） | `file`: PDF 檔案, `save_to_db`: bool |

### 文件管理

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/documents` | GET | 列出所有文件 | `limit`: int |
| `/documents/{id}` | GET | 取得文件詳情 | `doc_id`: UUID |
| `/documents/{id}/debug` | GET | 調試：查看原始 OCR 結果 | `doc_id`: UUID |
| `/documents/{id}` | DELETE | 刪除文件 | `doc_id`: UUID |
| `/documents/batch-delete` | POST | 批次刪除文件 | `document_ids`: List[str] |

### RAG 問答

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/ask` | POST | RAG 問答 | `question`: str, `top_k`: int, `document_ids`: List[str] |

### 查詢記錄

| 端點 | 方法 | 功能 | 參數 |
|------|------|------|------|
| `/query-logs` | GET | 取得查詢記錄 | `limit`: int, `days`: int |
| `/query-stats` | GET | 取得查詢統計 | `days`: int |

### 範例請求

#### 上傳 PDF（同步）
```bash
curl -X POST "http://localhost:8000/ocr/upload?save_to_db=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

#### 上傳 PDF（串流進度）
```bash
curl -X POST "http://localhost:8000/ocr/upload-stream?save_to_db=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
# 返回 Server-Sent Events (SSE) 格式的進度更新
```

#### RAG 問答（所有文件）
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "這份文件的主要內容是什麼？",
    "top_k": 10
  }'
```

#### RAG 問答（指定文件）
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "這份履歷的學歷是什麼？",
    "top_k": 5,
    "document_ids": ["uuid-1", "uuid-2"]
  }'
```

#### 取得文件列表
```bash
curl "http://localhost:8000/documents?limit=20"
```

#### 刪除文件
```bash
curl -X DELETE "http://localhost:8000/documents/{doc_id}"
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

### query_logs（查詢記錄表）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| question | TEXT | 使用者問題 |
| answer | TEXT | AI 回答 |
| document_ids | UUID[] | 關聯的文件 ID 列表 |
| search_keywords | TEXT[] | 搜尋使用的關鍵字 |
| matched_blocks | JSONB | 匹配的區塊資訊 |
| similarity_scores | FLOAT[] | 相似度分數 |
| ip_address | VARCHAR | 使用者 IP 地址 |
| user_agent | TEXT | 使用者代理 |
| query_time | TIMESTAMP | 查詢時間 |
| response_time_ms | INT | 回應時間（毫秒） |
| status | VARCHAR | 狀態（success/error） |

---

## 資料流程

### 1. 上傳 PDF 流程（含進度追蹤）
```
前端 (Nuxt.js)
      │
      ▼
┌─────────────────┐
│  upload/index   │  選擇 PDF 檔案
│  .vue           │  顯示進度條
└────────┬────────┘  支援取消功能
         │
         │ HTTP POST (multipart/form-data)
         │ SSE 串流進度更新
         ▼
┌─────────────────┐
│  api.py         │
│  /ocr/upload-   │  接收檔案
│  stream         │  串流返回進度
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ocr_agent.py   │  ──► Vertex AI Gemini 2.5 Flash Lite
│  分批處理 PDF    │      (每批 3 頁，並行處理)
│  頁碼修正       │      支援取消中斷
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  ──► Cloud SQL PostgreSQL
│  批次儲存       │      儲存 blocks、key_values、images
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  embedding.py   │  ──► Vertex AI Embeddings
│  批次生成向量    │      (text-embedding-004)
│  (100個/批)     │      批次處理優化
└────────┬────────┘
         │
         ▼
    更新 DB 中的
    embedding 欄位
    (背景處理)
```

### 2. RAG 問答流程
```
前端 (Nuxt.js)
      │
      ▼
┌─────────────────┐
│  ask/index.vue  │  輸入問題
│                 │  選擇文件（可多選）
│                 │  設定參考數量 (Top K)
└────────┬────────┘
         │
         │ HTTP POST (JSON)
         ▼
┌─────────────────┐
│  api.py         │
│  /ask           │  接收問題與文件 ID
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  關鍵字提取      │  從問題提取關鍵字
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│  database.py    │  │  embedding.py   │
│  search_key_    │  │  問題轉向量      │
│  values()       │  │                 │
│  (關鍵字搜索)    │  └────────┬────────┘
└────────┬────────┘           │
         │                    │
         │ 如果結果不足        │
         │                    ▼
         │          ┌─────────────────┐
         │          │  database.py    │
         │          │  search_blocks  │
         │          │  (向量搜尋)      │
         │          └────────┬────────┘
         │                   │
         └───────────┬───────┘
                     │
                     ▼
┌─────────────────┐
│  擴展上下文      │  獲取相關頁面內容
│  (頁面範圍)      │  (當前頁 + 後 2 頁)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini 2.5     │  ──► 組合 context + 問題
│  Flash Lite     │      生成自然語言回答
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  記錄查詢日誌    │  儲存到 query_logs 表
└────────┬────────┘
         │
         ▼
    回傳答案 + 來源
    (含相似度分數)
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

| PDF 頁數 | 每批頁數 | 說明 |
|---------|---------|------|
| 1-3 頁 | 全部一次處理 | 小文件單次處理 |
| 4+ 頁 | 每批 3 頁 | 統一批次大小，確保不超過 token 限制 |

**優化特性**：
- 批次並行處理（可同時處理多個批次）
- 支援取消中斷（每秒檢查取消狀態）
- 頁碼自動修正（確保正確對應原始 PDF）
- 進度即時回傳（SSE 串流更新）

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

### 後端技術

| 項目 | 技術 | 版本 |
|------|------|------|
| **程式語言** | Python | 3.14.2 |
| **API 框架** | FastAPI | >=0.104.0 |
| **ASGI 伺服器** | Uvicorn | >=0.24.0 |
| **OCR 模型** | Vertex AI Gemini 2.5 Flash Lite  | - |
| **Embedding 模型** | Vertex AI text-embedding-004 | - |
| **資料庫** | Cloud SQL PostgreSQL | 17 |
| **向量搜尋** | pgvector | - |
| **資料庫驅動** | psycopg2-binary | >=2.9.0 |
| **PDF 處理** | PyMuPDF (fitz) | >=1.23.0 |
| **GCP SDK** | google-cloud-aiplatform | >=1.38.0 |
| **資料驗證** | Pydantic | >=2.0.0 |
| **雲端平台** | Google Cloud Platform | - |

### 前端技術

| 項目 | 技術 | 版本 |
|------|------|------|
| **框架** | Nuxt.js | ^4.2.2 |
| **UI 框架** | Nuxt UI | ^4.3.0 |
| **程式語言** | TypeScript | ^5.9.3 |
| **CSS 框架** | Tailwind CSS | ^6.14.0 |
| **圖標庫** | Lucide Icons | ^0.562.0 |
| **HTTP 客戶端** | Axios | ^1.13.2 |
| **工具庫** | VueUse | ^14.1.0 |
| **程式碼檢查** | ESLint | ^9.39.2 |
| **建置工具** | Vite (內建於 Nuxt) | - |

### 基礎設施

| 項目 | 技術 | 說明 |
|------|------|------|
| **運算平台** | GCP Compute Engine | VM 執行環境 |
| **資料庫服務** | GCP Cloud SQL | PostgreSQL 託管服務 |
| **AI 服務** | Vertex AI | Gemini 與 Embedding API |
| **向量擴展** | pgvector | PostgreSQL 向量搜尋擴展 |
| **服務管理** | Systemd | Linux 服務管理 |
| **版本控制** | Git | 程式碼版本管理 |

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
