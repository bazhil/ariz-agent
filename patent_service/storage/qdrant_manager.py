import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from patent_service.config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE


logger = logging.getLogger(__name__)


class QdrantPatentsManager:
    def __init__(self, url: str = QDRANT_URL, collection: str = COLLECTION_NAME):
        self._client = QdrantClient(url=url)
        self._collection = collection

    def ensure_collection(self) -> None:
        collections = self._client.get_collections().collections
        if not any(c.name == self._collection for c in collections):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
            logger.info("Created collection %s", self._collection)

    def upsert_batch(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]]
    ) -> None:
        self.ensure_collection()
        points = [
            PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload)
            for vec, payload in zip(vectors, payloads)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        self.ensure_collection()
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        points = response.points if hasattr(response, "points") else []
        return [
            {
                "id": str(p.id),
                "score": p.score,
                **(p.payload or {})
            }
            for p in points
        ]

    def count(self) -> int:
        try:
            return self._client.count(collection_name=self._collection).count
        except Exception:
            return 0
