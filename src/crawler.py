"""Crawler implementation for the coursework search tool."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


NON_HTML_SUFFIXES = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".webp",
    ".xml",
    ".zip",
}


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
        """Return crawled in-scope pages from the target website."""
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
                if url == self.base_url:
                    raise
                continue

            soup = BeautifulSoup(html, "html.parser")
            pages.append(
                PageData(
                    url=url,
                    title=self._extract_title(soup),
                    text=self._extract_page_text(soup),
                )
            )

            for link in self._extract_page_links(soup, url):
                if link not in visited and link not in queue:
                    queue.append(link)

        return pages

    def _fetch_page(self, url: str) -> str:
        """Download a single page, respecting the politeness window."""
        self._respect_politeness_window()
        self._last_request_at = self.clock()
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def _respect_politeness_window(self) -> None:
        """Sleep until the minimum gap between requests has elapsed."""
        if self._last_request_at is None:
            return

        elapsed = self.clock() - self._last_request_at
        if elapsed < self.politeness_window:
            self.sleep(self.politeness_window - elapsed)

    def _extract_page_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        """Return normalised in-scope links found on the page."""
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            candidate = self._normalise_url(urljoin(current_url, anchor["href"]))
            if self._is_allowed_page(candidate):
                links.append(candidate)

        return links

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Return the page title or fall back to the base URL."""
        title = soup.find("title")
        return title.get_text(strip=True) if title else self.base_url

    def _extract_page_text(self, soup: BeautifulSoup) -> str:
        """Return indexable page text while trimming repeated site boilerplate."""
        working_soup = BeautifulSoup(str(soup), "html.parser")

        for selector in (
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "div.col-md-4.tags-box",
            "div.header-box",
        ):
            for element in working_soup.select(selector):
                element.decompose()

        content_root = working_soup.select_one("div.container") or working_soup.body or working_soup
        return content_root.get_text(" ", strip=True)

    def _is_allowed_page(self, url: str) -> bool:
        """Return True when *url* is an in-scope HTML page on the target site."""
        parsed_url = urlparse(url)
        parsed_base = urlparse(self.base_url)

        if (parsed_url.scheme, parsed_url.netloc) != (
            parsed_base.scheme,
            parsed_base.netloc,
        ):
            return False

        path = parsed_url.path.lower()
        return not any(path.endswith(suffix) for suffix in NON_HTML_SUFFIXES)

    def _normalise_url(self, url: str) -> str:
        """Canonicalise a URL by enforcing trailing slashes and collapsing /page/1/."""
        parsed = urlparse(url)
        path = parsed.path or "/"
        last_segment = path.rsplit("/", maxsplit=1)[-1]

        if path == "/page/1/":
            path = "/"

        if path != "/" and not path.endswith("/") and "." not in last_segment:
            path = f"{path}/"

        normalised = parsed._replace(path=path, params="", query="", fragment="")
        return urlunparse(normalised)
