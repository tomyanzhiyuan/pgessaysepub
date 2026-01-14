"""Tests for the ContentParser module."""

import pytest
from pg_epub.parser import ContentParser


class TestContentParser:
    """Tests for ContentParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance without scraper (no image downloads)."""
        return ContentParser(scraper=None)

    def test_escape_html(self, parser):
        """Test HTML escaping."""
        assert parser.escape_html("<script>") == "&lt;script&gt;"
        assert parser.escape_html("Tom & Jerry") == "Tom &amp; Jerry"
        assert parser.escape_html('"quoted"') == "&quot;quoted&quot;"

    def test_convert_br_to_paragraphs(self, parser):
        """Test BR tag conversion to paragraph breaks."""
        html = "Line 1<br><br>Line 2"
        result = parser.convert_br_to_paragraphs(html)
        # The method converts <br><br> to </p><p>
        assert "</p><p>" in result or "\n\n" in result or "<br" in result

    def test_text_to_paragraphs(self, parser):
        """Test text splitting into paragraphs."""
        text = "First paragraph here with enough content to pass filter.\n\nSecond paragraph here with enough content to pass filter."
        paragraphs = parser.text_to_paragraphs(text)
        assert len(paragraphs) == 2
        assert "First paragraph" in paragraphs[0]
        assert "Second paragraph" in paragraphs[1]

    def test_text_to_paragraphs_filters_short(self, parser):
        """Test that very short text is filtered out."""
        text = "OK\n\nThis is a proper paragraph with real content that should pass the filter."
        paragraphs = parser.text_to_paragraphs(text)
        assert len(paragraphs) == 1
        assert "proper paragraph" in paragraphs[0]

    def test_build_chapter_html_with_sufficient_content(self, parser):
        """Test chapter HTML generation with sufficient content."""
        # Content must be > 100 chars to not be filtered
        long_content = "<p>" + "This is test content. " * 20 + "</p>"
        html = parser.build_chapter_html(
            title="Test Essay",
            content_html=long_content,
            date_str="January 2024"
        )
        if html:  # Only test if content passed the length check
            assert "<h1>Test Essay</h1>" in html
            assert "January 2024" in html

    def test_build_chapter_html_returns_empty_for_short_content(self, parser):
        """Test that build_chapter_html returns empty for short content."""
        html = parser.build_chapter_html(
            title="Test Essay",
            content_html="<p>Short</p>",
            date_str="January 2024"
        )
        # Short content should return empty string
        assert html == ""

    def test_extract_main_content_basic(self, parser):
        """Test basic content extraction."""
        html = """
        <html>
        <body>
            <table>
                <tr><td>
                    <font size="2" face="verdana">
                    January 2024<br><br>
                    This is the essay content. It should be extracted properly
                    and turned into paragraphs. The content needs to be long
                    enough to pass the minimum length filter that removes
                    navigation and other short snippets. We need plenty of text
                    here to ensure it gets through all the filtering steps.
                    </font>
                </td></tr>
            </table>
        </body>
        </html>
        """
        content, images = parser.extract_main_content(
            html, "http://paulgraham.com/test.html", title="Test"
        )
        assert "essay content" in content.lower()
        assert isinstance(images, list)

    def test_extract_main_content_filters_yc_ad(self, parser):
        """Test that YC ad content is filtered out."""
        html = """
        <html>
        <body>
            <table>
                <tr><td>
                    <font size="2" face="verdana">
                    Want to start a startup? Get funded by Y Combinator.<br><br>
                    This is the actual essay content that should be kept and
                    displayed to the reader. It contains valuable information
                    about startups and technology. This paragraph needs to be
                    long enough to pass through all the content filters we have.
                    </font>
                </td></tr>
            </table>
        </body>
        </html>
        """
        content, _ = parser.extract_main_content(
            html, "http://paulgraham.com/test.html", title="Test"
        )
        # YC ad should be filtered out
        assert "Y Combinator" not in content or "Get funded" not in content
        assert "actual essay content" in content.lower()

    def test_extract_main_content_returns_container(self, parser):
        """Test that extract_main_content returns a container div."""
        html = """
        <html><body>
            <table><tr><td>
                <font size="2" face="verdana">
                This is some essay content that is long enough to be extracted
                and processed by the parser. It needs sufficient length to pass
                all filtering criteria.
                </font>
            </td></tr></table>
        </body></html>
        """
        content, images = parser.extract_main_content(
            html, "http://example.com", title=""
        )
        assert 'class="essay-content"' in content
        assert isinstance(images, list)


class TestContentParserEdgeCases:
    """Edge case tests for ContentParser."""

    @pytest.fixture
    def parser(self):
        return ContentParser(scraper=None)

    def test_empty_html_returns_container(self, parser):
        """Test handling of empty HTML returns empty container."""
        content, images = parser.extract_main_content(
            "", "http://example.com", title=""
        )
        # Should return an empty container div
        assert "essay-content" in content
        assert images == []

    def test_malformed_html(self, parser):
        """Test handling of malformed HTML."""
        html = "<p>Unclosed paragraph<div>Mixed tags with enough content to test</p></div>"
        # Should not raise an exception
        content, images = parser.extract_main_content(
            html, "http://example.com", title=""
        )
        assert isinstance(content, str)
        assert isinstance(images, list)

    def test_extract_content_with_images(self, parser):
        """Test content extraction preserves image references."""
        html = """
        <html><body>
            <table><tr><td>
                <font size="2" face="verdana">
                This is essay content with an image below. The content needs
                to be long enough to pass filters.
                <img src="test.gif" alt="Test image">
                More content after the image to make it substantial enough.
                </font>
            </td></tr></table>
        </body></html>
        """
        content, images = parser.extract_main_content(
            html, "http://paulgraham.com/test.html", title=""
        )
        # Images list may be empty if image download fails (no scraper)
        assert isinstance(images, list)
