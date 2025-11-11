thonimport json
import os
import sys
from typing import Any, Dict

import pytest

# Ensure we can import from src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from extractors.bing_parser import BingSearchParser  # type: ignore
from outputs.export_json import export_to_json  # type: ignore

SAMPLE_HTML = """
<html>
  <body>
    <ol id="b_results">
      <li class="b_algo">
        <h2><a href="https://www.tripadvisor.com/Restaurants-g60763-New_York_City_New_York.html">10 Best Restaurants in NYC - Updated 2023</a></h2>
        <p>Discover the top restaurants in NYC, from fine dining to casual spots...</p>
      </li>
    </ol>

    <div id="b_rs">
      <ul class="b_vList">
        <li><a href="https://www.bing.com/search?q=best+pizza+restaurants+in+nyc">best pizza restaurants in nyc</a></li>
      </ul>
    </div>

    <div class="b_expando">
      <div class="b_qtitle">What are the best fine dining restaurants in NYC?</div>
      <div class="b_answerText">Some of the best fine dining options in NYC include Eleven Madison Park and Le Bernardin.</div>
    </div>

    <div class="imgres">
      <a href="https://www.bing.com/images/search?q=best+restaurants+in+NYC&id=123456" title="Top-rated restaurants in NYC with stunning views."></a>
    </div>

    <div class="b_videoResult">
      <a href="https://www.bing.com/videos/search?q=best+restaurants+in+NYC&docid=1234" title="Top 10 Restaurants in NYC">Top 10 Restaurants in NYC</a>
      <span class="vc_count">100K</span>
      <span class="vc_channel">NYC Eats</span>
      <span class="vc_provider">YouTube</span>
    </div>

    <div class="b_newsResult">
      <a href="https://example.com/news1">NYC dining scene continues to grow</a>
      <span class="source">Example News</span>
    </div>

    <div class="b_entityTP">
      <h2>New York City</h2>
      <p>New York City is the most populous city in the United States.</p>
      <a href="https://en.wikipedia.org/wiki/New_York_City">Wikipedia</a>
    </div>
  </body>
</html>
"""

def test_bing_parser_extracts_core_sections(tmp_path: Any) -> None:
    parser = BingSearchParser()
    record: Dict[str, Any] = parser.parse(
        html=SAMPLE_HTML,
        keyword="best restaurants in NYC",
        page_number=1,
        url="https://www.bing.com/search?q=best+restaurants+in+NYC",
    )

    # Organic results
    organic = record.get("organicResults", [])
    assert len(organic) == 1
    assert organic[0]["title"].startswith("10 Best Restaurants in NYC")

    # Related queries
    related = record.get("relatedQueries", [])
    assert any("pizza" in item["text"] for item in related)

    # People Also Ask
    paa = record.get("peopleAlsoAsk", [])
    assert any("fine dining restaurants in NYC" in item["question"] for item in paa)
    assert any("Eleven Madison Park" in item["answer"] for item in paa)

    # Images
    images = record.get("images", [])
    assert len(images) == 1
    assert images[0]["url"].startswith("https://www.bing.com/images/search")

    # Videos
    videos = record.get("videos", [])
    assert len(videos) == 1
    assert videos[0]["channel"] == "NYC Eats"
    assert videos[0]["provider"] == "YouTube"

    # News
    news = record.get("news", [])
    assert len(news) == 1
    assert "NYC dining scene" in news[0]["headline"]

    # Wiki / knowledge panel
    wiki = record.get("wikiResults")
    assert wiki is not None
    assert wiki["title"] == "New York City"
    assert "wikipedia.org" in wiki["url"]

    # Quick smoke test for JSON export
    out_file = tmp_path / "results.json"
    export_to_json([record], str(out_file))
    assert out_file.exists()

    with out_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert data[0]["keyword"] == "best restaurants in NYC"

def test_parser_handles_empty_html() -> None:
    parser = BingSearchParser()
    record = parser.parse("", "empty", 1, "https://www.bing.com/search?q=empty")
    assert record["keyword"] == "empty"
    assert record["pageNumber"] == 1
    assert record["organicResults"] == []
    assert record["relatedQueries"] == []
    assert record["peopleAlsoAsk"] == []
    assert record["images"] == []
    assert record["videos"] == []
    assert record["news"] == []