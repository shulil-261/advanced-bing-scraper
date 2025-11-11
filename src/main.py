thonimport argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

# Ensure local imports work when running as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from extractors.bing_parser import BingSearchParser  # type: ignore
from outputs.export_json import export_to_json  # type: ignore
from outputs.export_csv import export_to_csv  # type: ignore
from outputs.export_xlsx import export_to_xlsx  # type: ignore

try:
    import requests
except ImportError as exc:  # pragma: no cover - import-time safety
    raise SystemExit(
        "The 'requests' package is required. Install dependencies with:\n"
        "pip install -r requirements.txt"
    ) from exc

DEFAULT_CONFIG_PATH = os.path.join(CURRENT_DIR, "config", "settings.example.json")
DEFAULT_INPUT_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "data", "input.sample.json")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")

def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_config(path: str) -> Dict[str, Any]:
    logger = logging.getLogger("config")
    config: Dict[str, Any] = {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "timeout": 10,
        "max_retries": 2,
        "default_output_dir": DEFAULT_OUTPUT_DIR,
        "bing_base_url": "https://www.bing.com/search",
    }

    if not os.path.exists(path):
        logger.warning("Config file %s not found. Using built-in defaults.", path)
        return config

    try:
        with open(path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        if isinstance(user_config, dict):
            config.update(user_config)
        else:
            logger.warning("Config file %s does not contain a JSON object.", path)
    except Exception as exc:
        logger.error("Failed to read config file %s: %s", path, exc)

    return config

def load_jobs(path: str) -> List[Dict[str, Any]]:
    logger = logging.getLogger("input")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file {path} not found.")

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    jobs: List[Dict[str, Any]] = []

    if isinstance(payload, list):
        # Assume already a list of job dicts
        jobs = payload
    elif isinstance(payload, dict):
        if "queries" in payload and isinstance(payload["queries"], list):
            jobs = payload["queries"]
        else:
            # Single job dict
            jobs = [payload]
    else:
        raise ValueError("Input JSON must be an object or a list of objects.")

    normalized_jobs: List[Dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            logger.warning("Skipping non-object job entry: %r", job)
            continue
        keyword = job.get("keyword")
        if not keyword:
            logger.warning("Skipping job without 'keyword': %r", job)
            continue
        pages = int(job.get("pages", 1))
        normalized_jobs.append({"keyword": str(keyword), "pages": max(1, pages)})

    if not normalized_jobs:
        raise ValueError("No valid jobs found in input JSON.")

    return normalized_jobs

def build_bing_url(base_url: str, keyword: str, page_number: int) -> str:
    from urllib.parse import urlencode

    params = {"q": keyword}
    if page_number > 1:
        # Bing paging: "first" is 1-based index of first result
        params["first"] = (page_number - 1) * 10 + 1

    return f"{base_url}?{urlencode(params)}"

def fetch_bing_html(
    url: str, user_agent: str, timeout: int, max_retries: int
) -> str:
    logger = logging.getLogger("fetch")
    headers = {"User-Agent": user_agent}

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("Requesting URL (attempt %d/%d): %s", attempt, max_retries, url)
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # pragma: no cover - network dependent
            last_exc = exc
            logger.warning("Request attempt %d failed: %s", attempt, exc)

    error_message = f"Failed to fetch {url} after {max_retries} attempts"
    logger.error("%s. Last error: %s", error_message, last_exc)
    raise RuntimeError(error_message) from last_exc

def run_scraper(
    config_path: str,
    input_path: str,
    output_format: str,
    output_dir: str | None = None,
) -> Dict[str, Any]:
    config = load_config(config_path)
    jobs = load_jobs(input_path)

    if output_dir is None:
        output_dir = config.get("default_output_dir", DEFAULT_OUTPUT_DIR)

    os.makedirs(output_dir, exist_ok=True)

    parser = BingSearchParser()
    bing_base_url: str = config.get("bing_base_url", "https://www.bing.com/search")
    user_agent: str = config.get("user_agent")
    timeout: int = int(config.get("timeout", 10))
    max_retries: int = int(config.get("max_retries", 2))

    all_results: List[Dict[str, Any]] = []
    logger = logging.getLogger("scraper")

    for job in jobs:
        keyword: str = job["keyword"]
        pages: int = job.get("pages", 1)

        logger.info("Processing keyword '%s' (%d page(s))", keyword, pages)

        for page_number in range(1, pages + 1):
            url = build_bing_url(bing_base_url, keyword, page_number)
            try:
                html = fetch_bing_html(url, user_agent, timeout, max_retries)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.error("Skipping page due to fetch error: %s", exc)
                continue

            record = parser.parse(html, keyword, page_number, url)
            all_results.append(record)

    if not all_results:
        raise RuntimeError("No results were collected. Check connectivity or input keywords.")

    base_output_path = os.path.join(output_dir, "bing_results")

    if output_format in ("json", "all"):
        json_path = f"{base_output_path}.json"
        export_to_json(all_results, json_path)

    if output_format in ("csv", "all"):
        csv_path = f"{base_output_path}.csv"
        export_to_csv(all_results, csv_path)

    if output_format in ("xlsx", "all"):
        xlsx_path = f"{base_output_path}.xlsx"
        export_to_xlsx(all_results, xlsx_path)

    summary = {
        "jobs": len(jobs),
        "records": len(all_results),
        "output_base_path": base_output_path,
    }
    logging.getLogger("summary").info("Scraping completed: %s", summary)
    return summary

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Advanced Bing Scraper - collects structured Bing search data."
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to settings JSON (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Path to input JSON describing keywords (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Output directory (default: configured default_output_dir or ./data)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "xlsx", "all"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)

def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)
    run_scraper(
        config_path=args.config,
        input_path=args.input,
        output_format=args.format,
        output_dir=args.output_dir,
    )

if __name__ == "__main__":
    main()