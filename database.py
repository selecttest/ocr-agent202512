"""
資料庫操作模組
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging
from typing import Dict, List, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 資料庫連線設定
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "10.36.64.3"),  
    "port": os.environ.get("DB_PORT", "5432"),
    "database": os.environ.get("DB_NAME", "ocr_rag"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "ocr_DB251223")  # 請替換
}


class Database:
    def __init__(self):
        self.conn = None
    
    def connect(self):
        """建立資料庫連線"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("資料庫連線成功")
            return True
        except Exception as e:
            logger.error(f"資料庫連線失敗: {e}")
            return False
    
    def close(self):
        """關閉連線"""
        if self.conn:
            self.conn.close()
    
    def save_document(self, ocr_result: Dict, filename: str) -> Optional[str]:
        """儲存文件和所有相關資料"""
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor()
            
            # 1. 儲存文件主表
            cur.execute("""
                INSERT INTO documents 
                (filename, detected_type, language, total_pages, processing_time_seconds, summary, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                filename,
                ocr_result.get("detected_type", ""),
                ocr_result.get("language", ""),
                ocr_result.get("total_pages", 0),
                ocr_result.get("processing_time", {}).get("total_seconds"),
                ocr_result.get("full_text", ""),
                Json(ocr_result.get("processing_time"))
            ))
            
            doc_id = cur.fetchone()[0]
            logger.info(f"文件已儲存，ID: {doc_id}")
            
            # 2. 儲存 blocks
            blocks = ocr_result.get("blocks", [])
            for block in blocks:
                cur.execute("""
                    INSERT INTO blocks 
                    (document_id, block_id, block_type, page, region, content, confidence, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    doc_id,
                    block.get("id", ""),
                    block.get("type", ""),
                    block.get("page"),
                    block.get("region", ""),
                    block.get("content", ""),
                    block.get("confidence"),
                    Json(block.get("metadata", {}))
                ))
            logger.info(f"已儲存 {len(blocks)} 個 blocks")
            
            # 3. 儲存 key_values
            key_values = ocr_result.get("key_value_pairs", [])
            for kv in key_values:
                cur.execute("""
                    INSERT INTO key_values (document_id, key, value, page)
                    VALUES (%s, %s, %s, %s)
                """, (
                    doc_id,
                    kv.get("key", ""),
                    kv.get("value", ""),
                    kv.get("page")
                ))
            logger.info(f"已儲存 {len(key_values)} 個 key-value pairs")
            
            # 4. 儲存 images
            images_summary = ocr_result.get("images_summary")
            if images_summary:
                items = []
                if isinstance(images_summary, dict):
                    items = images_summary.get("items", [])
                elif isinstance(images_summary, list):
                    items = images_summary
                
                for img in items:
                    cur.execute("""
                        INSERT INTO images (document_id, image_type, page, region, description)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        doc_id,
                        img.get("type", ""),
                        img.get("page"),
                        img.get("region", ""),
                        img.get("description", "")
                    ))
                logger.info(f"已儲存 {len(items)} 個 images")
            
            self.conn.commit()
            return str(doc_id)
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"儲存文件失敗: {e}")
            raise e
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """取得文件資料"""
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # 取得文件
            cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
            doc = cur.fetchone()
            
            if not doc:
                return None
            
            # 取得 blocks
            cur.execute("SELECT * FROM blocks WHERE document_id = %s ORDER BY page, block_id", (doc_id,))
            blocks = cur.fetchall()
            
            # 取得 key_values
            cur.execute("SELECT * FROM key_values WHERE document_id = %s", (doc_id,))
            key_values = cur.fetchall()
            
            # 取得 images
            cur.execute("SELECT * FROM images WHERE document_id = %s", (doc_id,))
            images = cur.fetchall()
            
            return {
                "document": dict(doc),
                "blocks": [dict(b) for b in blocks],
                "key_values": [dict(kv) for kv in key_values],
                "images": [dict(img) for img in images]
            }
            
        except Exception as e:
            logger.error(f"取得文件失敗: {e}")
            return None
    
    def list_documents(self, limit: int = 20) -> List[Dict]:
        """列出所有文件"""
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, filename, detected_type, language, total_pages, upload_time 
                FROM documents 
                ORDER BY upload_time DESC 
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"列出文件失敗: {e}")
            return []
    
    def search_blocks(self, query_embedding: List[float], limit: int = 10) -> List[Dict]:
        """向量搜尋相關區塊"""
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # 使用 cosine 相似度搜尋
            cur.execute("""
                SELECT 
                    b.id,
                    b.document_id,
                    b.block_type,
                    b.page,
                    b.region,
                    b.content,
                    d.filename,
                    d.detected_type,
                    1 - (b.embedding <=> %s::vector) as similarity
                FROM blocks b
                JOIN documents d ON b.document_id = d.id
                WHERE b.embedding IS NOT NULL
                ORDER BY b.embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            
            return [dict(row) for row in cur.fetchall()]
            
        except Exception as e:
            logger.error(f"向量搜尋失敗: {e}")
            return []


# 全域資料庫實例
db = Database()
