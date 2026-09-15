"""Constrained acquisition of a supplied source URL (no private-infrastructure reach, bounded size/time/redirects)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from django.conf import settings


class AcquisitionRefused(RuntimeError):
    """The URL was refused safely; the source gap is preserved, not filled."""


def _resolve_public(host: str) -> list:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise AcquisitionRefused(f"host could not be resolved: {host}") from exc
    addresses = []
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (address.is_private or address.is_loopback or address.is_link_local or address.is_multicast
                or address.is_reserved or address.is_unspecified or getattr(address, "is_site_local", False)):
            raise AcquisitionRefused("URL resolves to a private or internal address and was refused")
        addresses.append(str(address))
    return addresses


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise AcquisitionRefused("only http(s) URLs are accepted")
    if not parsed.hostname:
        raise AcquisitionRefused("URL has no host")
    if parsed.username or parsed.password:
        raise AcquisitionRefused("URLs with embedded credentials are refused")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if not ip.is_global:
            raise AcquisitionRefused("literal IP addresses outside the public range are refused")
    except ValueError:
        pass
    _resolve_public(parsed.hostname)


def fetch(url: str) -> tuple:
    """Return (final_url, content_type, bytes). Each redirect hop is re-validated."""
    max_bytes = settings.PORTAL_URL_FETCH_MAX_BYTES
    timeout = settings.PORTAL_URL_FETCH_TIMEOUT_SECONDS
    current = url
    for _hop in range(settings.PORTAL_URL_FETCH_MAX_REDIRECTS + 1):
        _check_url(current)
        response = requests.get(current, stream=True, timeout=timeout, allow_redirects=False,
                                headers={"User-Agent": "SR-Research-Library-portal/1.0 (source acquisition)"})
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                raise AcquisitionRefused("redirect without a Location header")
            current = requests.compat.urljoin(current, location)
            response.close()
            continue
        if response.status_code >= 400:
            raise AcquisitionRefused(f"source returned HTTP {response.status_code}")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > max_bytes:
            raise AcquisitionRefused("source is larger than the acquisition limit")
        chunks, total = [], 0
        for chunk in response.iter_content(chunk_size=1 << 16):
            total += len(chunk)
            if total > max_bytes:
                response.close()
                raise AcquisitionRefused("source exceeded the acquisition limit while downloading")
            chunks.append(chunk)
        return current, response.headers.get("Content-Type", ""), b"".join(chunks)
    raise AcquisitionRefused("too many redirects")
