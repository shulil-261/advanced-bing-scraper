thonimport logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("media_parser")

def _safe_text(node: Optional[Tag]) -> str:
    if not node:
        return ""
    return " ".join(node.get_text(strip=True).split())

def parse_images(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract image search style results.

    For real Bing pages this would involve dedicated image search results.
    Here we support simplified patterns for robustness and testing.
    """
    images: List[Dict[str, Any]] = []

    # Pattern for our tests: div.imgres > a[href]
    for container in soup.select("div.imgres, div.image_result, div.b_imageContainer"):
        link = container.find("a", href=True)
        if not link:
            continue
        url = link["href"]
        description = link.get("title") or _safe_text(container)
        images.append({"url": url, "description": description})

    logger.debug("Extracted %d image entries", len(images))
    return images

def parse_videos(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract video-style results.

    Supports a simplified structure for tests and examples.
    """
    videos: List[Dict[str, Any]] = []

    for container in soup.select("div.b_videoResult, div.video_result, li.video"):
        link = container.find("a", href=True)
        if not link:
            continue

        url = link["href"]
        title = link.get("title") or _safe_text(link)
        views_tag = container.select_one(".vc_count, .views")
        channel_tag = container.select_one(".vc_channel, .channel")
        provider_tag = container.select_one(".vc_provider, .provider")

        videos.append(
            {
                "url": url,
                "title": title,
                "views": _safe_text(views_tag),
                "channel": _safe_text(channel_tag),
                "provider": _safe_text(provider_tag),
            }
        )

    logger.debug("Extracted %d video entries", len(videos))
    return videos

def parse_news(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract news results.

    Looks for simple headline + source patterns.
    """
    news_items: List[Dict[str, Any]] = []

    for container in soup.select("div.news-card, li.news, div.b_entityTP, div.b_newsResult"):
        link = container.find("a", href=True)
        if not link:
            continue
        headline = _safe_text(link)
        source_tag = container.select_one(".source, .provider, .b_attribution")
        source = _safe_text(source_tag)
        news_items.append(
            {
                "headline": headline,
                "url": link["href"],
                "source": source,
            }
        )

    logger.debug("Extracted %d news entries", len(news_items))
    return news_items