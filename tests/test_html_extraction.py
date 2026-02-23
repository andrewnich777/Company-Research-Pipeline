"""Tests for HTML text extraction."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.tool_definitions import extract_text_from_html


class TestHtmlExtraction:
    """Test HTML text extraction function."""

    def test_basic_html_extraction(self):
        """Test extracting text from basic HTML."""
        html = "<html><body><p>Hello World</p></body></html>"
        result = extract_text_from_html(html)
        assert "Hello World" in result

    def test_script_tag_removal(self):
        """Test that script tags are removed."""
        html = """
        <html>
        <body>
            <script>alert('bad');</script>
            <p>Content</p>
        </body>
        </html>
        """
        result = extract_text_from_html(html)
        assert "alert" not in result
        assert "Content" in result

    def test_style_tag_removal(self):
        """Test that style tags are removed."""
        html = """
        <html>
        <head><style>.class { color: red; }</style></head>
        <body><p>Content</p></body>
        </html>
        """
        result = extract_text_from_html(html)
        assert "color" not in result
        assert "Content" in result

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        html = "<p>Hello     World</p><p>Another    Paragraph</p>"
        result = extract_text_from_html(html)
        # Should not have multiple consecutive spaces
        assert "     " not in result
        assert "Hello" in result

    def test_max_length_truncation(self):
        """Test that content is truncated at max length."""
        html = "<p>" + "x" * 20000 + "</p>"
        result = extract_text_from_html(html, max_length=1000)
        assert len(result) <= 1020  # 1000 + "[truncated]" marker
        assert "[truncated]" in result

    def test_empty_html(self):
        """Test handling empty HTML."""
        result = extract_text_from_html("")
        assert result == ""

    def test_nested_tags(self):
        """Test extraction from nested tags."""
        html = """
        <div>
            <div>
                <p>Nested <strong>content</strong></p>
            </div>
        </div>
        """
        result = extract_text_from_html(html)
        assert "Nested" in result
        assert "content" in result

    def test_html_entities(self):
        """Test that HTML entities are handled."""
        html = "<p>Test &amp; Demo</p>"
        result = extract_text_from_html(html)
        # BeautifulSoup should decode entities
        assert "Test" in result
        assert "Demo" in result
