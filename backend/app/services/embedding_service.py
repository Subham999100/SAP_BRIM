import logging
import hashlib
import numpy as np
from typing import List
from backend.app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self._model = None
        self._model_failed = False
        self.embedding_dim = settings.EMBEDDING_DIM

    def _get_model(self):
        if self._model is not None:
            return self._model
        if self._model_failed:
            return None
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("SentenceTransformer model loaded successfully.")
            return self._model
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Using robust fallback embedding generator.")
            self._model_failed = True
            return None

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Deterministic, normalized dense projection (dim=384) fallback
        ensuring cosine similarity between semantically overlapping texts is high
        even without a live network connection to HuggingFace.
        """
        dim = self.embedding_dim
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        for word in words:
            # Hash word into 3 bucket dimensions with sign
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            for i in range(3):
                idx = (h >> (i * 10)) % dim
                sign = 1.0 if ((h >> (i * 10 + 9)) & 1) else -1.0
                vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_text(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self.embedding_dim

        model = self._get_model()
        if model:
            try:
                emb = model.encode(cleaned, convert_to_numpy=True)
                # Normalize vector
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return emb.tolist()
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding error: {e}. Falling back.")

        return self._fallback_embed(cleaned)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        if model:
            try:
                embs = model.encode(texts, batch_size=32, convert_to_numpy=True)
                result = []
                for emb in embs:
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        emb = emb / norm
                    result.append(emb.tolist())
                return result
            except Exception as e:
                logger.warning(f"SentenceTransformer batch error: {e}. Falling back.")

        return [self._fallback_embed(t) for t in texts]

embedding_service = EmbeddingService()
