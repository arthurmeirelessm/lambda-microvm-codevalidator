import requests
import pytest

from app.exceptions import EmptyContentError, ScrapingError, UnsupportedContentTypeError
from app.scraper import BrowserRenderResult, WebScraper
from app.settings import AppSettings


class FakeResponse:
    def __init__(self, body: bytes, *, status_code: int = 200, content_type: str = 'text/html; charset=utf-8', url: str = 'https://example.com/article') -> None:
        self._body = body
        self.status_code = status_code
        self.headers = {'Content-Type': content_type}
        self.url = url
        self.encoding = 'utf-8'
        self.closed = False

    def iter_content(self, chunk_size: int = 8192):
        for index in range(0, len(self._body), chunk_size):
            yield self._body[index:index + chunk_size]

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.max_redirects = 0

    def get(self, *_args, **_kwargs):
        if self.error is not None:
            raise self.error
        return self.response


def make_scraper(
    *,
    response=None,
    error=None,
    browser_content_loader=None,
    max_response_bytes: int = 2_000_000,
    max_content_characters: int = 50_000,
    enable_javascript_fallback: bool = True,
) -> WebScraper:
    settings = AppSettings(
        max_response_bytes=max_response_bytes,
        max_content_characters=max_content_characters,
        enable_javascript_fallback=enable_javascript_fallback,
    )
    return WebScraper(
        settings,
        session=FakeSession(response=response, error=error),
        browser_content_loader=browser_content_loader,
    )


def test_scraper_extracts_valid_html_page() -> None:
    html = b'<html><head><title>Example</title></head><body><main><p>Important content for the example page used in tests.</p></main></body></html>'
    page = make_scraper(response=FakeResponse(html)).scrape('https://example.com/article')
    assert page.title == 'Example'
    assert 'Important content' in page.content


def test_scraper_removes_scripts_and_styles() -> None:
    html = b'<html><head><title>Example</title><style>.x{display:none}</style></head><body><main><script>alert(1)</script><p>Main content with enough text to remain useful after cleanup.</p></main></body></html>'
    page = make_scraper(response=FakeResponse(html)).scrape('https://example.com/article')
    assert 'alert' not in page.content
    assert 'display:none' not in page.content


def test_scraper_extracts_title() -> None:
    html = b'<html><head><title>Useful Title</title></head><body><main><p>Meaningful body text that contains enough words for extraction.</p></main></body></html>'
    page = make_scraper(response=FakeResponse(html)).scrape('https://example.com/article')
    assert page.title == 'Useful Title'


def test_scraper_rejects_page_without_meaningful_text() -> None:
    html = b'<html><head><title>Empty</title></head><body><main><p>short</p></main></body></html>'
    with pytest.raises(EmptyContentError):
        make_scraper(response=FakeResponse(html)).scrape('https://example.com/article')


def test_scraper_handles_timeout() -> None:
    with pytest.raises(ScrapingError):
        make_scraper(error=requests.Timeout('boom')).scrape('https://example.com/article')


def test_scraper_handles_connection_error() -> None:
    with pytest.raises(ScrapingError):
        make_scraper(error=requests.ConnectionError('boom')).scrape('https://example.com/article')


def test_scraper_accepts_redirected_response() -> None:
    html = b'<html><head><title>Redirected</title></head><body><main><p>Redirected content with enough text to be considered valid.</p></main></body></html>'
    response = FakeResponse(html, url='https://example.com/final')
    page = make_scraper(response=response).scrape('https://example.com/start')
    assert page.url == 'https://example.com/final'


def test_scraper_rejects_non_html_content_type() -> None:
    response = FakeResponse(b'{"ok": true}', content_type='application/json')
    with pytest.raises(UnsupportedContentTypeError):
        make_scraper(response=response).scrape('https://example.com/api')


def test_scraper_does_not_fallback_for_non_html_content_type() -> None:
    response = FakeResponse(b'{"ok": true}', content_type='application/json')

    def unexpected_browser_call(_url: str) -> BrowserRenderResult:
        raise AssertionError("Browser fallback should not run for non-HTML responses.")

    with pytest.raises(UnsupportedContentTypeError):
        make_scraper(
            response=response,
            browser_content_loader=unexpected_browser_call,
        ).scrape('https://example.com/api')


def test_scraper_rejects_response_larger_than_limit() -> None:
    body = b'a' * 64
    response = FakeResponse(body)
    with pytest.raises(ScrapingError):
        make_scraper(response=response, max_response_bytes=32).scrape('https://example.com/article')


def test_scraper_rejects_http_error_status() -> None:
    response = FakeResponse(b'<html></html>', status_code=503)
    with pytest.raises(ScrapingError):
        make_scraper(response=response).scrape('https://example.com/article')


def test_scraper_falls_back_to_playwright_when_request_fails() -> None:
    browser_page = BrowserRenderResult(
        url='https://example.com/article',
        title='Rendered Title',
        html='<html><body><main><p>Content rendered by JavaScript with enough text to be useful.</p></main></body></html>',
        status_code=200,
    )
    page = make_scraper(
        error=requests.ConnectionError('boom'),
        browser_content_loader=lambda _url: browser_page,
    ).scrape('https://example.com/article')
    assert page.title == 'Rendered Title'
    assert 'rendered by JavaScript' in page.content


def test_scraper_falls_back_to_playwright_when_request_content_is_empty() -> None:
    response = FakeResponse(b'<html><head><title>Stub</title></head><body><main><p>short</p></main></body></html>')
    browser_page = BrowserRenderResult(
        url='https://example.com/article',
        title='Hydrated Page',
        html='<html><body><main><p>Hydrated content from the browser fallback contains enough detail for extraction.</p></main></body></html>',
        status_code=200,
    )
    page = make_scraper(
        response=response,
        browser_content_loader=lambda _url: browser_page,
    ).scrape('https://example.com/article')
    assert page.title == 'Hydrated Page'
    assert 'Hydrated content' in page.content


def test_scraper_does_not_fallback_when_disabled() -> None:
    with pytest.raises(ScrapingError):
        make_scraper(
            error=requests.ConnectionError('boom'),
            browser_content_loader=lambda _url: BrowserRenderResult(
                url='https://example.com/article',
                title='Rendered Title',
                html='<html><body><main><p>Rendered content should not be used.</p></main></body></html>',
                status_code=200,
            ),
            enable_javascript_fallback=False,
        ).scrape('https://example.com/article')
