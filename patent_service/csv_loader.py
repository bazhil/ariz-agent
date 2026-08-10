import logging
from io import StringIO
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def read_patents_csv(file_content: bytes) -> pd.DataFrame:
    content = file_content.decode("utf-8", errors="replace")
    lines = content.splitlines()
    if not lines:
        raise ValueError("CSV file is empty")
    if lines[0].strip().lower().startswith("search url"):
        cleaned = "\n".join(lines[1:])
    else:
        cleaned = "\n".join(lines)
    df = pd.read_csv(StringIO(cleaned))
    required = ["title"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV must contain columns: {required}. Missing: {missing}")
    return df


def row_to_text(row: pd.Series) -> str:
    parts = []
    if "title" in row.index and pd.notna(row.get("title")) and str(row["title"]).strip():
        parts.append(str(row["title"]).strip())
    if "assignee" in row.index and pd.notna(row.get("assignee")) and str(row["assignee"]).strip():
        parts.append(str(row["assignee"]).strip())
    inventor_col = "inventor/author"
    if inventor_col in row.index and pd.notna(row.get(inventor_col)) and str(row[inventor_col]).strip():
        parts.append(str(row[inventor_col]).strip())
    if "id" in row.index and pd.notna(row.get("id")) and str(row["id"]).strip():
        parts.append(str(row["id"]).strip())
    if not parts:
        for col in row.index:
            if pd.notna(row.get(col)) and isinstance(row[col], str) and len(str(row[col]).strip()) > 10:
                parts.append(str(row[col]).strip())
                break
    return " ".join(parts) if parts else ""


def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def row_to_payload(row: pd.Series, default_url: str = "") -> Dict[str, Any]:
    payload = {}
    mapping = [
        ("id", "id"),
        ("title", "title"),
        ("assignee", "assignee"),
        ("inventor/author", "inventors"),
        ("priority date", "priority_date"),
        ("filing/creation date", "filing_date"),
        ("publication date", "publication_date"),
        ("grant date", "grant_date"),
        ("result link", "url"),
        ("representative figure link", "representative_figure_link"),
    ]
    for csv_col, key in mapping:
        if csv_col in row.index and pd.notna(row.get(csv_col)):
            val = row[csv_col]
            payload[key] = _safe_str(val) if isinstance(val, str) else val
    if "url" not in payload and default_url:
        payload["url"] = default_url
    return payload
