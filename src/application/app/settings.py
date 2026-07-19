"""Runtime settings."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os


@dataclass(frozen=True)
class AppSettings:
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    bedrock_model_id: str = field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"
        )
    )
    http_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    )
    max_response_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_RESPONSE_BYTES", "2000000"))
    )
    max_content_characters: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONTENT_CHARACTERS", "50000"))
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    enable_javascript_fallback: bool = field(
        default_factory=lambda: os.getenv("ENABLE_JAVASCRIPT_FALLBACK", "true").lower()
        in {"1", "true", "yes"}
    )
    playwright_navigation_timeout_seconds: int = field(
        default_factory=lambda: int(
            os.getenv(
                "PLAYWRIGHT_NAVIGATION_TIMEOUT_SECONDS",
                os.getenv("HTTP_TIMEOUT_SECONDS", "10"),
            )
        )
    )
    playwright_wait_until: str = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_WAIT_UNTIL", "networkidle")
    )
    playwright_browser_executable_path: str | None = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_BROWSER_EXECUTABLE_PATH") or None
    )
    user_agent: str = "LambdaWebSummarizer/1.0"
    max_redirects: int = 3
    bedrock_max_tokens: int = 600
    bedrock_temperature: float = 0.2
    test_mode: bool = field(
        default_factory=lambda: os.getenv("APP_TEST_MODE", "0").lower() in {"1", "true", "yes"}
    )
    test_summary: str = field(
        default_factory=lambda: os.getenv(
            "APP_TEST_SUMMARY", "Resumo gerado em modo de teste controlado."
        )
    )
    test_page_title: str = field(
        default_factory=lambda: os.getenv("APP_TEST_PAGE_TITLE", "Example Domain")
    )
    test_page_content: str = field(
        default_factory=lambda: os.getenv(
            "APP_TEST_PAGE_CONTENT",
            (
                "Example Domain is for use in illustrative examples in documents. "
                "This page helps validate the scraping and summarization flow."
            ),
        )
    )


def configure_logging(level_name: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
