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

# 資料庫連線設定（全部從環境變數讀取）
DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT", "5432"),
    "database": os.environ.get("DB_NAME", "ocr_rag"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD")
}


class Database:
    def __init__(self):
        self.conn = None
    
    def connect(self):
        """建立資料庫連線"""
        if not DB_CONFIG["host"] or not DB_CONFIG["password"]:
            logger.error("請設定 DB_HOST 和 DB_PASSWORD 環境變數")
            return False
        
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("資料庫連線成功")
            return True
        except Exception as e:
            logger.error(f"資料庫連線失敗: {e}")
            return False
    
    def ensure_connection(self):
        """確保連線有效，如果斷開則重新連線"""
        try:
            if self.conn is None or self.conn.closed:
                logger.info("連線已斷開，正在重新連線...")
                return self.connect()
            
            # 測試連線是否有效
            cur = self.conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception as e:
            logger.warning(f"連線測試失敗，正在重新連線: {e}")
            try:
                self.conn = psycopg2.connect(**DB_CONFIG)
                logger.info("重新連線成功")
                return True
            except Exception as e2:
                logger.error(f"重新連線失敗: {e2}")
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
                ocr_result.get("processing_time", {}).get("total_seconds") if ocr_result.get("processing_time") else None,
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
            
            # 3.1 將 header 和 section_title 類型的 blocks 也存入 key_values
            # 這樣可以更好地理解文件結構
            section_count = 0
            for block in blocks:
                block_type = block.get("type", "")
                if block_type in ("header", "section_title"):
                    content = block.get("content", "").strip()
                    if content:
                        cur.execute("""
                            INSERT INTO key_values (document_id, key, value, page)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            doc_id,
                            f"章節標題({block_type})",
                            content,
                            block.get("page")
                        ))
                        section_count += 1
            
            total_kv = len(key_values) + section_count
            logger.info(f"已儲存 {total_kv} 個 key-value pairs（含 {section_count} 個章節標題）")
            
            # 4. 儲存 images
            images_summary = ocr_result.get("images_summary")
            image_count = 0
            if images_summary:
                items = []
                if isinstance(images_summary, dict):
                    items = images_summary.get("items", [])
                elif isinstance(images_summary, list):
                    items = images_summary
                
                for img in items:
                    # 存入 images 表
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
                    
                    # 【新增】把圖片描述也存入 key_values，以便搜索
                    description = img.get("description", "").strip()
                    if description:
                        img_type = img.get("type", "圖片")
                        cur.execute("""
                            INSERT INTO key_values (document_id, key, value, page)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            doc_id,
                            f"圖片內容({img_type})",
                            description,
                            img.get("page")
                        ))
                        image_count += 1
                
                logger.info(f"已儲存 {len(items)} 個 images，{image_count} 個圖片描述加入 key_values")
            
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
            
            cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
            doc = cur.fetchone()
            
            if not doc:
                return None
            
            cur.execute("SELECT * FROM blocks WHERE document_id = %s ORDER BY page, block_id", (doc_id,))
            blocks = cur.fetchall()
            
            cur.execute("SELECT * FROM key_values WHERE document_id = %s", (doc_id,))
            key_values = cur.fetchall()
            
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
    
    def search_blocks(self, query_embedding: List[float], limit: int = 10, document_ids: List[str] = None) -> List[Dict]:
        """向量搜尋相關區塊
        
        搜索策略：
        1. 優先搜索 header/section_title 類型（權重加成）
        2. 再搜索一般內容
        
        Args:
            query_embedding: 查詢向量
            limit: 回傳數量上限
            document_ids: 可選，限定搜尋的文件 ID 列表
        """
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            if document_ids and len(document_ids) > 0:
                # 有指定文件 ID，只搜尋這些文件
                # 使用 CASE 給 header/section_title 類型加權
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
                        1 - (b.embedding <=> %s::vector) as base_similarity,
                        CASE 
                            WHEN b.block_type IN ('header', 'section_title') THEN 
                                (1 - (b.embedding <=> %s::vector)) * 1.2
                            ELSE 
                                1 - (b.embedding <=> %s::vector)
                        END as similarity
                    FROM blocks b
                    JOIN documents d ON b.document_id = d.id
                    WHERE b.embedding IS NOT NULL
                      AND b.document_id = ANY(%s::uuid[])
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (query_embedding, query_embedding, query_embedding, document_ids, limit))
            else:
                # 沒有指定文件 ID，搜尋所有文件
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
                        1 - (b.embedding <=> %s::vector) as base_similarity,
                        CASE 
                            WHEN b.block_type IN ('header', 'section_title') THEN 
                                (1 - (b.embedding <=> %s::vector)) * 1.2
                            ELSE 
                                1 - (b.embedding <=> %s::vector)
                        END as similarity
                    FROM blocks b
                    JOIN documents d ON b.document_id = d.id
                    WHERE b.embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (query_embedding, query_embedding, query_embedding, limit))
            
            return [dict(row) for row in cur.fetchall()]
            
        except Exception as e:
            logger.error(f"向量搜尋失敗: {e}")
            return []
    
    def search_key_values(
        self, 
        keywords: List[str], 
        document_ids: List[str] = None
    ) -> List[Dict]:
        """用關鍵字搜索 key_values 表
        
        Args:
            keywords: 關鍵字列表
            document_ids: 可選，限定搜尋的文件 ID 列表
        """
        if not self.ensure_connection():
            return []
        
        if not keywords:
            return []
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # 建立 LIKE 條件（任一關鍵字匹配 key 或 value）
            like_conditions = []
            params = []
            
            for keyword in keywords:
                like_conditions.append("(kv.key ILIKE %s OR kv.value ILIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            like_clause = " OR ".join(like_conditions)
            
            if document_ids and len(document_ids) > 0:
                query = f"""
                    SELECT 
                        kv.id,
                        kv.document_id,
                        kv.key,
                        kv.value,
                        kv.page,
                        d.filename
                    FROM key_values kv
                    JOIN documents d ON kv.document_id = d.id
                    WHERE kv.document_id = ANY(%s::uuid[])
                      AND ({like_clause})
                    ORDER BY kv.page
                """
                params = [document_ids] + params
            else:
                query = f"""
                    SELECT 
                        kv.id,
                        kv.document_id,
                        kv.key,
                        kv.value,
                        kv.page,
                        d.filename
                    FROM key_values kv
                    JOIN documents d ON kv.document_id = d.id
                    WHERE {like_clause}
                    ORDER BY kv.page
                """
            
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            logger.info(f"key_values 關鍵字搜索: {keywords} → 找到 {len(results)} 筆")
            return results
            
        except Exception as e:
            logger.error(f"key_values 搜索失敗: {e}")
            return []
    
    def get_blocks_by_page_range(
        self, 
        document_id: str, 
        start_page: int, 
        end_page: int
    ) -> List[Dict]:
        """取得指定文件、指定頁碼範圍的所有 blocks
        
        Args:
            document_id: 文件 ID
            start_page: 起始頁碼
            end_page: 結束頁碼
        """
        if not self.ensure_connection():
            return []
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    b.id,
                    b.document_id,
                    b.block_type,
                    b.page,
                    b.region,
                    b.content,
                    d.filename
                FROM blocks b
                JOIN documents d ON b.document_id = d.id
                WHERE b.document_id = %s
                  AND b.page >= %s
                  AND b.page <= %s
                ORDER BY b.page, b.id
            """, (document_id, start_page, end_page))
            
            return [dict(row) for row in cur.fetchall()]
            
        except Exception as e:
            logger.error(f"取得頁面區塊失敗: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """刪除文件及其所有相關資料
        
        由於資料表有設定 ON DELETE CASCADE，
        刪除 documents 表的記錄會自動刪除 blocks、key_values、images 的相關記錄
        """
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor()
            
            # 先檢查文件是否存在
            cur.execute("SELECT id, filename FROM documents WHERE id = %s", (doc_id,))
            doc = cur.fetchone()
            
            if not doc:
                logger.warning(f"文件不存在: {doc_id}")
                return False
            
            filename = doc[1]
            
            # 刪除文件（CASCADE 會自動刪除關聯資料）
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            
            self.conn.commit()
            logger.info(f"已刪除文件: {filename} (ID: {doc_id})")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"刪除文件失敗: {e}")
            return False
    
    def delete_documents(self, doc_ids: List[str]) -> Dict:
        """批次刪除多個文件
        
        Returns:
            Dict: {"deleted": 成功數量, "failed": 失敗數量, "deleted_ids": 成功刪除的ID列表}
        """
        if not self.conn:
            self.connect()
        
        deleted_ids = []
        failed_count = 0
        
        for doc_id in doc_ids:
            if self.delete_document(doc_id):
                deleted_ids.append(doc_id)
            else:
                failed_count += 1
        
        return {
            "deleted": len(deleted_ids),
            "failed": failed_count,
            "deleted_ids": deleted_ids
        }


    def init_query_logs_table(self):
        """初始化問答記錄表"""
        if not self.ensure_connection():
            logger.error("無法連線到資料庫，無法初始化問答記錄表")
            return False
        
        try:
            cur = self.conn.cursor()
            
            # 建立問答記錄表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    question TEXT NOT NULL,
                    answer TEXT,
                    document_ids UUID[],
                    search_keywords TEXT[],
                    matched_blocks JSONB,
                    similarity_scores FLOAT[],
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    status VARCHAR(20) DEFAULT 'success'
                );
                
                -- 建立索引加速查詢
                CREATE INDEX IF NOT EXISTS idx_query_logs_time ON query_logs(query_time DESC);
                CREATE INDEX IF NOT EXISTS idx_query_logs_ip ON query_logs(ip_address);
                CREATE INDEX IF NOT EXISTS idx_query_logs_document_ids ON query_logs USING GIN(document_ids);
            """)
            
            self.conn.commit()
            logger.info("問答記錄表初始化成功")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"初始化問答記錄表失敗: {e}")
            return False
    
    def log_query(
        self,
        question: str,
        answer: str = None,
        document_ids: List[str] = None,
        search_keywords: List[str] = None,
        matched_blocks: List[Dict] = None,
        similarity_scores: List[float] = None,
        ip_address: str = None,
        user_agent: str = None,
        response_time_ms: int = None,
        status: str = "success"
    ) -> Optional[str]:
        """記錄問答內容
        
        Args:
            question: 使用者問題
            answer: AI 回答
            document_ids: 搜尋的文件 ID 列表
            search_keywords: 搜尋關鍵字
            matched_blocks: 匹配的區塊資訊
            similarity_scores: 相似度分數列表
            ip_address: 使用者 IP
            user_agent: 使用者瀏覽器資訊
            response_time_ms: 回應時間（毫秒）
            status: 狀態（success/error）
        
        Returns:
            記錄 ID
        """
        if not self.ensure_connection():
            logger.error("無法連線到資料庫，問答記錄未儲存")
            return None
        
        try:
            cur = self.conn.cursor()
            
            # Debug: 印出要儲存的資料
            logger.info(f"正在儲存問答記錄: question={question[:50]}..., ip={ip_address}")
            
            cur.execute("""
                INSERT INTO query_logs 
                (question, answer, document_ids, search_keywords, matched_blocks, 
                 similarity_scores, ip_address, user_agent, response_time_ms, status)
                VALUES (%s, %s, %s::uuid[], %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                question,
                answer,
                document_ids,
                search_keywords,
                Json(matched_blocks) if matched_blocks else None,
                similarity_scores,
                ip_address,
                user_agent,
                response_time_ms,
                status
            ))
            
            log_id = cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"問答記錄已儲存，ID: {log_id}")
            return str(log_id)
            
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"儲存問答記錄失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_query_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        ip_address: str = None,
        document_id: str = None,
        start_time: str = None,
        end_time: str = None
    ) -> List[Dict]:
        """取得問答記錄
        
        Args:
            limit: 回傳數量上限
            offset: 跳過的記錄數
            ip_address: 過濾特定 IP
            document_id: 過濾特定文件
            start_time: 開始時間 (ISO format)
            end_time: 結束時間 (ISO format)
        """
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            query = "SELECT * FROM query_logs WHERE 1=1"
            params = []
            
            if ip_address:
                query += " AND ip_address = %s"
                params.append(ip_address)
            
            if document_id:
                query += " AND %s = ANY(document_ids)"
                params.append(document_id)
            
            if start_time:
                query += " AND query_time >= %s"
                params.append(start_time)
            
            if end_time:
                query += " AND query_time <= %s"
                params.append(end_time)
            
            query += " ORDER BY query_time DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
            
        except Exception as e:
            logger.error(f"取得問答記錄失敗: {e}")
            return []
    
    def get_query_stats(self, days: int = 7) -> Dict:
        """取得問答統計資料
        
        Args:
            days: 統計天數
        """
        if not self.conn:
            self.connect()
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT ip_address) as unique_ips,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count
                FROM query_logs
                WHERE query_time >= NOW() - INTERVAL '%s days'
            """, (days,))
            
            stats = dict(cur.fetchone())
            
            # 每日統計
            cur.execute("""
                SELECT 
                    DATE(query_time) as date,
                    COUNT(*) as count
                FROM query_logs
                WHERE query_time >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(query_time)
                ORDER BY date DESC
            """, (days,))
            
            stats["daily_counts"] = [dict(row) for row in cur.fetchall()]
            
            return stats
            
        except Exception as e:
            logger.error(f"取得問答統計失敗: {e}")
            return {}


# 全域資料庫實例
db = Database()
