thonimport logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .organic_handler import (
    parse_organic_results,
    parse_related_queries,
    parse_people_also_ask,
    parse_wiki_results,
)
from .media_parser import parse_images, parse_videos, parse_news

logger = logging.getLogger("bing_parser")

@dataclass
class ParsedResult:
    url: str
    keyword: str
    page_number: int
    organic_results: List[Dict[str, Any]]
    related_queries: List[Dict[str, Any]]
    people_also_ask: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    videos: List[Dict[str, Any]]
    news: List[Dict[str, Any]]
    wiki_results: Optional[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "keyword": self.keyword,
            "pageNumber": self.page_number,
            "organicResults": self.organic_results,
            "relatedQueries": self.related_queries,
            "peopleAlsoAsk": self.people_also_ask,
            "images": self.images,
            "videos": self.videos,
            "news": self.news,
            "wikiResults": self.wiki_results,
        }

class BingSearchParser:
    """
    Parses Bing search result HTML into a structured dictionary.

    The parser is resilient: if a particular section cannot be parsed,
    it logs the error and returns an empty list for that section.
    """

    def parse(
        self,
        html: str,
        keyword: str,
        page_number: int,
        url: str,
    ) -> Dict[str, Any]:
        logger.debug(
            "Parsing HTML for keyword=%s, page=%d, url=%s", keyword, page_number, url
        )

        soup = BeautifulSoup(html, "html.parser")

        try:
            organic_results = parse_organic_results(soup)
        except Exception as exc:
            logger.error("Error parsing organic results: %s", exc)
            organic_results = []

        try:
            related_queries = parse_related_queries(soup)
        except Exception as exc:
            logger.error("Error parsing related queries: %s", exc)
            related_queries = []

        try:
            people_also_ask = parse_people_also_ask(soup)
        except Exception as exc:
            logger.error("Error parsing People Also Ask: %s", exc)
            people_also_ask = []

        try:
            images = parse_images(soup)
        except Exception as exc:
            logger.error("Error parsing images: %s", exc)
            images = []

        try:
            videos = parse_videos(soup)
        except Exception as exc:
            logger.error("Error parsing videos: %s", exc)
            videos = []

        try:
            news = parse_news(soup)
        except Exception as exc:
            logger.error("Error parsing news: %s", exc)
            news = []

        try:
            wiki_results = parse_wiki_results(soup)
        except Exception as exc:
            logger.error("Error parsing wiki/knowledge panel: %s", exc)
            wiki_results = None

        parsed = ParsedResult(
            url=url,
            keyword=keyword,
            page_number=page_number,
            organic_results=organic_results,
            related_queries=related_queries,
            people_also_ask=people_also_ask,
            images=images,
            videos=videos,
            news=news,
            wiki_results=wiki_results,
        )

        record = parsed.as_dict()
        logger.debug("Parsed record summary: %s", {k: len(v) if isinstance(v, list) else v for k, v in record.items()})
        return record