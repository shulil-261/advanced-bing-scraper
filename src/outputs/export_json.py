thonimport json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger("export_json")

def export_to_json(records: List[Dict[str, Any]], path: str) -> None:
    """
    Writes the full list of scraping records to a JSON file.

    The file is written with UTF-8 encoding and pretty-printed for readability.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        logger.info("JSON export completed: %s (%d records)", path, len(records))
    except Exception as exc:
        logger.error("Failed to export JSON to %s: %s", path, exc)
        raise