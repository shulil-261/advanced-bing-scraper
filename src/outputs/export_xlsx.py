thonimport logging
import os
from typing import Any, Dict, List

from openpyxl import Workbook

logger = logging.getLogger("export_xlsx")

def export_to_xlsx(records: List[Dict[str, Any]], path: str) -> None:
    """
    Writes a simplified XLSX workbook containing a summary sheet
    of organic results plus counts of other sections.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Organic Results"

    ws.append(
        [
            "Keyword",
            "Page",
            "Title",
            "URL",
            "Description",
            "RelatedQueriesCount",
            "PeopleAlsoAskCount",
            "ImagesCount",
            "VideosCount",
            "NewsCount",
        ]
    )

    for record in records:
        keyword = record.get("keyword", "")
        page = record.get("pageNumber", "")
        related_count = len(record.get("relatedQueries", []))
        paa_count = len(record.get("peopleAlsoAsk", []))
        images_count = len(record.get("images", []))
        videos_count = len(record.get("videos", []))
        news_count = len(record.get("news", []))

        organic_results = record.get("organicResults", []) or [{}]
        for item in organic_results:
            ws.append(
                [
                    keyword,
                    page,
                    item.get("title", ""),
                    item.get("url", ""),
                    item.get("description", ""),
                    related_count,
                    paa_count,
                    images_count,
                    videos_count,
                    news_count,
                ]
            )

    try:
        wb.save(path)
        logger.info("XLSX export completed: %s", path)
    except Exception as exc:
        logger.error("Failed to export XLSX to %s: %s", path, exc)
        raise