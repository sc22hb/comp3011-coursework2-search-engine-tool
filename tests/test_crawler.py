from typing import Callable

import requests

from crawler import Crawler


class StubResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class StubSession:
    def __init__(self, handler: Callable[[str], StubResponse]) -> None:
        self.handler = handler
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int) -> StubResponse:
        self.requested_urls.append(url)
        return self.handler(url)


def test_crawler_class_exists() -> None:
    crawler = Crawler()
    assert isinstance(crawler, Crawler)


def test_crawler_collects_paginated_pages_without_duplicates() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <head><title>Quotes to Scrape</title></head>
                <body>
                    <a href="/page/2/">Next</a>
                    <a href="/page/2/">Duplicate</a>
                    <a href="/author/albert-einstein">Ignored</a>
                    <div>First page text</div>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/page/2/": """
            <html>
                <head><title>Quotes to Scrape - Page 2</title></head>
                <body>
                    <a href="/">Back</a>
                    <div>Second page text</div>
                </body>
            </html>
        """,
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]
    assert session.requested_urls == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]


def test_crawler_treats_page_one_as_the_root_page() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <body>
                    <a href="/page/1/">Page 1</a>
                    <a href="/page/2/">Page 2</a>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/page/2/": "<html><body>Page 2</body></html>",
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]


def test_crawler_ignores_external_links() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <body>
                    <a href="https://example.com/page/2/">External</a>
                </body>
            </html>
        """
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == ["https://quotes.toscrape.com/"]


def test_crawler_extracts_quote_text_without_layout_boilerplate() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <head><title>Quotes to Scrape</title></head>
                <body>
                    <nav>Login Home</nav>
                    <div class="quote">
                        <span class="text">"Good friends, good books."</span>
                        <span>by <small class="author">Jane Austen</small></span>
                        <div class="tags">
                            <a class="tag" href="/tag/friends/">friends</a>
                        </div>
                    </div>
                    <div class="col-md-4 tags-box">
                        <span class="tag-item"><a class="tag">Top Ten Tags</a></span>
                    </div>
                    <footer>Made with ❤ by Someone</footer>
                </body>
            </html>
        """,
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert len(crawled_pages) == 1
    assert crawled_pages[0].text == '"Good friends, good books." Jane Austen'


def test_crawler_waits_for_politeness_window_between_requests() -> None:
    current_time = {"value": 0.0}
    sleep_calls: list[float] = []

    def clock() -> float:
        return current_time["value"]

    def sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        current_time["value"] += seconds

    def handler(url: str) -> StubResponse:
        if url == "https://quotes.toscrape.com/":
            current_time["value"] += 2.0
            return StubResponse(
                """
                <html>
                    <body><a href="/page/2/">Next</a></body>
                </html>
                """
            )

        return StubResponse("<html><body>Last page</body></html>")

    session = StubSession(handler)
    crawler = Crawler(
        session=session,
        politeness_window=6.0,
        clock=clock,
        sleep=sleep,
    )

    crawler.crawl()

    assert sleep_calls == [4.0]


def test_crawler_skips_failed_requests_and_continues() -> None:
    def handler(url: str) -> StubResponse:
        if url == "https://quotes.toscrape.com/page/3/":
            raise requests.RequestException("Temporary failure")

        if url == "https://quotes.toscrape.com/":
            return StubResponse(
                """
                <html>
                    <body>
                        <a href="/page/2/">Page 2</a>
                        <a href="/page/3/">Page 3</a>
                    </body>
                </html>
                """
            )

        return StubResponse("<html><body>Page 2</body></html>")

    session = StubSession(handler)
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]


def test_crawler_raises_if_initial_request_fails() -> None:
    session = StubSession(
        lambda url: (_ for _ in ()).throw(requests.RequestException("Root failure"))
    )
    crawler = Crawler(session=session, politeness_window=0)

    try:
        crawler.crawl()
    except requests.RequestException as error:
        assert "Root failure" in str(error)
    else:
        assert False, "Expected the crawler to raise when the initial request fails."
