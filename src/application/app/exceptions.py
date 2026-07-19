"""Application-specific exceptions."""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class InvalidRequestError(AppError):
    """Raised when the Lambda event payload is invalid."""


class InvalidUrlError(AppError):
    """Raised when the provided URL is malformed."""


class UnsafeUrlError(AppError):
    """Raised when the provided URL targets an unsafe destination."""


class ScrapingError(AppError):
    """Raised when the target page cannot be scraped."""


class UnsupportedContentTypeError(ScrapingError):
    """Raised when the response is not HTML."""


class EmptyContentError(ScrapingError):
    """Raised when no meaningful content is extracted."""


class BedrockInvocationError(AppError):
    """Raised when Amazon Bedrock cannot process the request."""
