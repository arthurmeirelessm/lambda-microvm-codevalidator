"""HTML scraping service."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Callable

import requests
from bs4 import BeautifulSoup

try:
    from .exceptions import EmptyContentError, ScrapingError, UnsupportedContentTypeError
    from .settings import AppSettings
except ImportError:  # pragma: no cover - flat package build fallback
    from exceptions import EmptyContentError, ScrapingError, UnsupportedContentTypeError
    from settings import AppSettings

REMOVABLE_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "nav",
    "footer",
    "header",
    "form",
    "aside",
    "iframe",
    "canvas",
    "button",
    "input",
    "select",
    "option",
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapedPage:
    url: str
    title: str
    content: str
    content_length: int
    status_code: int


@dataclass(frozen=True)
class BrowserRenderResult:
    url: str
    title: str
    html: str
    status_code: int


class WebScraper:
    def __init__(
        self,
        settings: AppSettings,
        session: requests.Session | None = None,
        browser_content_loader: Callable[[str], BrowserRenderResult] | None = None,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.session.max_redirects = settings.max_redirects
        self.browser_content_loader = browser_content_loader or self._load_browser_content

    def scrape(self, url: str) -> ScrapedPage:
        try:
            return self._scrape_with_requests(url)
        except UnsupportedContentTypeError:
            raise
        except (ScrapingError, EmptyContentError) as exc:
            if not self.settings.enable_javascript_fallback:
                raise
            logger.info("Retrying scrape with Playwright fallback: %s", exc)
            return self._scrape_with_browser(url, primary_error=exc)

    def _scrape_with_requests(self, url: str) -> ScrapedPage:
        headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
                allow_redirects=True,
                stream=True,
            )
        except requests.Timeout as exc:
            raise ScrapingError("Tempo limite esgotado ao acessar a página.") from exc
        except requests.TooManyRedirects as exc:
            raise ScrapingError("A página excedeu o limite de redirecionamentos.") from exc
        except requests.RequestException as exc:
            raise ScrapingError("Não foi possível extrair o conteúdo da página.") from exc

        status_code = getattr(response, "status_code", 0)
        if status_code >= 400:
            raise ScrapingError("Não foi possível extrair o conteúdo da página.")

        content_type = response.headers.get("Content-Type", "").lower()
        if not any(value in content_type for value in ("text/html", "application/xhtml+xml")):
            raise UnsupportedContentTypeError("A página informada não contém HTML.")

        html = self._read_body(response)
        title, content = self._extract_content(html)
        final_url = getattr(response, "url", url) or url
        return ScrapedPage(
            url=final_url,
            title=title,
            content=content,
            content_length=len(content),
            status_code=status_code,
        )

    def _scrape_with_browser(self, url: str, primary_error: Exception) -> ScrapedPage:
        try:
            rendered_page = self.browser_content_loader(url)
            html_size = len(rendered_page.html.encode("utf-8"))
            if html_size > self.settings.max_response_bytes:
                raise ScrapingError("A resposta excedeu o tamanho máximo permitido.")
            title, content = self._extract_content(
                rendered_page.html,
                preferred_title=rendered_page.title,
            )
            return ScrapedPage(
                url=rendered_page.url,
                title=title,
                content=content,
                content_length=len(content),
                status_code=rendered_page.status_code,
            )
        except (ScrapingError, EmptyContentError, UnsupportedContentTypeError) as exc:
            logger.warning("Playwright fallback failed, returning original error: %s", exc)
            raise primary_error from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Playwright fallback unavailable or failed: %s", exc)
            raise primary_error from exc

    def _read_body(self, response: requests.Response) -> str:
        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > self.settings.max_response_bytes:
                    raise ScrapingError("A resposta excedeu o tamanho máximo permitido.")
                chunks.append(chunk)
        finally:
            response.close()
        encoding = getattr(response, "encoding", None) or "utf-8"
        return b"".join(chunks).decode(encoding, errors="replace")

    def _extract_content(self, html: str, preferred_title: str | None = None) -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")

        for tag in REMOVABLE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        for selector in ('[role="navigation"]', '[aria-hidden="true"]'):
            for element in soup.select(selector):
                element.decompose()

        root = soup.find("main") or soup.find("article") or soup.body or soup
        title = _normalize_whitespace(preferred_title or "")
        if not title:
            title = _normalize_whitespace(soup.title.get_text(" ", strip=True)) if soup.title else ""
        if not title:
            heading = root.find("h1") if hasattr(root, "find") else None
            title = _normalize_whitespace(heading.get_text(" ", strip=True)) if heading else "Sem título"

        content = _normalize_whitespace(root.get_text(" ", strip=True))
        if len(content) < 30:
            raise EmptyContentError("Não foi possível extrair conteúdo textual útil.")
        if len(content) > self.settings.max_content_characters:
            truncated = content[: self.settings.max_content_characters]
            content = truncated.rsplit(" ", 1)[0].strip() or truncated.strip()

        return title, content

    def _load_browser_content(self, url: str) -> BrowserRenderResult:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on runtime packaging
            raise RuntimeError("Playwright não está disponível no ambiente atual.") from exc

        timeout_ms = self.settings.playwright_navigation_timeout_seconds * 1000
        launch_options: dict[str, object] = {
            "headless": True,
            "args": [
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
                "--single-process",
            ],
        }
        if self.settings.playwright_browser_executable_path:
            launch_options["executable_path"] = self.settings.playwright_browser_executable_path

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**launch_options)
                context = browser.new_context(user_agent=self.settings.user_agent)
                page = context.new_page()
                response = page.goto(
                    url,
                    wait_until=self.settings.playwright_wait_until,
                    timeout=timeout_ms,
                )
                page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)

                status_code = response.status if response is not None else 200
                if status_code >= 400:
                    raise ScrapingError("Não foi possível extrair o conteúdo da página.")

                content_type = ""
                if response is not None:
                    content_type = (response.headers or {}).get("content-type", "").lower()
                if content_type and not any(
                    value in content_type for value in ("text/html", "application/xhtml+xml")
                ):
                    raise UnsupportedContentTypeError("A página informada não contém HTML.")

                rendered_html = page.content()
                rendered_title = _normalize_whitespace(page.title())
                final_url = page.url or url
                context.close()
                browser.close()
        except PlaywrightTimeoutError as exc:
            raise ScrapingError("Tempo limite esgotado ao renderizar a página com JavaScript.") from exc
        except PlaywrightError as exc:
            raise ScrapingError("Não foi possível renderizar a página com JavaScript.") from exc

        return BrowserRenderResult(
            url=final_url,
            title=rendered_title,
            html=rendered_html,
            status_code=status_code,
        )


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
