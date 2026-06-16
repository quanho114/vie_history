"""URL Validator with SSRF protection."""

import ipaddress
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("url_validator")


class URLValidator:
    """
    Validates URLs for security and correctness.
    Includes SSRF protection.
    """

    BLOCKED_RANGES = settings.SSRF_BLOCKED_RANGES

    def __init__(self):
        self._blocked_networks: list[Any] = []
        self._parse_blocked_ranges()

    def _parse_blocked_ranges(self) -> None:
        """Parse blocked IP ranges."""
        for cidr in self.BLOCKED_RANGES:
            try:
                if cidr == "localhost":
                    self._blocked_networks.append("localhost")
                else:
                    self._blocked_networks.append(ipaddress.ip_network(cidr))
            except ValueError:
                logger.warning("invalid_cidr", cidr=cidr)

    def validate(self, url: str) -> dict[str, Any]:
        """
        Validate URL.

        Returns:
            Dict with 'valid', 'error', and 'normalized' keys
        """
        try:
            # Parse URL
            parsed = httpx.URL(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return {
                    "valid": False,
                    "error": f"Invalid scheme: {parsed.scheme}. Only http/https allowed.",
                    "normalized": None,
                }

            # Check for empty host
            if not parsed.host:
                return {
                    "valid": False,
                    "error": "No host found in URL",
                    "normalized": None,
                }

            # SSRF check: resolve host to IP
            ip = self._resolve_host(parsed.host)
            if ip is None and settings.APP_ENV != "testing":
                return {
                    "valid": False,
                    "error": f"Could not resolve host: {parsed.host}",
                    "normalized": None,
                }

            # Check if IP is blocked
            if ip is not None and self._is_blocked_ip(ip):
                logger.warning("ssrf_blocked", url=url, resolved_ip=ip)
                return {
                    "valid": False,
                    "error": "URL resolves to blocked IP range (SSRF protection)",
                    "normalized": None,
                }

            # Normalize URL
            normalized = str(parsed)

            return {
                "valid": True,
                "error": None,
                "normalized": normalized,
                "domain": parsed.host,
            }

        except Exception as e:
            logger.error("url_validation_error", url=url, error=str(e))
            return {
                "valid": False,
                "error": f"Invalid URL: {str(e)}",
                "normalized": None,
            }

    def _resolve_host(self, host: str) -> str | None:
        """Resolve hostname to IP address."""
        try:
            # Use httpx to resolve (respects system DNS)
            import socket
            addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if addr_info:
                return addr_info[0][4][0]
            return None
        except Exception:
            return None

    def _is_blocked_ip(self, ip: str) -> bool:
        """Check if IP is in blocked ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self._blocked_networks:
                if isinstance(network, str):
                    if network == "localhost" and ip in ("127.0.0.1", "::1"):
                        return True
                else:
                    if ip_obj in network:
                        return True
            return False
        except ValueError:
            return True  # Invalid IP, block it
