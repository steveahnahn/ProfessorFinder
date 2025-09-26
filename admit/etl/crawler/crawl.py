"""
Content Crawling System
Fetches HTML/PDF content with proper rate limiting and storage
"""

import asyncio
import aiohttp
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import aiofiles
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime
import mimetypes
import pdfplumber
from io import BytesIO
import json
import structlog
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import CrawlResult

logger = structlog.get_logger()


class ContentFetcher:
    """Fetches and stores web content with multiple strategies"""

    def __init__(self, storage_config: Dict[str, Any] = None):
        self.storage_config = storage_config or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.playwright_context = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None

        # Rate limiting
        self.domain_delays: Dict[str, float] = {}
        self.last_request_times: Dict[str, datetime] = {}

        # Configuration
        self.user_agent = "GradAdmissionsBot/1.0 (Educational Research; contact@gradbot.edu)"
        self.default_delay = 1.5  # seconds between requests to same domain
        self.max_retries = 3
        self.request_timeout = 30

        # Storage paths
        self.base_storage_path = Path(self.storage_config.get('base_path', './storage'))
        self.base_storage_path.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        """Initialize async resources"""
        # HTTP session
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
        )

        # Playwright for JS-heavy sites
        self.playwright_context = await async_playwright().start()
        self.browser = await self.playwright_context.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.browser_context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 1024}
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async resources"""
        if self.browser_context:
            await self.browser_context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright_context:
            await self.playwright_context.stop()
        if self.session:
            await self.session.close()

    async def fetch_content(self, url: str, force_browser: bool = False) -> Optional[CrawlResult]:
        """
        Main content fetching method

        Args:
            url: URL to fetch
            force_browser: Force use of Playwright browser

        Returns:
            CrawlResult object or None if failed
        """
        logger.info("Fetching content", url=url, method="browser" if force_browser else "auto")

        # Apply rate limiting
        await self._apply_rate_limit(url)

        # Try HTTP first unless forced to use browser
        if not force_browser:
            try:
                result = await self._fetch_http(url)
                if result:
                    return result
            except Exception as e:
                logger.warning("HTTP fetch failed, falling back to browser", url=url, error=str(e))

        # Fall back to browser
        return await self._fetch_browser(url)

    async def _apply_rate_limit(self, url: str):
        """Apply polite rate limiting per domain"""
        domain = urlparse(url).netloc

        if domain in self.last_request_times:
            elapsed = (datetime.now() - self.last_request_times[domain]).total_seconds()
            required_delay = self.domain_delays.get(domain, self.default_delay)

            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                logger.debug("Applying rate limit", domain=domain, sleep_seconds=sleep_time)
                await asyncio.sleep(sleep_time)

        self.last_request_times[domain] = datetime.now()

    async def _fetch_http(self, url: str) -> Optional[CrawlResult]:
        """Fetch using HTTP client (faster, works for static content)"""
        try:
            async with self.session.get(url) as response:
                content_type = response.headers.get('content-type', '')
                status_code = response.status

                if status_code != 200:
                    logger.warning("HTTP fetch failed", url=url, status_code=status_code)
                    return None

                # Handle PDFs
                if 'application/pdf' in content_type:
                    content_bytes = await response.read()
                    return await self._process_pdf(url, content_bytes, response.headers)

                # Handle HTML/text
                content = await response.text()
                etag = response.headers.get('etag', '')

                # Calculate DOM hash for change detection
                dom_hash = hashlib.sha256(content.encode()).hexdigest()

                # Store content
                storage_path = await self._store_content(url, content, content_type)

                return CrawlResult(
                    url=url,
                    status_code=status_code,
                    content_type=content_type,
                    content_length=len(content),
                    storage_path=str(storage_path),
                    dom_hash=dom_hash,
                    etag=etag,
                    robots_allowed=True,  # Assumed if we got this far
                    crawl_timestamp=datetime.now()
                )

        except asyncio.TimeoutError:
            logger.warning("HTTP request timeout", url=url)
            return None
        except Exception as e:
            logger.error("HTTP fetch error", url=url, error=str(e))
            raise  # Re-raise to trigger browser fallback

    async def _fetch_browser(self, url: str) -> Optional[CrawlResult]:
        """Fetch using Playwright browser (handles JS-heavy sites)"""
        page: Optional[Page] = None

        try:
            page = await self.browser_context.new_page()

            # Navigate with network idle wait
            await page.goto(url, wait_until='networkidle', timeout=self.request_timeout * 1000)

            # Wait a bit more for dynamic content
            await page.wait_for_timeout(2000)

            # Get final URL (after redirects)
            final_url = page.url

            # Get content
            content = await page.content()
            dom_hash = hashlib.sha256(content.encode()).hexdigest()

            # Take screenshot
            screenshot_bytes = await page.screenshot(full_page=True, type='png')

            # Store content and screenshot
            storage_path = await self._store_content(final_url, content, 'text/html')
            screenshot_path = await self._store_screenshot(final_url, screenshot_bytes)

            return CrawlResult(
                url=final_url,
                status_code=200,  # Browser successful navigation
                content_type='text/html',
                content_length=len(content),
                storage_path=str(storage_path),
                screenshot_path=str(screenshot_path),
                dom_hash=dom_hash,
                robots_allowed=True,
                crawl_timestamp=datetime.now()
            )

        except Exception as e:
            logger.error("Browser fetch error", url=url, error=str(e))
            return None

        finally:
            if page:
                await page.close()

    async def _process_pdf(self, url: str, pdf_bytes: bytes, headers: Dict[str, str]) -> CrawlResult:
        """Process PDF content"""
        try:
            # Extract text from PDF
            extracted_content = []

            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    tables = page.extract_tables()

                    page_content = {
                        'page': page_num,
                        'text': text or '',
                        'tables': tables or [],
                        'bbox': page.bbox if hasattr(page, 'bbox') else None
                    }
                    extracted_content.append(page_content)

            # Store original PDF and extracted text
            pdf_storage_path = await self._store_binary_content(url, pdf_bytes, 'application/pdf')
            text_content = json.dumps(extracted_content, indent=2)
            text_storage_path = await self._store_content(url, text_content, 'application/json', suffix='_extracted')

            # Hash the extracted text for change detection
            dom_hash = hashlib.sha256(text_content.encode()).hexdigest()

            return CrawlResult(
                url=url,
                status_code=200,
                content_type='application/pdf',
                content_length=len(pdf_bytes),
                storage_path=str(text_storage_path),  # Point to extracted text
                dom_hash=dom_hash,
                etag=headers.get('etag', ''),
                robots_allowed=True,
                crawl_timestamp=datetime.now()
            )

        except Exception as e:
            logger.error("PDF processing error", url=url, error=str(e))
            return None

    async def _store_content(self, url: str, content: str, content_type: str, suffix: str = '') -> Path:
        """Store content to local filesystem"""
        # Generate filename from URL and timestamp
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path_part = parsed_url.path.replace('/', '_').replace('.', '_')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

        filename = f"{domain}_{path_part}_{timestamp}_{content_hash}{suffix}"

        # Determine subdirectory by content type
        if 'html' in content_type:
            subdir = 'html'
            filename += '.html'
        elif 'pdf' in content_type:
            subdir = 'pdfs'
            filename += '.json'  # Extracted PDF content
        else:
            subdir = 'other'
            filename += '.txt'

        storage_path = self.base_storage_path / subdir / filename
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        async with aiofiles.open(storage_path, 'w', encoding='utf-8') as f:
            await f.write(content)

        # Store metadata
        metadata = {
            'url': url,
            'content_type': content_type,
            'content_length': len(content),
            'stored_at': datetime.now().isoformat(),
            'storage_path': str(storage_path)
        }

        metadata_path = storage_path.with_suffix(storage_path.suffix + '.meta.json')
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(json.dumps(metadata, indent=2))

        logger.debug("Content stored", url=url, path=str(storage_path))
        return storage_path

    async def _store_binary_content(self, url: str, content: bytes, content_type: str) -> Path:
        """Store binary content (PDFs, images)"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path_part = parsed_url.path.replace('/', '_')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hashlib.sha256(content).hexdigest()[:8]

        # Get appropriate extension
        extension = mimetypes.guess_extension(content_type) or '.bin'
        filename = f"{domain}_{path_part}_{timestamp}_{content_hash}{extension}"

        subdir = 'pdfs' if 'pdf' in content_type else 'binary'
        storage_path = self.base_storage_path / subdir / filename
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Write binary content
        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(content)

        logger.debug("Binary content stored", url=url, path=str(storage_path))
        return storage_path

    async def _store_screenshot(self, url: str, screenshot_bytes: bytes) -> Path:
        """Store screenshot"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path_part = parsed_url.path.replace('/', '_')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()[:8]

        filename = f"{domain}_{path_part}_{timestamp}_{screenshot_hash}.png"
        storage_path = self.base_storage_path / 'screenshots' / filename
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(screenshot_bytes)

        logger.debug("Screenshot stored", url=url, path=str(storage_path))
        return storage_path

    async def fetch_multiple(self, urls: List[str], max_concurrent: int = 5) -> List[CrawlResult]:
        """Fetch multiple URLs concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def fetch_with_semaphore(url: str) -> Optional[CrawlResult]:
            async with semaphore:
                return await self.fetch_content(url)

        # Create tasks
        tasks = [fetch_with_semaphore(url) for url in urls]

        # Execute with progress logging
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            if result:
                results.append(result)
                logger.info("Fetch completed", progress=f"{i}/{len(tasks)}", url=result.url)
            else:
                logger.warning("Fetch failed", progress=f"{i}/{len(tasks)}")

        return results


async def main():
    """Test the content fetcher"""
    test_urls = [
        "https://www.williams.edu/graduate",
        "https://engineering.asu.edu/graduate-programs",
        "https://www.uchicago.edu/admissions/graduate"
    ]

    storage_config = {
        'base_path': './test_storage'
    }

    async with ContentFetcher(storage_config) as fetcher:
        results = await fetcher.fetch_multiple(test_urls, max_concurrent=2)

        print(f"\n=== Fetched {len(results)} URLs ===")
        for result in results:
            print(f"✓ {result.url}")
            print(f"  Status: {result.status_code}")
            print(f"  Type: {result.content_type}")
            print(f"  Size: {result.content_length} bytes")
            print(f"  Storage: {result.storage_path}")
            print(f"  Hash: {result.dom_hash[:12]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())