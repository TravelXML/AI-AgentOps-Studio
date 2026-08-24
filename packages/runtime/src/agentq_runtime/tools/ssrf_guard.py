"""Blocks the generic HTTP tools from reaching localhost/loopback/link-local/cloud-metadata
addresses (spec section 60), since a workflow author (or a prompt-injected agent) could otherwise
turn the HTTP tool into an internal network scanner or credential-metadata reader.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from agentq_runtime.tools.registry import ToolExecutionError

_BLOCKED_HOSTNAMES = {"metadata.google.internal", "metadata.internal"}


def assert_safe_url(url: str, *, allowed_hosts: set[str] | None = None) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ToolExecutionError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise ToolExecutionError("URL has no hostname.")

    if allowed_hosts and host in allowed_hosts:
        return

    if host.lower() in _BLOCKED_HOSTNAMES:
        raise ToolExecutionError(f"Blocked host for SSRF protection: {host}")

    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ToolExecutionError(f"Could not resolve host: {host}") from exc

    for _family, _type, _proto, _canon, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_private
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ToolExecutionError(f"Blocked address for SSRF protection: {host} resolves to {ip_str}")
