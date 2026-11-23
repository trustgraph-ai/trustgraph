"""
Web Remote Action Service - DuckDuckGo search and web content fetching.

Provides two operations via the 'operation' param:
  - search: Search DuckDuckGo and return formatted results.
  - fetch: Fetch and parse content from a webpage URL.

Params for search:
    operation: "search"
    query: The search query string.
    max-results: Maximum number of results (default: 10).

Params for fetch:
    operation: "fetch"
    url: The webpage URL to fetch content from.

Returns:
    TextBlobArtifact with search results or page content.

Example remote-action config (two capabilities, same queue):
{
    "web-search": "{
        \"request-topic\": \"request:tg:web\",
        \"response-topic\": \"response:tg:web\"
    }",
    "web-fetch": "{
        \"request-topic\": \"request:tg:web\",
        \"response-topic\": \"response:tg:web\"
    }"
}
"""

import re
import logging
import urllib.parse
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from ... base import RemoteActionService

logger = logging.getLogger(__name__)

default_ident = "web-action-service"
default_topic = "web"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


class RateLimiter:

    def __init__(self, requests_per_minute=30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        import asyncio
        now = datetime.now()
        self.requests = [
            req for req in self.requests
            if now - req < timedelta(minutes=1)
        ]
        if len(self.requests) >= self.requests_per_minute:
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        self.requests.append(now)


class Processor(RemoteActionService):

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        self.search_limiter = RateLimiter(requests_per_minute=30)
        self.fetch_limiter = RateLimiter(requests_per_minute=20)
        logger.info("Web action service initialized")

    async def execute(self, params, input_artifacts, user_context):

        operation = params.get("operation", "")

        if operation == "search":
            return await self._search(params)
        elif operation == "fetch":
            return await self._fetch(params)
        else:
            raise ValueError(
                f"Unknown operation: '{operation}'. "
                f"Expected 'search' or 'fetch'."
            )

    async def _search(self, params):

        query = params.get("query", "")
        if not query:
            raise ValueError("Missing required parameter: query")

        max_results = int(params.get("max-results", "10"))

        await self.search_limiter.acquire()

        logger.info(f"Searching DuckDuckGo for: {query}")

        data = {"q": query, "b": "", "kl": ""}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://html.duckduckgo.com/html",
                data=data,
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
            )
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup:
            return "TextBlobArtifact", {
                "text": "Failed to parse search results.",
            }

        results = []
        for result in soup.select(".result"):
            title_elem = result.select_one(".result__title")
            if not title_elem:
                continue

            link_elem = title_elem.find("a")
            if not link_elem:
                continue

            title = link_elem.get_text(strip=True)
            link = link_elem.get("href", "")

            if "y.js" in link:
                continue

            if link.startswith("//duckduckgo.com/l/?uddg="):
                link = urllib.parse.unquote(
                    link.split("uddg=")[1].split("&")[0]
                )

            snippet_elem = result.select_one(".result__snippet")
            snippet = (
                snippet_elem.get_text(strip=True) if snippet_elem else ""
            )

            results.append({
                "position": len(results) + 1,
                "title": title,
                "link": link,
                "snippet": snippet,
            })

            if len(results) >= max_results:
                break

        if not results:
            text = (
                "No results were found for your search query. "
                "This could be due to DuckDuckGo's bot detection "
                "or the query returned no matches."
            )
        else:
            lines = [f"Found {len(results)} search results:\n"]
            for r in results:
                lines.append(f"{r['position']}. {r['title']}")
                lines.append(f"   URL: {r['link']}")
                lines.append(f"   Summary: {r['snippet']}")
                lines.append("")
            text = "\n".join(lines)

        logger.info(f"Search returned {len(results)} results")

        return "TextBlobArtifact", {"text": text}

    async def _fetch(self, params):

        url = params.get("url", "")
        if not url:
            raise ValueError("Missing required parameter: url")

        await self.fetch_limiter.acquire()

        logger.info(f"Fetching content from: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=30.0,
            )
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        text = soup.get_text()

        lines = (line.strip() for line in text.splitlines())
        chunks = (
            phrase.strip()
            for line in lines
            for phrase in line.split("  ")
        )
        text = " ".join(chunk for chunk in chunks if chunk)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 8000:
            text = text[:8000] + "... [content truncated]"

        logger.info(f"Fetched {len(text)} characters from {url}")

        return "TextBlobArtifact", {"text": text}

    @staticmethod
    def add_args(parser):
        RemoteActionService.add_args(parser)
        for action in parser._actions:
            if '--topic' in action.option_strings:
                action.default = default_topic
                break


def run():
    Processor.launch(default_ident, __doc__)
