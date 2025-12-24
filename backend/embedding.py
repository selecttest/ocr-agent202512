"""
Embedding 生成模組
"""

import vertexai
from vertexai.language_models import TextEmbeddingModel
import logging
from typing import List
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "aic-rain-playground")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")


class EmbeddingService:
    def __init__(self):
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        logger.info("Embedding 服務初始化完成")
    
    def get_embedding(self, text: str) -> List[float]:
        """取得單一文字的 embedding"""
        if not text or len(text.strip()) == 0:
            return None
        
        try:
            # 限制文字長度
            text = text[:2000]
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"生成 embedding 失敗: {e}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批次取得多個文字的 embedding"""
        if not texts:
            return []
        
        try:
            # 過濾空字串並限制長度
            valid_texts = [t[:2000] for t in texts if t and len(t.strip()) > 0]
            
            if not valid_texts:
                return []
            
            # Vertex AI 一次最多處理 250 個
            results = []
            batch_size = 100
            
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i+batch_size]
                embeddings = self.model.get_embeddings(batch)
                results.extend([e.values for e in embeddings])
            
            return results
            
        except Exception as e:
            logger.error(f"批次生成 embedding 失敗: {e}")
            return []


# 全域服務實例
embedding_service = EmbeddingService()
