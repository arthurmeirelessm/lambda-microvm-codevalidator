"""AWS Lambda handler."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
from time import monotonic
from typing import Any, Protocol

try:
    from .bedrock_service import BedrockSummarizer
    from .exceptions import (
        BedrockInvocationError,
        EmptyContentError,
        InvalidRequestError,
        InvalidUrlError,
        ScrapingError,
        UnsafeUrlError,
        UnsupportedContentTypeError,
    )
    from .scraper import ScrapedPage, WebScraper
    from .settings import AppSettings, configure_logging
    from .validators import extract_url_from_event, sanitize_url_for_logging, validate_url
except ImportError:  # pragma: no cover - flat package build fallback
    from bedrock_service import BedrockSummarizer
    from exceptions import (
        BedrockInvocationError,
        EmptyContentError,
        InvalidRequestError,
        InvalidUrlError,
        ScrapingError,
        UnsafeUrlError,
        UnsupportedContentTypeError,
    )
    from scraper import ScrapedPage, WebScraper
    from settings import AppSettings, configure_logging
    from validators import extract_url_from_event, sanitize_url_for_logging, validate_url

logger = logging.getLogger(__name__)


class ScraperProtocol(Protocol):
    def scrape(self, url: str) -> ScrapedPage: ...


class SummarizerProtocol(Protocol):
    def summarize(self, source_url: str, title: str, content: str) -> str: ...


class TestModeScraper:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def scrape(self, url: str) -> ScrapedPage:
        content = self.settings.test_page_content[: self.settings.max_content_characters]
        return ScrapedPage(
            url=url,
            title=self.settings.test_page_title,
            content=content,
            content_length=len(content),
            status_code=200,
        )


class TestModeSummarizer:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def summarize(self, source_url: str, title: str, content: str) -> str:
        return self.settings.test_summary


def lambda_handler(
    event: dict[str, Any],
    context: Any,
    scraper: ScraperProtocol | None = None,
    summarizer: SummarizerProtocol | None = None,
    settings: AppSettings | None = None,
) -> dict[str, Any]:
    settings = settings or AppSettings()
    configure_logging(settings.log_level)
    started_at = monotonic()

    try:
        logger.info("Lambda execution started")
        url = extract_url_from_event(event)
        sanitized_url = sanitize_url_for_logging(url)
        logger.info("Target URL accepted for processing: %s", sanitized_url)

        validate_url(url)
        logger.info("URL validation passed: %s", sanitized_url)

        scraper = scraper or _build_scraper(settings)
        summarizer = summarizer or _build_summarizer(settings)

        scrape_started = monotonic()
        page = scraper.scrape(url)
        scrape_elapsed = monotonic() - scrape_started
        logger.info(
            "Scraping completed: url=%s status=%s chars=%s durationSeconds=%.3f",
            sanitized_url,
            page.status_code,
            page.content_length,
            scrape_elapsed,
        )

        bedrock_started = monotonic()
        summary = summarizer.summarize(
            source_url=page.url,
            title=page.title,
            content=page.content,
        )
        bedrock_elapsed = monotonic() - bedrock_started
        logger.info(
            "Bedrock completed: url=%s durationSeconds=%.3f",
            sanitized_url,
            bedrock_elapsed,
        )

        return _response(
            200,
            {
                "url": page.url,
                "title": page.title,
                "summary": summary,
                "contentLength": page.content_length,
            },
        )
    except InvalidRequestError as exc:
        _log_error("Invalid request", exc, settings)
        return _response(400, {"error": "INVALID_REQUEST", "message": str(exc)})
    except (InvalidUrlError, UnsafeUrlError) as exc:
        _log_error("Invalid or unsafe URL", exc, settings)
        return _response(400, {"error": "INVALID_URL", "message": str(exc)})
    except (ScrapingError, UnsupportedContentTypeError, EmptyContentError) as exc:
        _log_error("Scraping failed", exc, settings)
        return _response(422, {"error": "SCRAPING_FAILED", "message": str(exc)})
    except BedrockInvocationError as exc:
        _log_error("Bedrock invocation failed", exc, settings)
        return _response(500, {"error": "INTERNAL_ERROR", "message": str(exc)})
    except Exception as exc:  # pragma: no cover
        _log_error("Unhandled internal error", exc, settings)
        return _response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Não foi possível processar o conteúdo.",
            },
        )
    finally:
        logger.info("Lambda execution finished in %.3f seconds", monotonic() - started_at)


def _build_scraper(settings: AppSettings) -> ScraperProtocol:
    if settings.test_mode:
        return TestModeScraper(settings)
    return WebScraper(settings)


def _build_summarizer(settings: AppSettings) -> SummarizerProtocol:
    if settings.test_mode:
        return TestModeSummarizer(settings)
    return BedrockSummarizer(settings)


def _log_error(message: str, exc: Exception, settings: AppSettings) -> None:
    if settings.log_level == "DEBUG":
        logger.exception(message)
    else:
        logger.error("%s: %s", message, exc)


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _run_local() -> int:
    event_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "events" / "success.json"
    )
    event = json.loads(event_path.read_text(encoding="utf-8"))
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_local())
