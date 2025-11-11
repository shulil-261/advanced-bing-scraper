thonimport csv
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger("export_csv")

CSV_FIELDS = [
    "keyword",
    "pageNumber",
    "resultType",
    "title",
    "url",
    "description",
    "extra",
]

def _flatten_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flattens a single structured record into multiple CSV rows.

    We primarily expose organic results, related queries, and PAA entries,
    but also include simple representations of images, videos, and news.
    """
    rows: List[Dict[str, Any]] = []

    keyword = record.get("keyword", "")
    page_number = record.get("pageNumber", "")

    def add_row(result_type: str, title: str, url: str, description: str, extra: str = "") -> None:
        rows.append(
            {
                "keyword": keyword,
                "pageNumber": page_number,
                "resultType": result_type,
                "title": title,
                "url": url,
                "description": description,
                "extra": extra,
            }
        )

    for item in record.get("organicResults", []):
        add_row(
            "organic",
            item.get("title", ""),
            item.get("url", ""),
            item.get("description", ""),
        )

    for item in record.get("relatedQueries", []):
        add_row(
            "related_query",
            item.get("text", ""),
            item.get("url", ""),
            "",
        )

    for item in record.get("peopleAlsoAsk", []):
        add_row(
            "people_also_ask",
            item.get("question", ""),
            "",
            item.get("answer", ""),
        )

    for item in record.get("images", []):
        add_row(
            "image",
            "",
            item.get("url", ""),
            item.get("description", ""),
        )

    for item in record.get("videos", []):
        extra = f"views={item.get('views', '')};channel={item.get('channel', '')};provider={item.get('provider', '')}"
        add_row(
            "video",
            item.get("title", ""),
            item.get("url", ""),
            "",
            extra,
        )

    for item in record.get("news", []):
        extra = f"source={item.get('source', '')}"
        add_row(
            "news",
            item.get("headline", ""),
            item.get("url", ""),
            "",
            extra,
        )

    wiki = record.get("wikiResults")
    if wiki:
        add_row(
            "wiki",
            wiki.get("title", ""),
            wiki.get("url", ""),
            wiki.get("description", ""),
        )

    return rows

def export_to_csv(records: List[Dict[str, Any]], path: str) -> None:
    """
    Writes a flattened CSV view of the scraping results.

    Each nested result (organic result, related query, etc.) becomes one row.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    all_rows: List[Dict[str, Any]] = []

    for record in records:
        all_rows.extend(_flatten_record(record))

    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        logger.info("CSV export completed: %s (%d rows)", path, len(all_rows))
    except Exception as exc:
        logger.error("Failed to export CSV to %s: %s", path, exc)
        raise