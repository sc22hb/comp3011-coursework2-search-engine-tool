"""Crawler implementation for the coursework search tool."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
import time
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


QUOTE_PAGE_PATTERN = re.compile(r"^/page/\d+/$")


@dataclass(frozen=True)
class PageData:
    """Represents a crawled page that can later be indexed."""

    url: str
    title: str
    text: str


class Crawler:
    """Crawls the target website and returns page data for indexing."""

    def __init__(
        self,
        base_url: str = "https://quotes.toscrape.com/",
        politeness_window: float = 6.0,
        session: requests.Session | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.base_url = self._normalise_url(base_url)
        self.politeness_window = politeness_window
        self.session = session or requests.Session()
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self._last_request_at: float | None = None

    def crawl(self) -> list[PageData]:
        """Return crawled quote-listing pages from the target website."""
        pages: list[PageData] = []
        queue = deque([self.base_url])
        visited: set[str] = set()

        while queue:
            url = queue.popleft()
            if url in visited:
                continue

            visited.add(url)

            try:
                html = self._fetch_page(url)
            except requests.RequestException:
                continue

            soup = BeautifulSoup(html, "html.parser")
            pages.append(
                PageData(
                    url=url,
                    title=self._extract_title(soup),
                    text=soup.get_text(" ", strip=True),
                )
            )

            for link in self._extract_page_links(soup, url):
                if link not in visited and link not in queue:
                    queue.append(link)

        return pages

    def _fetch_page(self, url: str) -> str:
        self._respect_politeness_window()
        self._last_request_at = self.clock()
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def _respect_politeness_window(self) -> None:
        if self._last_request_at is None:
            return

        elapsed = self.clock() - self._last_request_at
        if elapsed < self.politeness_window:
            self.sleep(self.politeness_window - elapsed)

    def _extract_page_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            candidate = self._normalise_url(urljoin(current_url, anchor["href"]))
            if self._is_allowed_page(candidate):
                links.append(candidate)

        return links

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title = soup.find("title")
        return title.get_text(strip=True) if title else self.base_url

    def _is_allowed_page(self, url: str) -> bool:
        parsed_url = urlparse(url)
        parsed_base = urlparse(self.base_url)

        if (parsed_url.scheme, parsed_url.netloc) != (
            parsed_base.scheme,
            parsed_base.netloc,
        ):
            return False

        return parsed_url.path == "/" or bool(QUOTE_PAGE_PATTERN.match(parsed_url.path))

    def _normalise_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"

        if path != "/" and not path.endswith("/"):
            path = f"{path}/"

        normalised = parsed._replace(path=path, params="", query="", fragment="")
        return urlunparse(normalised)
