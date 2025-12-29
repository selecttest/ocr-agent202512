"""
更新資料庫中的 Embedding（批次處理優化版本）
"""
##embedding 生成
import psycopg2
from psycopg2.extras import execute_batch
from embedding import embedding_service
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """取得資料庫連線"""
    DB_HOST = os.environ.get("DB_HOST")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    
    if not DB_HOST or not DB_PASSWORD:
        raise ValueError("請設定 DB_HOST 和 DB_PASSWORD 環境變數")
    
    return psycopg2.connect(
        host=DB_HOST,
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "ocr_rag"),
        user=os.environ.get("DB_USER", "postgres"),
        password=DB_PASSWORD
    )


def update_block_embeddings():
    """為所有沒有 embedding 的 blocks 生成 embedding（批次處理）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, content FROM blocks 
        WHERE embedding IS NULL AND content IS NOT NULL AND content != ''
        ORDER BY id
    """)
    blocks = cur.fetchall()
    
    if not blocks:
        logger.info("沒有需要更新的 blocks")
        cur.close()
        conn.close()
        return
    
    logger.info(f"找到 {len(blocks)} 個需要更新的 blocks，開始批次處理...")
    
    # 批次處理：每批 100 個（Vertex AI 限制）
    batch_size = 100
    total_updated = 0
    
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(blocks) + batch_size - 1) // batch_size
        
        block_ids = [b[0] for b in batch]
        contents = [b[1] for b in batch]
        
        logger.info(f"處理批次 {batch_num}/{total_batches} ({len(batch)} 個 blocks)...")
        
        try:
            # 批次生成 embeddings
            embeddings = embedding_service.get_embeddings_batch(contents)
            
            # 批次更新資料庫
            update_data = [
                (emb, block_id) 
                for emb, block_id in zip(embeddings, block_ids) 
                if emb is not None
            ]
            
            if update_data:
                execute_batch(
                    cur,
                    "UPDATE blocks SET embedding = %s::vector WHERE id = %s",
                    update_data,
                    page_size=100
                )
                conn.commit()
                total_updated += len(update_data)
                logger.info(f"✓ 批次 {batch_num} 完成，已更新 {total_updated}/{len(blocks)} 個 blocks")
            else:
                logger.warning(f"批次 {batch_num} 沒有成功生成任何 embedding")
                
        except Exception as e:
            logger.error(f"批次 {batch_num} 處理失敗: {e}")
            conn.rollback()
            # 繼續處理下一批
    
    cur.close()
    conn.close()
    
    logger.info(f"完成！共更新 {total_updated}/{len(blocks)} 個 blocks")


def update_image_embeddings():
    """為所有沒有 embedding 的 images 生成 embedding（批次處理）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, description FROM images 
        WHERE embedding IS NULL AND description IS NOT NULL AND description != ''
        ORDER BY id
    """)
    images = cur.fetchall()
    
    if not images:
        logger.info("沒有需要更新的 images")
        cur.close()
        conn.close()
        return
    
    logger.info(f"找到 {len(images)} 個需要更新的 images，開始批次處理...")
    
    # 批次處理：每批 100 個
    batch_size = 100
    total_updated = 0
    
    for i in range(0, len(images), batch_size):
        batch = images[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(images) + batch_size - 1) // batch_size
        
        image_ids = [img[0] for img in batch]
        descriptions = [img[1] for img in batch]
        
        logger.info(f"處理批次 {batch_num}/{total_batches} ({len(batch)} 個 images)...")
        
        try:
            # 批次生成 embeddings
            embeddings = embedding_service.get_embeddings_batch(descriptions)
            
            # 批次更新資料庫
            update_data = [
                (emb, img_id) 
                for emb, img_id in zip(embeddings, image_ids) 
                if emb is not None
            ]
            
            if update_data:
                execute_batch(
                    cur,
                    "UPDATE images SET embedding = %s::vector WHERE id = %s",
                    update_data,
                    page_size=100
                )
                conn.commit()
                total_updated += len(update_data)
                logger.info(f"✓ 批次 {batch_num} 完成，已更新 {total_updated}/{len(images)} 個 images")
            else:
                logger.warning(f"批次 {batch_num} 沒有成功生成任何 embedding")
                
        except Exception as e:
            logger.error(f"批次 {batch_num} 處理失敗: {e}")
            conn.rollback()
            # 繼續處理下一批
    
    cur.close()
    conn.close()
    
    logger.info(f"完成！共更新 {total_updated}/{len(images)} 個 images")


if __name__ == "__main__":
    update_block_embeddings()
    update_image_embeddings()
