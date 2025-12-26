"""
OCR API 服務 - 含資料庫儲存
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging
import time

from ocr_agent import UniversalOCRAgent
from database import db
from embedding import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "aic-rain-playground")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

app = FastAPI(
    title="OCR RAG API",
    description="OCR 文件處理 + RAG 問答服務",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_agent: Optional[UniversalOCRAgent] = None


def get_ocr_agent() -> UniversalOCRAgent:
    global ocr_agent
    if ocr_agent is None:
        ocr_agent = UniversalOCRAgent(project_id=PROJECT_ID, location=LOCATION)
    return ocr_agent


# ==================== 資料模型 ====================

class OCRResponse(BaseModel):
    success: bool
    document_id: Optional[str] = None
    total_pages: int
    detected_type: str
    language: str
    blocks: List[Dict]
    full_text: str
    key_value_pairs: List[Dict]
    tables: List[Dict]
    images_summary: Optional[Any] = None
    processing_time: Optional[Dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    project_id: str
    location: str
    version: str


class DocumentListResponse(BaseModel):
    documents: List[Dict]


class QuestionRequest(BaseModel):
    question: str
    top_k: int = 10  # 增加搜索數量以獲得更多相關內容
    document_ids: Optional[List[str]] = None  # 可選：指定要查詢的文件 ID 列表


class AnswerResponse(BaseModel):
    answer: str
    sources: List[Dict]


class DeleteResponse(BaseModel):
    success: bool
    message: str


class BatchDeleteRequest(BaseModel):
    document_ids: List[str]


class BatchDeleteResponse(BaseModel):
    deleted: int
    failed: int
    deleted_ids: List[str]


class QueryLogResponse(BaseModel):
    logs: List[Dict]


class QueryStatsResponse(BaseModel):
    total_queries: int
    unique_ips: int
    avg_response_time: Optional[float]
    success_count: int
    error_count: int
    daily_counts: List[Dict]


# ==================== API 端點 ====================

@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        status="healthy", 
        project_id=PROJECT_ID, 
        location=LOCATION, 
        version="3.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy", 
        project_id=PROJECT_ID, 
        location=LOCATION, 
        version="3.0.0"
    )


@app.post("/ocr/upload", response_model=OCRResponse)
async def ocr_upload(file: UploadFile = File(...), save_to_db: bool = True):
    """
    上傳 PDF 並進行 OCR
    - save_to_db: 是否儲存到資料庫（預設 True）
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支援 PDF 檔案")
    
    logger.info(f"收到檔案: {file.filename}")
    
    try:
        content = await file.read()
        agent = get_ocr_agent()
        result = agent.process_bytes(content)
        result_dict = result.to_dict()
        
        document_id = None
        
        # 儲存到資料庫
        if save_to_db and result_dict.get("success"):
            try:
                document_id = db.save_document(result_dict, file.filename)
                logger.info(f"文件已儲存到資料庫，ID: {document_id}")
                
                # 生成 embedding
                update_embeddings_for_document(document_id)
                
            except Exception as e:
                logger.error(f"儲存到資料庫失敗: {e}")
        
        return OCRResponse(
            success=result_dict.get("success", False),
            document_id=document_id,
            total_pages=result_dict.get("total_pages", 0),
            detected_type=result_dict.get("detected_type", ""),
            language=result_dict.get("language", ""),
            blocks=result_dict.get("blocks", []),
            full_text=result_dict.get("full_text", ""),
            key_value_pairs=result_dict.get("key_value_pairs", []),
            tables=result_dict.get("tables", []),
            images_summary=result_dict.get("images_summary"),
            processing_time=result_dict.get("processing_time"),
            error=result_dict.get("error")
        )
        
    except Exception as e:
        logger.error(f"處理錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(limit: int = 20):
    """列出所有已處理的文件"""
    documents = db.list_documents(limit)
    return DocumentListResponse(documents=documents)


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """取得特定文件的詳細資料"""
    result = db.get_document(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")
    return result


@app.get("/documents/{doc_id}/debug")
async def debug_document(doc_id: str):
    """Debug：查看文件的所有 blocks 內容"""
    result = db.get_document(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 整理輸出
    debug_info = {
        "document": {
            "id": str(result["document"]["id"]),
            "filename": result["document"]["filename"],
            "detected_type": result["document"]["detected_type"],
            "total_pages": result["document"]["total_pages"],
            "summary": result["document"]["summary"]
        },
        "blocks_count": len(result["blocks"]),
        "blocks": [
            {
                "page": b["page"],
                "type": b["block_type"],
                "region": b["region"],
                "content": b["content"],
                "has_embedding": b.get("embedding") is not None
            }
            for b in result["blocks"]
        ],
        "key_values": result["key_values"]
    }
    return debug_info


@app.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str):
    """刪除特定文件及其所有相關資料"""
    logger.info(f"收到刪除文件請求: {doc_id}")
    
    success = db.delete_document(doc_id)
    
    if success:
        return DeleteResponse(
            success=True,
            message=f"文件 {doc_id} 已成功刪除"
        )
    else:
        raise HTTPException(status_code=404, detail="文件不存在或刪除失敗")


@app.post("/documents/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_documents(request: BatchDeleteRequest):
    """批次刪除多個文件"""
    logger.info(f"收到批次刪除請求: {len(request.document_ids)} 個文件")
    
    result = db.delete_documents(request.document_ids)
    
    return BatchDeleteResponse(
        deleted=result["deleted"],
        failed=result["failed"],
        deleted_ids=result["deleted_ids"]
    )


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest, req: Request):
    """
    RAG 問答：根據已上傳的文件回答問題
    - document_ids: 可選，指定要查詢的文件 ID 列表（為空時搜尋所有文件）
    """
    start_time = time.time()
    question = request.question
    top_k = request.top_k
    document_ids = request.document_ids
    
    # 取得使用者資訊
    client_ip = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent", "")
    
    # 嘗試取得真實 IP（如果經過 proxy）
    forwarded_for = req.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    logger.info(f"收到問題: {question} (來自 IP: {client_ip})")
    if document_ids:
        logger.info(f"限定查詢文件: {document_ids}")
    
    answer = None
    sources = []
    status = "success"
    similarity_scores = []
    matched_blocks_info = []
    relevant_blocks = []  # 初始化，避免未定義錯誤
    
    try:
        # 1. 從問題中提取關鍵字（用於 key_values 搜索）
        stop_words = {'是', '什麼', '有', '哪些', '嗎', '呢', '的', '了', '在', '這', '那', '請', '問', '告訴', '我', '你', '他', '她', '它', '們'}
        keywords = [w for w in question if len(w) >= 2 and w not in stop_words]
        
        # 加入完整問題中的關鍵詞組
        keyword_phrases = []
        common_phrases = [
            # 履歷相關
            '學歷', '工作經歷', '技能', '經驗', '技術', '專案', '專案經歷', 
            '聯絡', 'email', '電話', '姓名', '技術架構', 'Skills', '主修', '科系', '公司', '職位',
            # 圖片相關
            '圖片', '地圖', '照片', '圖表', 'logo', '標誌', '位置', '交通', '停車',
            # 一般文件
            '表格', '摘要', '總結', '內容', '說明'
        ]
        for phrase in common_phrases:
            if phrase.lower() in question.lower():
                keyword_phrases.append(phrase)
        
        all_keywords = list(set(keywords + keyword_phrases))
        logger.info(f"提取的關鍵字: {all_keywords}")
        
        # 2. 【優先】用關鍵字搜索 key_values
        matched_key_values = db.search_key_values(all_keywords, document_ids)
        
        context_parts = []
        expanded_blocks = []
        use_block_search = True  # 是否需要搜索 blocks
        
        # 如果 key_values 找到足夠的結果（>= 2 條），就不搜索 blocks
        if matched_key_values and len(matched_key_values) >= 2:
            logger.info(f"key_values 找到 {len(matched_key_values)} 筆結果，跳過 blocks 搜索")
            use_block_search = False
            
            # 組合 key_values 結果
            kv_text = "\n".join([
                f"- {kv['key']}: {kv['value']} (第{kv['page']}頁)" 
                for kv in matched_key_values
            ])
            context_parts.append(f"[關鍵資訊]\n{kv_text}")
            
            # 根據 key_values 的頁碼，獲取相關頁面的 blocks 內容作為補充
            kv_pages = set()
            kv_doc_ids = set()
            for kv in matched_key_values:
                if kv.get("page"):
                    kv_pages.add(kv["page"])
                if kv.get("document_id"):
                    kv_doc_ids.add(str(kv["document_id"]))
            
            # 獲取相關頁面的 blocks 作為補充上下文
            for doc_id in kv_doc_ids:
                if kv_pages:
                    min_page = min(kv_pages)
                    max_page = max(kv_pages) + 1  # 多取一頁
                    extra_blocks = db.get_blocks_by_page_range(doc_id, min_page, max_page)
                    expanded_blocks.extend(extra_blocks)
            
            logger.info(f"從 key_values 相關頁面獲取 {len(expanded_blocks)} 個 blocks 作為補充")
        
        # 3. 如果 key_values 沒找到足夠結果，才搜索 blocks
        if use_block_search:
            logger.info("key_values 結果不足，執行 blocks 向量搜索")
            
            # 將問題轉成 embedding
            question_embedding = embedding_service.get_embedding(question)
            
            if not question_embedding:
                status = "error"
                raise HTTPException(status_code=500, detail="無法生成問題的 embedding")
            
            # 向量搜尋 blocks
            relevant_blocks = db.search_blocks(
                question_embedding, 
                limit=top_k,
                document_ids=document_ids
            )
            
            if not relevant_blocks and not matched_key_values:
                msg = "抱歉，在"
                if document_ids:
                    msg += f"選擇的 {len(document_ids)} 份文件中"
                else:
                    msg += "已上傳的文件中"
                msg += "找不到相關資訊。"
                answer = msg
                
                response_time_ms = int((time.time() - start_time) * 1000)
                db.log_query(
                    question=question,
                    answer=answer,
                    document_ids=document_ids,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    response_time_ms=response_time_ms,
                    status=status
                )
                
                return AnswerResponse(answer=msg, sources=[])
            
            # 收集匹配資訊
            for block in relevant_blocks:
                similarity_scores.append(block.get("similarity", 0))
                matched_blocks_info.append({
                    "block_id": str(block.get("id")),
                    "document_id": str(block.get("document_id")),
                    "filename": block.get("filename"),
                    "page": block.get("page"),
                    "similarity": block.get("similarity")
                })
            
            # 擴展搜索：獲取搜索結果所在頁及後續 2 頁
            seen_block_ids = set()
            doc_page_ranges = {}
            
            for block in relevant_blocks:
                doc_id = str(block.get("document_id"))
                page = block.get("page", 1)
                
                if doc_id not in doc_page_ranges:
                    doc_page_ranges[doc_id] = set()
                
                for p in range(page, page + 3):
                    doc_page_ranges[doc_id].add(p)
            
            for doc_id, pages in doc_page_ranges.items():
                min_page = min(pages)
                max_page = max(pages)
                
                logger.info(f"擴展搜索: 文件 {doc_id}, 頁碼 {min_page}-{max_page}")
                
                extra_blocks = db.get_blocks_by_page_range(doc_id, min_page, max_page)
                for b in extra_blocks:
                    block_id = str(b.get("id"))
                    if block_id not in seen_block_ids:
                        seen_block_ids.add(block_id)
                        expanded_blocks.append(b)
            
            logger.info(f"原始搜索結果: {len(relevant_blocks)} 個, 擴展後: {len(expanded_blocks)} 個")
            
            # 如果有 key_values 結果，也加入
            if matched_key_values:
                kv_text = "\n".join([
                    f"- {kv['key']}: {kv['value']} (第{kv['page']}頁)" 
                    for kv in matched_key_values
                ])
                context_parts.append(f"[關鍵資訊]\n{kv_text}")
        
        # 4. 組合 blocks 內容到 context
        expanded_blocks.sort(key=lambda x: (str(x.get("document_id")), x.get("page", 0)))
        
        current_doc = None
        current_page = None
        page_content = []
        
        for block in expanded_blocks:
            doc_id = str(block.get("document_id"))
            page = block.get("page")
            filename = block.get("filename", "未知文件")
            
            # 如果換頁或換文件，先儲存上一頁的內容
            if (current_doc != doc_id or current_page != page) and page_content:
                context_parts.append(
                    f"[來源: {current_filename}, 第{current_page}頁]\n" + "\n".join(page_content)
                )
                page_content = []
            
            current_doc = doc_id
            current_page = page
            current_filename = filename
            
            if block.get("content"):
                page_content.append(block["content"])
        
        # 加入最後一頁的內容
        if page_content:
            context_parts.append(
                f"[來源: {current_filename}, 第{current_page}頁]\n" + "\n".join(page_content)
            )
        
        # 如果有指定文件，加入文件摘要
        if document_ids:
            for doc_id in document_ids:
                doc_data = db.get_document(doc_id)
                if doc_data and doc_data["document"].get("summary"):
                    context_parts.append(
                        f"[文件摘要: {doc_data['document']['filename']}]\n{doc_data['document']['summary']}"
                    )
        
        context = "\n\n".join(context_parts)
        logger.info(f"組合的 context 長度: {len(context)} 字元")
        
        # 4. 呼叫 Gemini 生成回答
        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel("gemini-2.0-flash")
        
        prompt = f"""根據以下文件內容回答問題。如果文件中沒有相關資訊，請說明。

文件內容：
{context}

問題：{question}

請用繁體中文回答："""
        
        response = model.generate_content(prompt)
        answer = response.text
        
        # 5. 回傳結果
        sources = [
            {
                "filename": b["filename"],
                "page": b["page"],
                "content": b["content"][:100] + "..." if len(b["content"]) > 100 else b["content"],
                "similarity": round(b["similarity"], 3) if b.get("similarity") else None
            }
            for b in relevant_blocks
        ]
        
        # 記錄問答
        response_time_ms = int((time.time() - start_time) * 1000)
        db.log_query(
            question=question,
            answer=answer,
            document_ids=document_ids,
            matched_blocks=matched_blocks_info,
            similarity_scores=similarity_scores,
            ip_address=client_ip,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            status=status
        )
        
        return AnswerResponse(answer=answer, sources=sources)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"問答錯誤: {str(e)}")
        
        # 記錄錯誤
        response_time_ms = int((time.time() - start_time) * 1000)
        db.log_query(
            question=question,
            answer=str(e),
            document_ids=document_ids,
            ip_address=client_ip,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            status="error"
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query-logs", response_model=QueryLogResponse)
async def get_query_logs(
    limit: int = 50,
    offset: int = 0,
    ip: str = None,
    document_id: str = None,
    start_time: str = None,
    end_time: str = None
):
    """取得問答記錄"""
    logs = db.get_query_logs(
        limit=limit,
        offset=offset,
        ip_address=ip,
        document_id=document_id,
        start_time=start_time,
        end_time=end_time
    )
    return QueryLogResponse(logs=logs)


@app.get("/query-stats", response_model=QueryStatsResponse)
async def get_query_stats(days: int = 7):
    """取得問答統計資料"""
    stats = db.get_query_stats(days=days)
    return QueryStatsResponse(
        total_queries=stats.get("total_queries", 0),
        unique_ips=stats.get("unique_ips", 0),
        avg_response_time=stats.get("avg_response_time"),
        success_count=stats.get("success_count", 0),
        error_count=stats.get("error_count", 0),
        daily_counts=stats.get("daily_counts", [])
    )


def update_embeddings_for_document(doc_id: str):
    """為特定文件的 blocks 生成 embedding"""
    import psycopg2
    
    DB_HOST = os.environ.get("DB_HOST")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    
    if not DB_HOST or not DB_PASSWORD:
        logger.error("缺少 DB_HOST 或 DB_PASSWORD 環境變數")
        return
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port="5432",
        database="ocr_rag",
        user="postgres",
        password=DB_PASSWORD
    )
    cur = conn.cursor()
    
    # 取得該文件的 blocks
    cur.execute("""
        SELECT id, content FROM blocks 
        WHERE document_id = %s AND content IS NOT NULL AND content != ''
    """, (doc_id,))
    blocks = cur.fetchall()
    
    logger.info(f"為文件 {doc_id} 生成 {len(blocks)} 個 embeddings")
    
    for block_id, content in blocks:
        embedding = embedding_service.get_embedding(content)
        if embedding:
            cur.execute(
                "UPDATE blocks SET embedding = %s WHERE id = %s",
                (embedding, block_id)
            )
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"文件 {doc_id} 的 embeddings 生成完成")


@app.on_event("startup")
async def startup_event():
    """應用程式啟動時執行"""
    db.connect()
    # 初始化問答記錄表
    db.init_query_logs_table()
    logger.info("資料庫連線完成，問答記錄表已初始化")


if __name__ == "__main__":
    import uvicorn
    db.connect()
    db.init_query_logs_table()
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
