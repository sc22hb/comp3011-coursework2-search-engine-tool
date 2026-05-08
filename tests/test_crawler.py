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


def test_crawler_defaults_to_a_six_second_politeness_window() -> None:
    crawler = Crawler()
    assert crawler.politeness_window == 6.0


def test_crawler_collects_same_domain_pages_without_duplicates() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <head><title>Quotes to Scrape</title></head>
                <body>
                    <a href="/page/2/">Next</a>
                    <a href="/page/2/">Duplicate</a>
                    <a href="/author/albert-einstein">Author</a>
                    <a href="/tag/life/">Tag</a>
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
        "https://quotes.toscrape.com/author/albert-einstein/": """
            <html>
                <head><title>Albert Einstein</title></head>
                <body><div class="author-details">Relativity</div></body>
            </html>
        """,
        "https://quotes.toscrape.com/tag/life/": """
            <html>
                <head><title>Life Quotes</title></head>
                <body><div>Life tag page</div></body>
            </html>
        """,
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/author/albert-einstein/",
        "https://quotes.toscrape.com/tag/life/",
    ]
    assert session.requested_urls == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/author/albert-einstein/",
        "https://quotes.toscrape.com/tag/life/",
    ]


def test_crawler_treats_page_one_as_the_root_page() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <body>
                    <a href="/page/1/">Page 1</a>
                    <a href="/author/jane-austen/">Author</a>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/author/jane-austen/": "<html><body>Author</body></html>",
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert [page.url for page in crawled_pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/author/jane-austen/",
    ]


def test_crawler_ignores_external_links() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <body>
                    <a href="https://example.com/page/2/">External</a>
                    <a href="/static/site.css">Stylesheet</a>
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
                    <div class="container">
                        <div class="row header-box">
                            <h1>Quotes to Scrape</h1>
                            <ul><li><a href="/login">Login</a></li></ul>
                        </div>
                        <div class="quote">
                            <span class="text">"Good friends, good books."</span>
                            <span>by <small class="author">Jane Austen</small></span>
                            <div class="tags">
                                <a class="tag" href="/tag/friends/">friends</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 tags-box">
                        <span class="tag-item"><a class="tag">Top Ten Tags</a></span>
                    </div>
                    <footer>Made with ❤ by Someone</footer>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/tag/friends/": """
            <html>
                <head><title>Friend Quotes</title></head>
                <body>
                    <div class="container">Quotes tagged friends</div>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/login/": """
            <html>
                <head><title>Login</title></head>
                <body><div class="container">Login page</div></body>
            </html>
        """,
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert len(crawled_pages) == 3
    assert crawled_pages[0].text == '"Good friends, good books." by Jane Austen friends'


def test_crawler_extracts_text_from_non_quote_pages() -> None:
    pages = {
        "https://quotes.toscrape.com/": """
            <html>
                <body>
                    <a href="/author/albert-einstein/">About Einstein</a>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/author/albert-einstein/": """
            <html>
                <head><title>Albert Einstein</title></head>
                <body>
                    <nav>Home Login</nav>
                    <div class="container">
                        <div class="row header-box">
                            <h1>Quotes to Scrape</h1>
                            <ul><li><a href="/login">Login</a></li></ul>
                        </div>
                        <h3 class="author-title">Albert Einstein</h3>
                        <span class="author-born-date">March 14, 1879</span>
                        <div class="author-description">Developed the theory of relativity.</div>
                    </div>
                    <footer>Made with love</footer>
                </body>
            </html>
        """,
        "https://quotes.toscrape.com/login/": """
            <html>
                <head><title>Login</title></head>
                <body><div class="container">Login page</div></body>
            </html>
        """,
    }

    session = StubSession(lambda url: StubResponse(pages[url]))
    crawler = Crawler(session=session, politeness_window=0)

    crawled_pages = crawler.crawl()

    assert crawled_pages[1].text == "Albert Einstein March 14, 1879 Developed the theory of relativity."


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
        if url == "https://quotes.toscrape.com/tag/failure/":
            raise requests.RequestException("Temporary failure")

        if url == "https://quotes.toscrape.com/":
            return StubResponse(
                """
                <html>
                    <body>
                        <a href="/page/2/">Page 2</a>
                        <a href="/tag/failure/">Tag</a>
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
