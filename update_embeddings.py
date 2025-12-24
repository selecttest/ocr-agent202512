"""
更新資料庫中的 Embedding
"""

import psycopg2
from embedding import embedding_service
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", os.environ.get("DB_HOST", "localhost")),  # 請替換
    "port": "5432",
    "database": "ocr_rag",
    "user": "postgres",
    "password": os.environ.get("DB_PASSWORD", os.environ.get("DB_PASSWORD", ""))  # 請替換
}


def update_block_embeddings():
    """為所有沒有 embedding 的 blocks 生成 embedding"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 取得沒有 embedding 的 blocks
    cur.execute("""
        SELECT id, content FROM blocks 
        WHERE embedding IS NULL AND content IS NOT NULL AND content != ''
    """)
    blocks = cur.fetchall()
    
    logger.info(f"找到 {len(blocks)} 個需要更新的 blocks")
    
    updated = 0
    for block_id, content in blocks:
        embedding = embedding_service.get_embedding(content)
        if embedding:
            cur.execute(
                "UPDATE blocks SET embedding = %s WHERE id = %s",
                (embedding, block_id)
            )
            updated += 1
            
            if updated % 10 == 0:
                conn.commit()
                logger.info(f"已更新 {updated} 個 blocks")
    
    conn.commit()
    logger.info(f"完成！共更新 {updated} 個 blocks")
    
    cur.close()
    conn.close()


def update_image_embeddings():
    """為所有沒有 embedding 的 images 生成 embedding"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, description FROM images 
        WHERE embedding IS NULL AND description IS NOT NULL AND description != ''
    """)
    images = cur.fetchall()
    
    logger.info(f"找到 {len(images)} 個需要更新的 images")
    
    updated = 0
    for img_id, description in images:
        embedding = embedding_service.get_embedding(description)
        if embedding:
            cur.execute(
                "UPDATE images SET embedding = %s WHERE id = %s",
                (embedding, img_id)
            )
            updated += 1
    
    conn.commit()
    logger.info(f"完成！共更新 {updated} 個 images")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    update_block_embeddings()
    update_image_embeddings()
