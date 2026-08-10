import json
import logging
import uuid
from contextlib import asynccontextmanager

from typing import List, Optional, Any, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from patent_service.config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE
from patent_service.storage import TaskResultStorage
from patent_service.tasks import run_load_task
from patent_service.qdrant_manager import QdrantPatentsManager
from patent_service.embedder import embed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

task_storage = TaskResultStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    pass


app = FastAPI(title="Patent Qdrant Service", lifespan=lifespan)


class EmbedTextRequest(BaseModel):
    text: Optional[str] = Field(None, description="Single string to embed")
    texts: Optional[List[str]] = Field(None, description="List of strings to embed")

    model_config = {"extra": "forbid"}


def _search_queries(manager: QdrantPatentsManager, queries: List[str], limit: int = 7) -> List[List[Dict[str, Any]]]:
    if not queries:
        return []
    vectors = embed(queries)
    out = []
    for q, vec in zip(queries, vectors):
        hits = manager.search(query_vector=vec, limit=limit)
        out.append(hits)
    return out


@app.post("/embed")
async def get_embedding(body: EmbedTextRequest):
    if body.text is not None and body.texts is not None:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'texts', not both")
    if body.text is not None:
        s = body.text.strip()
        if not s:
            raise HTTPException(status_code=400, detail="'text' must be non-empty")
        vectors = embed([s])
        return {"embedding": vectors[0], "dim": VECTOR_SIZE}
    if body.texts is not None:
        texts = [t.strip() for t in body.texts if t and str(t).strip()]
        if not texts:
            raise HTTPException(status_code=400, detail="'texts' must contain at least one non-empty string")
        vectors = embed(texts)
        return {"embeddings": vectors, "dim": VECTOR_SIZE}
    raise HTTPException(status_code=400, detail="Provide 'text' or 'texts'")


@app.post("/load_csv", response_class=JSONResponse)
async def load_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV export from Google Patents"),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    contents = await file.read()
    task_id = str(uuid.uuid4())
    task_storage.create_task(task_id)
    background_tasks.add_task(run_load_task, task_id, contents, task_storage)

    return JSONResponse(
        content={
            "message": "CSV load started",
            "task_id": task_id,
            "status_endpoint": f"/load_status/{task_id}",
        },
        status_code=202,
    )


@app.get("/load_status/{task_id}")
async def load_status(task_id: str):
    if not task_storage.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    result = task_storage.get_task(task_id)
    if result["status"] == "completed":
        return {
            "status": "completed",
            "task_id": task_id,
            "success_count": result["success_count"],
            "total_rows": result["total_rows"],
        }
    if result["status"] == "failed":
        return JSONResponse(
            content={"status": "failed", "task_id": task_id, "error": result["error"]},
            status_code=500,
        )
    return {
        "status": "processing",
        "task_id": task_id,
        "processed": result["processed"],
        "total_rows": result["total_rows"],
        "progress_pct": round(100 * result["processed"] / max(1, result["total_rows"]), 1),
    }


@app.get("/search")
async def search(q: str, limit: int = 10):
    if limit < 1 or limit > 100:
        limit = 10
    if not q or not q.strip():
        return {"results": [], "query": q, "limit": limit}

    manager = QdrantPatentsManager(url=QDRANT_URL, collection=COLLECTION_NAME)
    query_vector = embed([q.strip()])[0]
    hits = manager.search(query_vector=query_vector, limit=limit)
    return {"results": hits, "query": q.strip(), "limit": limit}


@app.post("/search_by_output")
async def search_by_output(request: Request):
    raw = (await request.body()).decode("utf-8")
    logger.info("search_by_output body: %s", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict) and not any(
            k in data for k in ("breakthrough", "good", "trivial")
        ):
            inner = data.get("output")
            if isinstance(inner, str):
                data = json.loads(inner)
            elif isinstance(inner, dict):
                data = inner
    except json.JSONDecodeError as e:
        logger.warning("search_by_output invalid JSON: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid JSON in output: {e}")
    breakthrough = data.get("breakthrough") or []
    good = data.get("good") or []
    trivial = data.get("trivial") or []
    if not isinstance(breakthrough, list):
        logger.warning("search_by_output breakthrough is not list: %r", type(breakthrough))
        breakthrough = []
    if not isinstance(good, list):
        logger.warning("search_by_output good is not list: %r", type(good))
        good = []
    if not isinstance(trivial, list):
        logger.warning("search_by_output trivial is not list: %r", type(trivial))
        trivial = []
    breakthrough = [str(s).strip() for s in breakthrough if s and str(s).strip()]
    good = [str(s).strip() for s in good if s and str(s).strip()]
    trivial = [str(s).strip() for s in trivial if s and str(s).strip()]
    logger.info(
        "search_by_output parsed counts: breakthrough=%d, good=%d, trivial=%d",
        len(breakthrough),
        len(good),
        len(trivial),
    )

    limit = 7
    manager = QdrantPatentsManager(url=QDRANT_URL, collection=COLLECTION_NAME)
    result = {
        "breakthrough": _search_queries(manager, breakthrough, limit=limit),
        "good": _search_queries(manager, good, limit=limit),
        "trivial": _search_queries(manager, trivial, limit=limit),
    }
    logger.info(
        "search_by_output search finished: breakthrough_hits=%d, good_hits=%d, trivial_hits=%d",
        len(result["breakthrough"]),
        len(result["good"]),
        len(result["trivial"]),
    )
    return result


@app.get("/health")
async def health():
    try:
        manager = QdrantPatentsManager(url=QDRANT_URL, collection=COLLECTION_NAME)
        count = manager.count()
        return {"status": "ok", "qdrant": "connected", "patents_count": count}
    except Exception as e:
        logger.warning("Health check failed: %s", e)
        return JSONResponse(
            content={"status": "error", "qdrant": str(e)},
            status_code=503,
        )
