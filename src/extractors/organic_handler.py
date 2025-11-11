thonimport logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("organic_handler")

def _safe_text(node: Optional[Tag]) -> str:
    if not node:
        return ""
    return " ".join(node.get_text(strip=True).split())

def parse_organic_results(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extracts organic search results from Bing HTML.

    Targets typical Bing DOM patterns such as 'li.b_algo' entries.
    """
    results: List[Dict[str, Any]] = []

    for li in soup.select("li.b_algo"):
        title_tag = li.select_one("h2 a")
        snippet_tag = li.select_one("p")
        url = title_tag.get("href") if title_tag and title_tag.has_attr("href") else ""

        result = {
            "title": _safe_text(title_tag),
            "url": url,
            "description": _safe_text(snippet_tag),
        }

        if result["title"] or result["url"]:
            results.append(result)

    logger.debug("Extracted %d organic results", len(results))
    return results

def parse_related_queries(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extracts 'related searches' queries.

    Looks for lists commonly used by Bing for related terms.
    """
    related: List[Dict[str, Any]] = []

    # Common pattern: "Related searches" near 'b_rs' or generic suggestion lists
    candidate_lists = soup.select("ul.b_vList, ul.b_list, ul.b_rs, ul.related, ul.suggestions")

    for ul in candidate_lists:
        for li in ul.select("li"):
            a = li.find("a")
            if not a:
                continue
            text = _safe_text(a)
            href = a.get("href", "")
            if text:
                related.append({"text": text, "url": href})

    # Deduplicate by text/url combination
    seen = set()
    unique_related: List[Dict[str, Any]] = []
    for item in related:
        key = (item["text"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique_related.append(item)

    logger.debug("Extracted %d related queries", len(unique_related))
    return unique_related

def parse_people_also_ask(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extracts 'People Also Ask' style Q&A.

    The real Bing DOM can be complex; here we support a couple of simple patterns
    and keep it resilient.
    """
    qa_items: List[Dict[str, Any]] = []

    # Pattern 1: custom markup in our tests (b_expando with b_qtitle and b_answerText)
    for container in soup.select("div.b_expando"):
        question_tag = container.select_one(".b_qtitle, .b_question, h3, summary")
        answer_tag = container.select_one(".b_answerText, .b_paractl, p")
        question = _safe_text(question_tag)
        answer = _safe_text(answer_tag)
        if question:
            qa_items.append({"question": question, "answer": answer})

    # Pattern 2: more generic Q&A lists (fallback)
    if not qa_items:
        for qa_block in soup.select("div.paa, div.people-also-ask"):
            for q in qa_block.select("div.question, dt"):
                question = _safe_text(q)
                if not question:
                    continue
                # Simple heuristic: answer is next sibling paragraph or dd
                answer_tag = q.find_next_sibling(["p", "dd"])
                answer = _safe_text(answer_tag)
                qa_items.append({"question": question, "answer": answer})

    logger.debug("Extracted %d People Also Ask entries", len(qa_items))
    return qa_items

def parse_wiki_results(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """
    Extracts a simple wiki/knowledge-panel style result when present.

    We intentionally keep this generic: look for an info panel with a header and snippet.
    """
    # Pattern for a knowledge panel style block
    panel = soup.select_one("div.b_entityTP, div.b_entityPanel, div.wiki-panel")
    if not panel:
        return None

    title_tag = panel.select_one("h2, h1, .b_entityTitle, .title")
    snippet_tag = panel.select_one("p, .snippet, .description")
    link_tag = panel.select_one("a[href*='wikipedia.org'], a[href]")

    wiki = {
        "title": _safe_text(title_tag),
        "description": _safe_text(snippet_tag),
        "url": link_tag.get("href") if link_tag and link_tag.has_attr("href") else "",
    }

    if not any(wiki.values()):
        return None

    logger.debug("Extracted wiki/knowledge panel result")
    return wiki