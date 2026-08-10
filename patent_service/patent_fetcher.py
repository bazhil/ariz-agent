import logging
from typing import Optional, List
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _extract_section_text(soup: BeautifulSoup, section_type: str) -> str:
    section = soup.find("section", {"itemprop": section_type})
    if not section:
        return ""
    for tag in section.find_all("span", class_="notranslate"):
        if tag.find(class_="google-src-text"):
            tag.decompose()
    return section.get_text(separator=" ", strip=True)


def _extract_list_items(soup: BeautifulSoup, item_type: str) -> List[str]:
    items = soup.find_all("dd", {"itemprop": item_type})
    return [item.get_text(strip=True) for item in items] if items else []


async def fetch_patent_content(patent_url: str, title: str = "") -> Optional[dict]:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(patent_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        abstract = _extract_section_text(soup, "abstract")
        description = _extract_section_text(soup, "description")
        claims = _extract_section_text(soup, "claims")
        if not title:
            h1 = soup.find("h1", {"itemprop": "title"})
            title = h1.get_text(strip=True) if h1 else ""
        return {
            "title": title or "No title",
            "abstract": abstract,
            "description": description,
            "claims": claims,
            "url": patent_url,
            "inventors": _extract_list_items(soup, "inventor"),
            "assignees": _extract_list_items(soup, "assignee"),
        }
    except Exception as e:
        logger.warning("Failed to fetch patent %s: %s", patent_url, e)
        return None
