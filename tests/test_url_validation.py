"""Tests for URL validation."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.tool_definitions import validate_url


class TestUrlValidation:
    """Test URL validation function."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs pass validation."""
        is_valid, result = validate_url("https://example.com")
        assert is_valid is True
        assert result == "https://example.com"

    def test_valid_http_url(self):
        """Test that valid HTTP URLs pass validation."""
        is_valid, result = validate_url("http://example.com")
        assert is_valid is True
        assert result == "http://example.com"

    def test_url_without_scheme_adds_https(self):
        """Test that URLs without scheme get HTTPS added."""
        is_valid, result = validate_url("example.com")
        assert is_valid is True
        assert result == "https://example.com"

    def test_url_with_path(self):
        """Test that URLs with paths are valid."""
        is_valid, result = validate_url("https://example.com/path/to/page")
        assert is_valid is True
        assert result == "https://example.com/path/to/page"

    def test_empty_url_rejected(self):
        """Test that empty URLs are rejected."""
        is_valid, result = validate_url("")
        assert is_valid is False
        assert "non-empty string" in result.lower()

    def test_none_url_rejected(self):
        """Test that None URLs are rejected."""
        is_valid, result = validate_url(None)
        assert is_valid is False

    def test_invalid_domain_rejected(self):
        """Test that invalid domains are rejected."""
        is_valid, result = validate_url("https://nodot")
        assert is_valid is False
        assert "invalid domain" in result.lower()

    def test_localhost_allowed(self):
        """Test that localhost is allowed."""
        is_valid, result = validate_url("http://localhost:8080")
        assert is_valid is True

    def test_url_with_query_params(self):
        """Test that URLs with query parameters are valid."""
        is_valid, result = validate_url("https://example.com/search?q=test&page=1")
        assert is_valid is True

    def test_subdomain_url(self):
        """Test that URLs with subdomains are valid."""
        is_valid, result = validate_url("https://api.example.com/v1")
        assert is_valid is True
