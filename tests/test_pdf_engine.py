"""Tests for PDF engine enhancements."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pdf_engine import (
    PlaywrightPDFEngine,
    create_page_footer_template,
    create_page_header_template,
    render_resume_to_pdf,
)


class TestPlaywrightPDFEngine:
    """Test PlaywrightPDFEngine functionality."""

    @pytest.fixture
    def mock_browser(self):
        """Mock browser for testing."""
        with patch("app.services.pdf_engine._browser", None):
            yield

    @pytest.mark.asyncio
    async def test_generate_pdf_with_header_footer(self, mock_browser):
        """Test PDF generation with header and footer templates."""
        engine = PlaywrightPDFEngine()

        mock_page = AsyncMock()
        mock_browser_obj = AsyncMock()
        mock_browser_obj.new_page = AsyncMock(return_value=mock_page)

        with patch.object(engine, "_get_browser", return_value=mock_browser_obj):
            result = await engine.generate_pdf(
                html_content="<html><body>Test</body></html>",
                output_path="/tmp/test.pdf",
                header_template="<span>Header {pageNumber}</span>",
                footer_template="<span>Page {pageNumber} of {total}</span>",
            )

        assert result == "/tmp/test.pdf"

    @pytest.mark.asyncio
    async def test_generate_pdf_with_custom_format(self, mock_browser):
        """Test PDF generation with custom paper format."""
        engine = PlaywrightPDFEngine()

        mock_page = AsyncMock()
        mock_browser_obj = AsyncMock()
        mock_browser_obj.new_page = AsyncMock(return_value=mock_page)

        with patch.object(engine, "_get_browser", return_value=mock_browser_obj):
            result = await engine.generate_pdf(
                html_content="<html><body>Test</body></html>",
                output_path="/tmp/test.pdf",
                format="Letter",
                scale=0.8,
            )

        assert result == "/tmp/test.pdf"

    @pytest.mark.asyncio
    async def test_generate_pdf_without_background(self, mock_browser):
        """Test PDF generation without background graphics."""
        engine = PlaywrightPDFEngine()

        mock_page = AsyncMock()
        mock_browser_obj = AsyncMock()
        mock_browser_obj.new_page = AsyncMock(return_value=mock_page)

        with patch.object(engine, "_get_browser", return_value=mock_browser_obj):
            result = await engine.generate_pdf(
                html_content="<html><body>Test</body></html>",
                output_path="/tmp/test.pdf",
                print_background=False,
            )

        assert result == "/tmp/test.pdf"


class TestPDFHelperFunctions:
    """Test PDF helper functions."""

    def test_create_page_header_template_default(self):
        """Test default header template creation."""
        template = create_page_header_template()

        assert "font-family" in template
        assert "{pageNumber}" in template

    def test_create_page_header_template_with_title(self):
        """Test header template with custom title."""
        template = create_page_header_template(title="My Resume")

        assert "My Resume" in template
        assert "{pageNumber}" in template

    def test_create_page_header_template_custom_style(self):
        """Test header template with custom styling."""
        template = create_page_header_template(
            font_family="Helvetica",
            font_size="12px",
        )

        assert "Helvetica" in template
        assert "12px" in template

    def test_create_page_footer_template_default(self):
        """Test default footer template creation."""
        template = create_page_footer_template()

        assert "font-family" in template
        assert "{pageNumber}" in template
        assert "{total}" in template

    def test_create_page_footer_template_alignment(self):
        """Test footer template with different alignments."""
        for align in ["left", "center", "right"]:
            template = create_page_footer_template(align=align)
            assert f"text-align: {align}" in template


class TestRenderResumeToPDF:
    """Test render_resume_to_pdf convenience function."""

    @pytest.mark.asyncio
    async def test_render_with_all_options(self, tmp_path):
        """Test rendering with all options."""
        with patch("app.services.pdf_engine.PlaywrightPDFEngine") as MockEngine:
            mock_instance = AsyncMock()
            mock_instance.generate_pdf = AsyncMock(
                return_value=str(tmp_path / "test.pdf")
            )
            MockEngine.return_value = mock_instance

            result = await render_resume_to_pdf(
                html_template="<html>Test</html>",
                output_dir=str(tmp_path),
                filename="test",
                margins={"top": 15, "bottom": 15},
                format="A4",
                header_template="<span>Header</span>",
                footer_template="<span>Footer</span>",
                print_background=False,
            )

        assert result == str(tmp_path / "test.pdf")
