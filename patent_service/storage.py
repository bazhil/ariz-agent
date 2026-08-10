from datetime import datetime, timezone
from typing import Dict, Any, Optional
from cachetools import TTLCache


class TaskResultStorage:
    def __init__(self, maxsize: int = 1000, ttl_hours: int = 24):
        self.cache = TTLCache(
            maxsize=maxsize,
            ttl=ttl_hours * 3600
        )

    def create_task(self, task_id: str) -> Dict[str, Any]:
        task_data = {
            "status": "pending",
            "start_time": datetime.now(timezone.utc),
            "total_rows": 0,
            "processed": 0,
            "success_count": 0,
            "completion_time": None,
            "error": None
        }
        self.cache[task_id] = task_data
        return task_data

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.cache.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_rows: Optional[int] = None,
        processed: Optional[int] = None,
        success_count: Optional[int] = None,
        completion_time: Optional[datetime] = None,
        error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        task = self.get_task(task_id)
        if task is None:
            return None
        if status is not None:
            task["status"] = status
        if total_rows is not None:
            task["total_rows"] = total_rows
        if processed is not None:
            task["processed"] = processed
        if success_count is not None:
            task["success_count"] = success_count
        if completion_time is not None:
            task["completion_time"] = completion_time
        if error is not None:
            task["error"] = error
        return task

    def task_exists(self, task_id: str) -> bool:
        return task_id in self.cache
