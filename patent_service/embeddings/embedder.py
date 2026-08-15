import logging
from typing import List

logger = logging.getLogger(__name__)

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        from patent_service.config import EMBEDDING_MODEL
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def embed(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedder()
    return model.encode(texts, convert_to_numpy=True).tolist()
