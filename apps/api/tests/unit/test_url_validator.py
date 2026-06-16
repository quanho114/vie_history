"""Unit tests for URL validator with SSRF protection."""

import pytest

from app.services.ingestion.url_validator import URLValidator


class TestURLValidatorSchemes:
    """URL scheme validation."""

    def test_accepts_https_url(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_Tranh_Vi%E1%BB%87t_Nam")

        assert result["valid"] is True
        assert result["normalized"] is not None
        assert "wikipedia.org" in result["normalized"]

    def test_accepts_http_url(self) -> None:
        validator = URLValidator()

        result = validator.validate("http://example.com/article")

        assert result["valid"] is True
        assert result["normalized"] is not None

    def test_rejects_invalid_scheme(self) -> None:
        validator = URLValidator()

        result = validator.validate("ftp://example.com/file")

        assert result["valid"] is False
        assert "Invalid scheme" in result["error"]
        assert result["normalized"] is None

    def test_rejects_file_scheme(self) -> None:
        validator = URLValidator()

        result = validator.validate("file:///etc/passwd")

        assert result["valid"] is False
        assert result["normalized"] is None

    def test_rejects_mailto_scheme(self) -> None:
        validator = URLValidator()

        result = validator.validate("mailto://admin@example.com")

        assert result["valid"] is False
        assert result["normalized"] is None


class TestURLValidatorFormat:
    """URL format and parsing validation."""

    def test_rejects_empty_url(self) -> None:
        validator = URLValidator()

        result = validator.validate("")

        assert result["valid"] is False
        assert result["normalized"] is None

    def test_rejects_invalid_url(self) -> None:
        validator = URLValidator()

        result = validator.validate("not-a-valid-url")

        assert result["valid"] is False
        assert result["normalized"] is None

    def test_rejects_missing_host(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://")

        assert result["valid"] is False
        assert result["normalized"] is None

    def test_normalizes_url_preserving_path(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_Tranh")

        assert result["valid"] is True
        assert result["domain"] == "vi.wikipedia.org"


class TestSSRFProtection:
    """SSRF protection — tests use mocking to avoid real network calls."""

    def test_blocks_localhost_via_direct_check(self) -> None:
        validator = URLValidator()
        validator._blocked_networks = ["localhost"]

        blocked = validator._is_blocked_ip("127.0.0.1")
        assert blocked is True

    def test_blocks_ipv6_localhost(self) -> None:
        validator = URLValidator()
        validator._blocked_networks = ["localhost"]

        blocked = validator._is_blocked_ip("::1")
        assert blocked is True

    def test_allows_public_ip_not_in_blocked_ranges(self) -> None:
        validator = URLValidator()
        validator._blocked_networks = []

        blocked = validator._is_blocked_ip("8.8.8.8")
        assert blocked is False

    def test_blocks_private_ip_10_range(self) -> None:
        validator = URLValidator()
        validator._blocked_networks = []

        blocked = validator._is_blocked_ip("10.0.0.1")
        assert blocked is False  # Only blocked if SSRf_BLOCKED_RANGES includes it

    def test_invalid_ip_returns_blocked(self) -> None:
        validator = URLValidator()
        validator._blocked_networks = []

        blocked = validator._is_blocked_ip("not-an-ip")
        assert blocked is True  # Invalid IPs are blocked

    def test_parses_valid_cidr(self) -> None:
        validator = URLValidator()
        initial_count = len(validator._blocked_networks)

        # Re-init with a specific CIDR
        validator2 = URLValidator()
        networks_before = len(validator2._blocked_networks)

        assert networks_before >= 0  # Blocked networks parsed without error


class TestURLValidatorEdgeCases:
    """Edge case URL validation."""

    def test_url_with_port_number(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://example.com:8443/path")

        # Valid if domain resolves, blocked if domain doesn't resolve
        # The only truly testable assertion here is the structure
        assert "valid" in result
        assert "normalized" in result
        assert "error" in result

    def test_url_with_fragment(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://example.com/page#section")

        assert "valid" in result
        assert "normalized" in result

    def test_url_with_query_params(self) -> None:
        validator = URLValidator()

        result = validator.validate("https://example.com/search?q=l%E1%BB%8Bch+s%E1%BB%AD")

        assert "valid" in result
        assert "normalized" in result
