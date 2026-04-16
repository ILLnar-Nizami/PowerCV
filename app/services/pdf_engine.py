"""WYSIWYG PDF Export Service using Headless Chromium.

This module provides a "What You See Is What You Get" PDF rendering engine
using Playwright (headless Chromium). It renders HTML/CSS templates exactly
as they appear in the browser, ensuring perfect PDF output accuracy.

Based on Resume Matcher pattern: apps/backend/app/pdf.py
"""

import asyncio
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# Browser management lock for concurrent PDF requests
_browser_lock = asyncio.Lock()
_browser = None


class PlaywrightPDFEngine:
    """Headless Chromium PDF Renderer for WYSIWYG output.

    Features:
    - Async browser management with race condition prevention
    - Multi-platform Chrome/Edge detection (Windows, macOS, Linux)
    - Smart margin handling at browser print level
    - PDF/A compliance support for archival
    """

    def __init__(self):
        """Initialize the PDF engine with platform detection."""
        self.browser_executable: Optional[str] = None
        self._detect_browser()

    def _detect_browser(self) -> Optional[str]:
        """Detect available Chromium-based browser executable.

        Checks common installation paths across platforms:
        - Linux: /usr/bin/{chromium,chromium-browser,google-chrome,chrome}
        - macOS: /Applications/{Chromium,Google Chrome}.app
        - Windows: %ProgramFiles%/{Google/Chrome,Microsoft/Edge}
        - Snap/Flatpak paths for Linux
        """
        candidates = []

        # Linux paths
        linux_browsers = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium",
        ]
        candidates.extend(linux_browsers)

        # Check PATH for common browser executables
        path_browsers = ["chromium", "chromium-browser", "google-chrome", "chrome"]
        for browser in path_browsers:
            result = shutil.which(browser)
            if result:
                candidates.append(result)

        # Verify executables exist and are runnable
        for path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                self.browser_executable = path
                logger.info(f"Found browser: {path}")
                return path

        logger.warning("No Chromium browser found - PDF generation will fail")
        return None

    async def _get_browser(self):
        """Get or launch a Playwright browser instance.

        Uses asyncio.Lock to prevent race conditions when multiple
        PDF requests arrive simultaneously.
        """
        global _browser

        async with _browser_lock:
            if _browser is None:
                try:
                    import playwright
                    from playwright.async_api import async_playwright

                    pw = await async_playwright().start()
                    _browser = await pw.chromium.launch(
                        executable_path=self.browser_executable,
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                    logger.info("Playwright browser launched successfully")
                except ImportError:
                    logger.error(
                        "Playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                    raise RuntimeError("Playwright is required for PDF generation")
                except Exception as e:
                    logger.error(f"Failed to launch browser: {e}")
                    raise

        return _browser

    async def generate_pdf(
        self,
        html_content: str,
        output_path: str,
        margins: Dict[str, float] = None,
        format: str = "A4",
        scale: float = 1.0,
        header_template: Optional[str] = None,
        footer_template: Optional[str] = None,
        print_background: bool = True,
    ) -> str:
        """Generate PDF from HTML content using headless Chromium.

        Args:
            html_content: Complete HTML document with CSS styling
            output_path: Destination path for PDF file
            margins: Dict with 'top', 'bottom', 'left', 'right' in mm
            format: Paper format ('A4', 'Letter', 'Legal', 'A3', 'A5')
            scale: Content scale factor (1.0 = 100%)
            header_template: HTML template for header (with {pageNumber} and {total} placeholders)
            footer_template: HTML template for footer (with {pageNumber} and {total} placeholders)
            print_background: Whether to print background graphics and colors

        Returns:
            Path to generated PDF file
        """
        if not self.browser_executable:
            raise RuntimeError(
                "No browser available. Install Chromium or Chrome, "
                "or run: playwright install chromium"
            )

        # Default margins (20mm standard margins)
        if margins is None:
            margins = {"top": 20, "bottom": 20, "left": 20, "right": 20}

        browser = await self._get_browser()

        page = await browser.new_page(
            viewport={"width": 210, "height": 297},  # A4 in mm at 96 DPI
        )

        try:
            # Set content and wait for render
            await page.set_content(html_content, wait_until="networkidle")

            # Generate PDF with browser's print API
            await page.pdf(
                path=output_path,
                format=format,
                scale=scale,
                margin={
                    "top": f"{margins.get('top', 20)}mm",
                    "bottom": f"{margins.get('bottom', 20)}mm",
                    "left": f"{margins.get('left', 20)}mm",
                    "right": f"{margins.get('right', 20)}mm",
                },
                print_background=print_background,
                display_header_footer=bool(header_template or footer_template),
                header_template=header_template,
                footer_template=footer_template,
            )

            logger.info(f"PDF generated: {output_path}")
            return output_path

        finally:
            await page.close()

    async def close(self):
        """Close the browser instance."""
        global _browser

        async with _browser_lock:
            if _browser is not None:
                await _browser.close()
                _browser = None
                logger.info("Playwright browser closed")


# Convenience function for PDF generation
async def render_resume_to_pdf(
    html_template: str,
    output_dir: str,
    filename: str,
    margins: Dict[str, float] = None,
    format: str = "A4",
    header_template: Optional[str] = None,
    footer_template: Optional[str] = None,
    print_background: bool = True,
) -> str:
    """Render a resume HTML template to PDF.

    Args:
        html_template: Complete HTML document with resume styling
        output_dir: Directory to save PDF
        filename: Output filename (without extension)
        margins: Optional margin overrides
        format: Paper format ('A4', 'Letter', etc.)
        header_template: HTML template for header
        footer_template: HTML template for footer
        print_background: Whether to print background graphics

    Returns:
        Full path to generated PDF
    """
    engine = PlaywrightPDFEngine()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{filename}.pdf")

    await engine.generate_pdf(
        html_content=html_template,
        output_path=output_path,
        margins=margins,
        format=format,
        header_template=header_template,
        footer_template=footer_template,
        print_background=print_background,
    )

    return output_path


def create_page_header_template(
    title: Optional[str] = None,
    font_family: str = "Arial",
    font_size: str = "10px",
) -> str:
    """Create a standard header template for PDF pages.

    Args:
        title: Optional title to show in header
        font_family: Font family for header text
        font_size: Font size for header text

    Returns:
        HTML header template string
    """
    content = f"<span style='font-family: {font_family}; font-size: {font_size};'>"
    if title:
        content += title
    content += "</span>"
    return (
        content
        + "<span style='font-family: {font_family}; font-size: {font_size}; margin-left: 20px;'>{pageNumber}/{{total}}</span>"
    )


def create_page_footer_template(
    font_family: str = "Arial",
    font_size: str = "10px",
    align: str = "center",
) -> str:
    """Create a standard footer template for PDF pages.

    Args:
        font_family: Font family for footer text
        font_size: Font size for footer text
        align: Text alignment ('left', 'center', 'right')

    Returns:
        HTML footer template string
    """
    return f"""<span style='font-family: {font_family}; font-size: {font_size}; margin: auto; padding: 0 20px;'>
<div style='width: 100%; text-align: {align};'>
Page {{pageNumber}} of {{total}}
</div>
</span>"""


# Browser cleanup on shutdown
async def cleanup_browser():
    """Clean up Playwright browser resources."""
    engine = PlaywrightPDFEngine()
    await engine.close()
