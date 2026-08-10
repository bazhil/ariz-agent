import re
from typing import List, Tuple

CHUNK_MAX_CHARS = 800
CHUNK_OVERLAP = 100


def _split_paragraphs(text: str) -> List[str]:
    if not text or not text.strip():
        return []
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_patent_content(
    title: str,
    abstract: str,
    description: str,
    claims: str,
    url: str,
    patent_id: str,
    assignee: str = "",
    inventors: str = "",
    max_chars: int = CHUNK_MAX_CHARS,
    overlap: int = CHUNK_OVERLAP,
) -> List[Tuple[str, dict]]:
    result = []
    base_payload = {
        "id": patent_id,
        "title": title,
        "url": url,
        "assignee": assignee,
        "inventors": inventors,
    }
    full_parts = []
    if abstract:
        full_parts.append(("abstract", abstract))
    if description:
        full_parts.append(("description", description))
    if claims:
        full_parts.append(("claims", claims))
    for section_name, section_text in full_parts:
        paragraphs = _split_paragraphs(section_text)
        current = []
        current_len = 0
        chunk_index = 0
        for p in paragraphs:
            p_len = len(p) + 2
            if current_len + p_len > max_chars and current:
                text = "\n\n".join(current)
                payload = {**base_payload, "section": section_name, "chunk_index": chunk_index, "fragment": text[:5000]}
                result.append((text, payload))
                chunk_index += 1
                overlap_text = "\n\n".join(current[-2:]) if len(current) >= 2 else current[-1]
                overlap_len = min(len(overlap_text), overlap)
                start = len(overlap_text) - overlap_len
                current = [overlap_text[start:].strip()] if start > 0 else []
                current_len = sum(len(x) + 2 for x in current)
            current.append(p)
            current_len += p_len
        if current:
            text = "\n\n".join(current)
            payload = {**base_payload, "section": section_name, "chunk_index": chunk_index, "fragment": text[:5000]}
            result.append((text, payload))
    if not result and (abstract or description or claims):
        text = "\n\n".join(t for _, t in full_parts)
        payload = {**base_payload, "section": "full", "chunk_index": 0, "fragment": text[:5000]}
        result.append((text[:10000], payload))
    return result
