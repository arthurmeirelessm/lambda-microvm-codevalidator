import socket

import pytest

from app.exceptions import InvalidRequestError, InvalidUrlError, UnsafeUrlError
from app.validators import extract_url_from_event, sanitize_url_for_logging, validate_url


def public_resolver(hostname: str, *_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 0))]


def test_extract_url_direct_event() -> None:
    assert extract_url_from_event({'url': 'https://example.com/article'}) == 'https://example.com/article'


def test_extract_url_missing_url() -> None:
    with pytest.raises(InvalidRequestError):
        extract_url_from_event({})


def test_extract_url_api_gateway_body() -> None:
    event = {'body': '{"url": "https://example.com/article"}'}
    assert extract_url_from_event(event) == 'https://example.com/article'


def test_extract_url_invalid_api_gateway_body() -> None:
    with pytest.raises(InvalidRequestError):
        extract_url_from_event({'body': '{invalid json}'})


def test_validate_url_accepts_valid_public_url() -> None:
    parsed = validate_url('https://example.com/article', resolver=public_resolver)
    assert parsed.hostname == 'example.com'


def test_validate_url_rejects_invalid_scheme() -> None:
    with pytest.raises(InvalidUrlError):
        validate_url('ftp://example.com/resource', resolver=public_resolver)


def test_validate_url_rejects_localhost() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url('http://localhost/admin', resolver=public_resolver)


def test_validate_url_rejects_private_address() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url('http://192.168.1.10/secret', resolver=public_resolver)


def test_validate_url_rejects_aws_metadata_address() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url('http://169.254.169.254/latest/meta-data', resolver=public_resolver)


def test_validate_url_rejects_invalid_hostname() -> None:
    with pytest.raises(InvalidUrlError):
        validate_url('https://bad_host^name/path', resolver=public_resolver)


def test_sanitize_url_for_logging_removes_query_string() -> None:
    assert sanitize_url_for_logging('https://example.com/path?token=secret#fragment') == 'https://example.com/path'
