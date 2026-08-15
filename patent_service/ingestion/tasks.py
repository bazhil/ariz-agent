import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Tuple

import pandas as pd

from patent_service.ingestion.csv_loader import read_patents_csv
from patent_service.ingestion.patent_fetcher import fetch_patent_content
from patent_service.ingestion.chunker import chunk_patent_content
from patent_service.embeddings.embedder import embed
from patent_service.storage.qdrant_manager import QdrantPatentsManager
from patent_service.storage.task_storage import TaskResultStorage
from patent_service.config import QDRANT_URL, COLLECTION_NAME

logger = logging.getLogger(__name__)

BATCH_SIZE = 32
FETCH_CONCURRENCY = 3


def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


async def _fetch_and_chunk_one(
    title: str,
    url: str,
    patent_id: str,
    assignee: str,
    inventors: str,
    semaphore: asyncio.Semaphore,
) -> List[Tuple[str, dict]]:
    async with semaphore:
        data = await fetch_patent_content(url, title=title)
    if not data:
        return []
    if not data.get("abstract") and not data.get("description") and not data.get("claims"):
        return []
    assignee_str = assignee or (", ".join(data["assignees"][:3]) if data.get("assignees") else "")
    inventors_str = inventors or (", ".join(data["inventors"][:5]) if data.get("inventors") else "")
    return chunk_patent_content(
        title=data["title"],
        abstract=data.get("abstract", ""),
        description=data.get("description", ""),
        claims=data.get("claims", ""),
        url=data["url"],
        patent_id=patent_id,
        assignee=assignee_str,
        inventors=inventors_str,
    )


async def _run_load_async(
    df: pd.DataFrame,
    task_id: str,
    task_storage: TaskResultStorage,
) -> None:
    url_col = "result link"
    if url_col not in df.columns:
        raise ValueError("CSV must contain 'result link' column for full content fetch")
    task_storage.update_task(task_id, total_rows=len(df))
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)
    all_texts: List[str] = []
    all_payloads: List[dict] = []
    processed_patents = 0
    for idx, row in df.iterrows():
        title = _safe_str(row.get("title", ""))
        url = _safe_str(row.get(url_col, ""))
        if not url:
            continue
        patent_id = _safe_str(row.get("id", "")) or f"row-{idx}"
        assignee = _safe_str(row.get("assignee", ""))
        inventors = _safe_str(row.get("inventor/author", "")) if "inventor/author" in row else ""
        chunks = await _fetch_and_chunk_one(
            title=title,
            url=url,
            patent_id=patent_id,
            assignee=assignee,
            inventors=inventors,
            semaphore=semaphore,
        )
        for text, payload in chunks:
            all_texts.append(text)
            all_payloads.append(payload)
        processed_patents += 1
        task_storage.update_task(task_id, processed=processed_patents)
    if not all_texts:
        task_storage.update_task(
            task_id,
            status="completed",
            success_count=0,
            completion_time=datetime.now(timezone.utc),
        )
        logger.warning("Task %s: no patent content extracted", task_id)
        return
    task_storage.update_task(task_id, total_rows=processed_patents)
    manager = QdrantPatentsManager(url=QDRANT_URL, collection=COLLECTION_NAME)
    manager.ensure_collection()
    total_chunks = len(all_texts)
    success_count = 0
    for i in range(0, total_chunks, BATCH_SIZE):
        batch_texts = all_texts[i : i + BATCH_SIZE]
        batch_payloads = all_payloads[i : i + BATCH_SIZE]
        vectors = embed(batch_texts)
        manager.upsert_batch(vectors=vectors, payloads=batch_payloads)
        success_count += len(batch_texts)
        task_storage.update_task(task_id, processed=processed_patents, success_count=success_count)
    task_storage.update_task(
        task_id,
        status="completed",
        success_count=success_count,
        completion_time=datetime.now(timezone.utc),
    )
    logger.info("Task %s completed: %d patents, %d fragments indexed", task_id, processed_patents, success_count)


def run_load_task(task_id: str, contents: bytes, task_storage: TaskResultStorage) -> None:
    try:
        df = read_patents_csv(contents)
        if df.empty:
            raise ValueError("CSV has no data rows")
        asyncio.run(_run_load_async(df, task_id, task_storage))
    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task_storage.update_task(
            task_id,
            status="failed",
            error=str(e),
            completion_time=datetime.now(timezone.utc),
        )
