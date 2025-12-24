"""
OCR API 服務 - 含資料庫儲存
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging

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
    top_k: int = 5
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
async def ask_question(request: QuestionRequest):
    """
    RAG 問答：根據已上傳的文件回答問題
    - document_ids: 可選，指定要查詢的文件 ID 列表（為空時搜尋所有文件）
    """
    question = request.question
    top_k = request.top_k
    document_ids = request.document_ids
    
    logger.info(f"收到問題: {question}")
    if document_ids:
        logger.info(f"限定查詢文件: {document_ids}")
    
    try:
        # 1. 將問題轉成 embedding
        question_embedding = embedding_service.get_embedding(question)
        
        if not question_embedding:
            raise HTTPException(status_code=500, detail="無法生成問題的 embedding")
        
        # 2. 向量搜尋相關內容（支援文件篩選）
        relevant_blocks = db.search_blocks(
            question_embedding, 
            limit=top_k,
            document_ids=document_ids
        )
        
        if not relevant_blocks:
            msg = "抱歉，在"
            if document_ids:
                msg += f"選擇的 {len(document_ids)} 份文件中"
            else:
                msg += "已上傳的文件中"
            msg += "找不到相關資訊。"
            return AnswerResponse(answer=msg, sources=[])
        
        # 3. 組合 context
        context_parts = []
        for block in relevant_blocks:
            context_parts.append(
                f"[來源: {block['filename']}, 第{block['page']}頁]\n{block['content']}"
            )
        context = "\n\n".join(context_parts)
        
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
        
        return AnswerResponse(answer=answer, sources=sources)
        
    except Exception as e:
        logger.error(f"問答錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn
    db.connect()
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
