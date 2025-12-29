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
        """批次取得多個文字的 embedding
        
        返回列表長度與輸入相同，空字串或無效文字返回 None
        
        Args:
            texts: 文字列表
            
        Returns:
            embedding 列表，每個元素是 List[float] 或 None
        """
        if not texts:
            return []
        
        try:
            # 建立索引映射：原始索引 -> 有效文字索引
            valid_indices = []
            valid_texts = []
            
            for idx, text in enumerate(texts):
                if text and len(text.strip()) > 0:
                    valid_indices.append(idx)
                    valid_texts.append(text[:2000])  # 限制長度
            
            if not valid_texts:
                # 全部都是空字串，返回全 None 列表
                return [None] * len(texts)
            
            # Vertex AI 一次最多處理 250 個，我們用 100 個批次
            all_embeddings = {}
            batch_size = 100
            
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i+batch_size]
                batch_indices = valid_indices[i:i+batch_size]
                
                embeddings = self.model.get_embeddings(batch)
                
                # 將結果對應回原始索引
                for idx, emb in zip(batch_indices, embeddings):
                    all_embeddings[idx] = emb.values
            
            # 構建返回列表，保持原始順序
            results = []
            for idx in range(len(texts)):
                results.append(all_embeddings.get(idx))
            
            return results
            
        except Exception as e:
            logger.error(f"批次生成 embedding 失敗: {e}")
            # 返回全 None 列表，保持長度一致
            return [None] * len(texts)


# 全域服務實例
embedding_service = EmbeddingService()
