"""HTML scraping service."""

from __future__ import annotations

from dataclasses import dataclass
import re

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


@dataclass(frozen=True)
class ScrapedPage:
    url: str
    title: str
    content: str
    content_length: int
    status_code: int


class WebScraper:
    def __init__(self, settings: AppSettings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.session.max_redirects = settings.max_redirects

    def scrape(self, url: str) -> ScrapedPage:
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

    def _extract_content(self, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")

        for tag in REMOVABLE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        for selector in ('[role="navigation"]', '[aria-hidden="true"]'):
            for element in soup.select(selector):
                element.decompose()

        root = soup.find("main") or soup.find("article") or soup.body or soup
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


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
