"""Input validation and SSRF protection."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

try:
    from .exceptions import InvalidRequestError, InvalidUrlError, UnsafeUrlError
except ImportError:  # pragma: no cover - flat package build fallback
    from exceptions import InvalidRequestError, InvalidUrlError, UnsafeUrlError

Resolver = Callable[..., Any]
HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}\.)*[A-Za-z0-9-]{1,63}\.?$"
)
BLOCKED_HOSTNAMES = {"localhost"}
BLOCKED_SUFFIXES = (".internal", ".local", ".localhost")
BLOCKED_IPS = {"0.0.0.0", "169.254.169.254"}


def extract_url_from_event(event: dict[str, Any]) -> str:
    if not isinstance(event, dict):
        raise InvalidRequestError("O evento recebido é inválido.")

    payload: dict[str, Any]
    if "body" in event and event.get("body") is not None:
        body = event["body"]
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise InvalidRequestError("O body do API Gateway é inválido.") from exc
        elif isinstance(body, dict):
            payload = body
        else:
            raise InvalidRequestError("O body do API Gateway é inválido.")
    else:
        payload = event

    url = payload.get("url")
    if not isinstance(url, str) or not url.strip():
        raise InvalidRequestError("A URL informada é obrigatória.")
    return url.strip()


def sanitize_url_for_logging(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def validate_url(url: str, resolver: Resolver = socket.getaddrinfo) -> SplitResult:
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as exc:
        raise InvalidUrlError("A URL informada é inválida.") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise InvalidUrlError("A URL informada é inválida.")
    if not parsed.hostname:
        raise InvalidUrlError("A URL informada é inválida.")

    hostname = parsed.hostname.lower().rstrip(".")
    if _is_blocked_hostname(hostname):
        raise UnsafeUrlError("A URL informada não é segura.")
    if not _is_valid_hostname(hostname):
        raise InvalidUrlError("A URL informada é inválida.")

    for address in resolve_public_addresses(hostname, resolver=resolver):
        if not _is_safe_ip(address):
            raise UnsafeUrlError("A URL informada não é segura.")

    return parsed


def resolve_public_addresses(
    hostname: str, resolver: Resolver = socket.getaddrinfo
) -> list[str]:
    literal = _parse_ip(hostname)
    if literal is not None:
        return [str(literal)]

    try:
        infos = resolver(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidUrlError("A URL informada é inválida.") from exc

    addresses: list[str] = []
    for info in infos:
        candidate = info[4][0]
        ip_obj = _parse_ip(candidate)
        if ip_obj is None:
            continue
        value = str(ip_obj)
        if value not in addresses:
            addresses.append(value)
    if not addresses:
        raise InvalidUrlError("A URL informada é inválida.")
    return addresses


def _is_valid_hostname(hostname: str) -> bool:
    if not hostname:
        return False
    if _parse_ip(hostname) is not None:
        return True
    if "." not in hostname:
        return False
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    return bool(HOSTNAME_RE.fullmatch(ascii_hostname))


def _is_blocked_hostname(hostname: str) -> bool:
    return hostname in BLOCKED_HOSTNAMES or hostname.endswith(BLOCKED_SUFFIXES)


def _parse_ip(value: str):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _is_safe_ip(value: str) -> bool:
    if value in BLOCKED_IPS:
        return False
    ip_obj = ipaddress.ip_address(value)
    return not any(
        (
            ip_obj.is_private,
            ip_obj.is_loopback,
            ip_obj.is_link_local,
            ip_obj.is_multicast,
            ip_obj.is_reserved,
            ip_obj.is_unspecified,
        )
    )
