"""
University URL Discovery System
Finds admissions-related pages from institution websites
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Set, Dict, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import re
from dataclasses import dataclass
import structlog
from pathlib import Path
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import CrawlResult

logger = structlog.get_logger()


@dataclass
class DiscoveryConfig:
    """Configuration for URL discovery"""
    max_concurrent: int = 5
    request_timeout: int = 30
    max_urls_per_site: int = 200  # Increased to find more schools/departments
    respect_robots: bool = True
    delay_between_requests: float = 1.0  # Slightly faster for more discovery
    user_agent: str = "GradAdmissionsBot/1.0 (Educational Research; contact@gradbot.edu)"


class UniversityDiscovery:
    """Discovers admissions-related URLs from university websites"""

    def __init__(self, config: DiscoveryConfig = None):
        self.config = config or DiscoveryConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.robots_cache: Dict[str, bool] = {}
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)

        # Comprehensive patterns for nested discovery (University → School → Department → Program)
        self.admissions_patterns = {
            'url_patterns': [
                # Direct admissions
                r'.*admissions?.*',
                r'.*graduate.*admissions?.*',
                r'.*apply.*',
                r'.*requirements.*',

                # Program levels
                r'.*masters?.*',
                r'.*phd.*',
                r'.*doctoral.*',
                r'.*mba.*',
                r'.*programs?.*',
                r'.*degrees?.*',

                # School/College level patterns
                r'.*school.*of.*engineering.*',
                r'.*college.*of.*engineering.*',
                r'.*engineering.*school.*',
                r'.*school.*of.*business.*',
                r'.*business.*school.*',
                r'.*school.*of.*medicine.*',
                r'.*medical.*school.*',
                r'.*law.*school.*',
                r'.*school.*of.*law.*',
                r'.*arts.*sciences.*',
                r'.*liberal.*arts.*',

                # Department level patterns
                r'.*computer.*science.*',
                r'.*electrical.*engineering.*',
                r'.*mechanical.*engineering.*',
                r'.*biomedical.*engineering.*',
                r'.*civil.*engineering.*',
                r'.*chemical.*engineering.*',
                r'.*mathematics.*',
                r'.*physics.*',
                r'.*chemistry.*',
                r'.*biology.*',
                r'.*psychology.*',
                r'.*economics.*',
                r'.*statistics.*',
                r'.*data.*science.*',

                # Academic structure
                r'.*academics.*',
                r'.*departments.*',
                r'.*schools.*',
                r'.*colleges.*',
                r'.*faculty.*',
                r'.*research.*',
                r'.*graduate.*school.*'
            ],
            'text_patterns': [
                # Admissions keywords
                r'\bgraduate\s+admissions?\b',
                r'\bapplication\s+requirements?\b',
                r'\btoefl\b',
                r'\bgre\b',
                r'\bgmat\b',
                r'\bapplication\s+deadline\b',
                r'\bapply\s+now\b',
                r'\bmasters?\s+programs?\b',
                r'\bphd\s+programs?\b',

                # School/Department structure
                r'\bschool\s+of\s+engineering\b',
                r'\bengineering\s+school\b',
                r'\bcomputer\s+science\s+department\b',
                r'\bdepartment\s+of\s+computer\s+science\b',
                r'\bcs\s+department\b',
                r'\bgraduate\s+programs\b',
                r'\bacademic\s+departments\b',
                r'\bschools\s+and\s+colleges\b'
            ]
        }

    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=self.config.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.config.user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def discover_admissions_urls(self, institution_url: str) -> List[str]:
        """
        Main discovery method - finds all admissions-related URLs for an institution

        Args:
            institution_url: Base URL of the institution

        Returns:
            List of discovered admissions-related URLs
        """
        logger.info("Starting URL discovery", institution=institution_url)

        # Check robots.txt first
        if not await self.check_robots_allowed(institution_url):
            logger.warning("Crawling not allowed by robots.txt", url=institution_url)
            return []

        all_urls = set()

        # Strategy 1: Parse sitemap.xml
        sitemap_urls = await self.discover_from_sitemap(institution_url)
        all_urls.update(sitemap_urls)
        logger.info("Found URLs from sitemap", count=len(sitemap_urls))

        # Strategy 2: Crawl homepage for links
        homepage_urls = await self.discover_from_homepage(institution_url)
        all_urls.update(homepage_urls)
        logger.info("Found URLs from homepage", count=len(homepage_urls))

        # Strategy 3: Common URL patterns (comprehensive)
        pattern_urls = await self.discover_common_patterns(institution_url)
        all_urls.update(pattern_urls)
        logger.info("Found URLs from patterns", count=len(pattern_urls))

        # Strategy 4: Recursive discovery from key pages (like schools page)
        recursive_urls = await self.discover_recursive_links(all_urls, institution_url)
        all_urls.update(recursive_urls)
        logger.info("Found URLs from recursive discovery", count=len(recursive_urls))

        # Strategy 5: Multi-level discovery (school → department)
        multilevel_urls = await self.discover_multilevel_structure(institution_url, all_urls)
        all_urls.update(multilevel_urls)
        logger.info("Found URLs from multilevel discovery", count=len(multilevel_urls))

        # Filter and prioritize URLs
        filtered_urls = self.filter_and_prioritize_urls(list(all_urls), institution_url)

        logger.info("URL discovery completed",
                   total_discovered=len(all_urls),
                   filtered_count=len(filtered_urls))

        return filtered_urls

    async def check_robots_allowed(self, base_url: str) -> bool:
        """Check if crawling is allowed by robots.txt"""
        domain = urlparse(base_url).netloc

        # Check cache first
        if domain in self.robots_cache:
            return self.robots_cache[domain]

        if not self.config.respect_robots:
            self.robots_cache[domain] = True
            return True

        robots_url = urljoin(base_url, '/robots.txt')

        try:
            async with self.semaphore:
                async with self.session.get(robots_url) as response:
                    if response.status == 200:
                        robots_content = await response.text()

                        # Parse robots.txt
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        robots_lines = robots_content.splitlines()

                        # Simple robots.txt parsing
                        user_agent_section = False
                        disallow_patterns = []

                        for line in robots_lines:
                            line = line.strip()
                            if line.startswith('User-agent:'):
                                ua = line.split(':', 1)[1].strip()
                                user_agent_section = ua == '*' or 'bot' in ua.lower()
                            elif line.startswith('Disallow:') and user_agent_section:
                                disallow_path = line.split(':', 1)[1].strip()
                                disallow_patterns.append(disallow_path)

                        # Check if our paths are disallowed
                        test_paths = ['/graduate', '/admissions', '/apply']
                        allowed = not any(
                            any(test_path.startswith(pattern.rstrip('*'))
                                for pattern in disallow_patterns if pattern)
                            for test_path in test_paths
                        )
                    else:
                        allowed = True  # No robots.txt = allowed

        except Exception as e:
            logger.warning("Error checking robots.txt", url=robots_url, error=str(e))
            allowed = True  # Default to allowed on error

        self.robots_cache[domain] = allowed
        return allowed

    async def discover_from_sitemap(self, base_url: str) -> Set[str]:
        """Discover URLs from sitemap.xml"""
        sitemap_urls = {
            urljoin(base_url, '/sitemap.xml'),
            urljoin(base_url, '/sitemap_index.xml'),
            urljoin(base_url, '/sitemap/sitemap.xml')
        }

        discovered_urls = set()

        for sitemap_url in sitemap_urls:
            try:
                async with self.semaphore:
                    async with self.session.get(sitemap_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            urls = self.parse_sitemap_xml(content)
                            discovered_urls.update(urls)
                            logger.debug("Parsed sitemap", url=sitemap_url, urls_found=len(urls))
                            break  # Stop at first successful sitemap
            except Exception as e:
                logger.debug("Failed to fetch sitemap", url=sitemap_url, error=str(e))

        # Filter for admissions-related URLs
        admissions_urls = set()
        for url in discovered_urls:
            if self.is_admissions_related_url(url):
                admissions_urls.add(url)

        return admissions_urls

    def parse_sitemap_xml(self, content: str) -> List[str]:
        """Parse XML sitemap content"""
        urls = []
        try:
            # Handle both sitemap indexes and URL sets
            root = ET.fromstring(content)

            # Check for sitemap index
            sitemap_ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Look for <sitemap> entries (sitemap index)
            sitemaps = root.findall('.//s:sitemap/s:loc', sitemap_ns)
            if sitemaps:
                for sitemap in sitemaps:
                    if sitemap.text:
                        urls.append(sitemap.text)

            # Look for <url> entries (regular sitemap)
            url_entries = root.findall('.//s:url/s:loc', sitemap_ns)
            for url_entry in url_entries:
                if url_entry.text:
                    urls.append(url_entry.text)

        except ET.ParseError as e:
            logger.warning("Failed to parse sitemap XML", error=str(e))

        return urls

    async def discover_from_homepage(self, base_url: str) -> Set[str]:
        """Discover URLs by crawling homepage links"""
        discovered_urls = set()

        try:
            async with self.semaphore:
                async with self.session.get(base_url) as response:
                    if response.status != 200:
                        return discovered_urls

                    content = await response.text()

            # Parse HTML for links
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)

                # Filter for same domain and admissions-related
                if self.is_same_domain(absolute_url, base_url) and self.is_admissions_related_url(absolute_url):
                    discovered_urls.add(absolute_url)

                # Also check link text for admissions keywords
                link_text = link.get_text().lower()
                if any(re.search(pattern, link_text) for pattern in self.admissions_patterns['text_patterns']):
                    absolute_url = urljoin(base_url, href)
                    if self.is_same_domain(absolute_url, base_url):
                        discovered_urls.add(absolute_url)

            # Limit to prevent runaway discovery
            if len(discovered_urls) > self.config.max_urls_per_site:
                discovered_urls = set(list(discovered_urls)[:self.config.max_urls_per_site])

        except Exception as e:
            logger.warning("Failed to discover from homepage", url=base_url, error=str(e))

        return discovered_urls

    async def discover_common_patterns(self, base_url: str) -> Set[str]:
        """Try comprehensive URL patterns for schools, departments, and programs"""
        common_paths = [
            # General admissions
            '/graduate',
            '/graduate-admissions',
            '/admissions',
            '/admissions/graduate',
            '/apply',
            '/apply/graduate',
            '/academics/graduate',
            '/programs/graduate',
            '/graduate-school',
            '/grad',
            '/graduate-programs',
            '/future-students/graduate',

            # School/College level URLs
            '/schools',
            '/colleges',
            '/academics',
            '/academics/schools',
            '/academics/colleges',
            '/schools-colleges',
            '/school-of-engineering',
            '/engineering',
            '/engineering-school',
            '/college-of-engineering',
            '/school-of-business',
            '/business-school',
            '/business',
            '/graduate-school-of-business',
            '/school-of-medicine',
            '/medical-school',
            '/medicine',
            '/law-school',
            '/school-of-law',
            '/law',
            '/arts-sciences',
            '/liberal-arts',
            '/school-of-arts-sciences',

            # Department level URLs - Engineering
            '/computer-science',
            '/cs',
            '/dept/computer-science',
            '/departments/computer-science',
            '/csd',
            '/electrical-engineering',
            '/ee',
            '/mechanical-engineering',
            '/me',
            '/civil-engineering',
            '/ce',
            '/chemical-engineering',
            '/cheme',
            '/biomedical-engineering',
            '/bme',

            # Department level URLs - Other fields
            '/mathematics',
            '/math',
            '/physics',
            '/chemistry',
            '/biology',
            '/psychology',
            '/economics',
            '/econ',
            '/statistics',
            '/stats',
            '/data-science',

            # Academic structure URLs
            '/departments',
            '/academic-departments',
            '/graduate-programs',
            '/graduate-degrees',
            '/masters-programs',
            '/doctoral-programs',
            '/phd-programs',
            '/research',
            '/faculty',
            '/programs-of-study'
        ]

        candidate_urls = []
        for path in common_paths:
            candidate_urls.append(urljoin(base_url, path))

        # Test which URLs exist
        discovered_urls = set()

        for url in candidate_urls:
            try:
                async with self.semaphore:
                    # Use HEAD request for efficiency
                    async with self.session.head(url, allow_redirects=True) as response:
                        if response.status == 200:
                            discovered_urls.add(str(response.url))  # Use final URL after redirects

                    # Add delay to be polite
                    await asyncio.sleep(self.config.delay_between_requests)

            except Exception as e:
                logger.debug("Failed to check URL", url=url, error=str(e))

        return discovered_urls

    async def discover_recursive_links(self, found_urls: Set[str], base_url: str) -> Set[str]:
        """
        Recursively discover links from key pages we've found (like schools, academics pages)
        """
        discovered_urls = set()

        # Identify key pages that likely contain links to schools/departments
        key_pages = []
        for url in found_urls:
            url_lower = url.lower()
            if any(key_indicator in url_lower for key_indicator in [
                'schools', 'academics', 'colleges', 'departments'
            ]):
                key_pages.append(url)

        logger.info("Found key pages for recursive discovery", count=len(key_pages))

        # Crawl each key page to find school/department links
        for key_page in key_pages:
            try:
                async with self.semaphore:
                    async with self.session.get(key_page) as response:
                        if response.status != 200:
                            continue

                        content = await response.text()

                # Parse HTML for links
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')

                # Find all links on this key page
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    link_text = link.get_text().lower()

                    # Look for school/department keywords in link text
                    if any(keyword in link_text for keyword in [
                        'engineering', 'business', 'medicine', 'medical', 'law', 'education',
                        'computer science', 'mathematics', 'physics', 'chemistry', 'biology'
                    ]):
                        # Make absolute URL
                        if href.startswith('http'):
                            absolute_url = href
                        else:
                            absolute_url = urljoin(key_page, href)

                        # Check if it's a valid school/department URL
                        if self.is_same_domain(absolute_url, base_url):
                            discovered_urls.add(absolute_url)
                            logger.debug("Found recursive URL", parent=key_page, discovered=absolute_url, text=link_text[:50])

                await asyncio.sleep(self.config.delay_between_requests)

            except Exception as e:
                logger.debug("Failed recursive discovery", page=key_page, error=str(e))

        return discovered_urls

    async def discover_multilevel_structure(self, base_url: str, found_school_urls: Set[str]) -> Set[str]:
        """
        Multi-level discovery: Use found school URLs to discover departments within them
        OPTIMIZED: Parallel processing + priority-based + chunked
        """
        discovered_urls = set()

        # Identify school-level URLs from what we've found
        school_urls = []
        for url in found_school_urls:
            url_lower = url.lower()
            if any(school_indicator in url_lower for school_indicator in [
                'school', 'college', 'engineering', 'business', 'medicine', 'law', 'arts'
            ]):
                school_urls.append(url)

        if not school_urls:
            return discovered_urls

        logger.info("Found potential school URLs for multilevel discovery", count=len(school_urls))

        # PRIORITY-BASED: Start with common directory patterns, then CRAWL them dynamically
        high_priority_patterns = ['/programs', '/admissions', '/graduate', '/apply']
        low_priority_patterns = ['/departments', '/academics', '/degrees']

        # CHUNKED PROCESSING: Limit concurrent requests to prevent timeout
        max_concurrent_multilevel = min(3, len(school_urls))  # Max 3 schools at once
        semaphore_multilevel = asyncio.Semaphore(max_concurrent_multilevel)

        async def discover_school_departments(school_url: str) -> Set[str]:
            """Discover departments within a single school (parallel)"""
            school_discoveries = set()

            async def test_pattern(pattern: str) -> str:
                """Test a single pattern against a school"""
                try:
                    candidate_url = urljoin(school_url, pattern)

                    async with semaphore_multilevel:
                        async with self.session.head(candidate_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                final_url = str(response.url)
                                if self.is_same_domain(final_url, base_url):
                                    logger.debug("Found multilevel URL", parent=school_url, discovered=final_url)
                                    return final_url

                        # Shorter delay for multilevel
                        await asyncio.sleep(0.3)

                except Exception as e:
                    logger.debug("Failed multilevel test", school=school_url, pattern=pattern, error=str(e)[:50])

                return None

            # Test high-priority patterns first (parallel within school)
            high_priority_tasks = [test_pattern(pattern) for pattern in high_priority_patterns]
            high_results = await asyncio.gather(*high_priority_tasks, return_exceptions=True)

            for result in high_results:
                if result and isinstance(result, str):
                    school_discoveries.add(result)

                    # DYNAMIC CRAWLING: If we found a directory page, crawl it for more links
                    if any(directory in result.lower() for directory in ['/programs', '/departments', '/academics']):
                        try:
                            crawled_links = await self._crawl_directory_page(result)
                            school_discoveries.update(crawled_links)
                            logger.debug("Dynamic crawling found links", parent=result, count=len(crawled_links))
                        except Exception as e:
                            logger.debug("Crawling failed", url=result, error=str(e)[:50])

            # ALWAYS test low priority patterns too - we want ALL the information
            low_priority_tasks = [test_pattern(pattern) for pattern in low_priority_patterns]  # Test ALL patterns
            low_results = await asyncio.gather(*low_priority_tasks, return_exceptions=True)

            for result in low_results:
                if result and isinstance(result, str):
                    school_discoveries.add(result)

                    # DYNAMIC CRAWLING for low priority results too
                    if any(directory in result.lower() for directory in ['/programs', '/departments', '/academics']):
                        try:
                            crawled_links = await self._crawl_directory_page(result)
                            school_discoveries.update(crawled_links)
                            logger.debug("Dynamic crawling found links", parent=result, count=len(crawled_links))
                        except Exception as e:
                            logger.debug("Crawling failed", url=result, error=str(e)[:50])

            return school_discoveries

        # PARALLEL SCHOOL PROCESSING: Process multiple schools simultaneously
        school_tasks = [discover_school_departments(school_url) for school_url in school_urls]

        logger.info("Starting parallel multilevel discovery", schools=len(school_urls), max_concurrent=max_concurrent_multilevel)

        try:
            # NO TIMEOUT - let it run until complete to get ALL the information
            school_results = await asyncio.gather(*school_tasks, return_exceptions=True)

            for result in school_results:
                if isinstance(result, set):
                    discovered_urls.update(result)
                elif isinstance(result, Exception):
                    logger.warning("School discovery failed", error=str(result))

        except Exception as e:
            logger.error("Failed multilevel discovery", error=str(e))

        logger.info("Completed multilevel discovery", total_found=len(discovered_urls))
        return discovered_urls

    async def _crawl_directory_page(self, directory_url: str) -> Set[str]:
        """DYNAMICALLY crawl a directory page to find actual program/department links"""
        discovered = set()

        try:
            async with self.semaphore:
                async with self.session.get(directory_url, timeout=15) as response:
                    if response.status != 200:
                        return discovered

                    content = await response.text()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Find all links on the directory page
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(directory_url, href)

                # Only include links from same domain
                if not self.is_same_domain(absolute_url, directory_url):
                    continue

                link_text = link.get_text().lower().strip()

                # Look for program/department related links dynamically
                if any(keyword in link_text for keyword in [
                    'program', 'degree', 'master', 'phd', 'doctoral', 'mba', 'admission',
                    'apply', 'requirements', 'department', 'school', 'msx', 'executive'
                ]):
                    discovered.add(absolute_url)
                    logger.debug("Crawled directory link", parent=directory_url, found=absolute_url, text=link_text[:50])

                    # If this looks like a program page, try to find its admission page
                    if any(term in link_text for term in ['program', 'degree', 'master', 'phd', 'mba']) and not any(term in absolute_url.lower() for term in ['admission', 'apply']):
                        admission_variants = [
                            absolute_url.rstrip('/') + '/admission',
                            absolute_url.rstrip('/') + '/admissions',
                            absolute_url.rstrip('/') + '/apply',
                            absolute_url.rstrip('/') + '/requirements'
                        ]
                        for variant in admission_variants:
                            try:
                                async with self.session.head(variant, timeout=5) as resp:
                                    if resp.status == 200:
                                        discovered.add(variant)
                                        logger.debug("Found admission page", program=absolute_url, admission=variant)
                                        break  # Only add the first working variant
                            except:
                                pass

        except Exception as e:
            logger.warning("Failed to crawl directory page", url=directory_url, error=str(e))

        return discovered

    def is_admissions_related_url(self, url: str) -> bool:
        """Check if URL is related to admissions"""
        url_lower = url.lower()

        return any(
            re.search(pattern, url_lower)
            for pattern in self.admissions_patterns['url_patterns']
        )

    def is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL is from the same domain or valid subdomain"""
        url_domain = urlparse(url).netloc.lower()
        base_domain = urlparse(base_url).netloc.lower()

        # Exact match
        if url_domain == base_domain:
            return True

        # For universities, accept school subdomains
        # e.g., engineering.stanford.edu for stanford.edu
        if base_domain.startswith('www.'):
            base_domain = base_domain[4:]  # Remove www.

        if url_domain.startswith('www.'):
            url_domain = url_domain[4:]  # Remove www.

        # Accept subdomains of the main university domain
        if url_domain.endswith('.' + base_domain):
            return True

        # Also accept common university subdomain patterns
        if base_domain in url_domain and any(school in url_domain for school in [
            'engineering', 'business', 'law', 'medicine', 'med', 'gsb', 'ed'
        ]):
            return True

        return False

    def filter_and_prioritize_urls(self, urls: List[str], base_url: str) -> List[str]:
        """Filter and prioritize discovered URLs"""

        # Remove duplicates and invalid URLs
        clean_urls = []
        seen = set()

        for url in urls:
            # Normalize URL
            parsed = urlparse(url)
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip('/'),
                parsed.params,
                parsed.query,
                None  # Remove fragment
            ))

            if normalized not in seen and self.is_same_domain(normalized, base_url):
                clean_urls.append(normalized)
                seen.add(normalized)

        # Priority scoring
        def priority_score(url: str) -> int:
            score = 0
            url_lower = url.lower()

            # Higher priority for specific admissions terms
            if 'graduate' in url_lower and 'admission' in url_lower:
                score += 100
            elif 'graduate' in url_lower:
                score += 50
            elif 'admission' in url_lower:
                score += 50

            # Bonus for specific program types
            if any(term in url_lower for term in ['ms', 'ma', 'phd', 'masters', 'doctoral']):
                score += 30

            # Bonus for requirements/apply pages
            if any(term in url_lower for term in ['requirements', 'apply', 'application']):
                score += 40

            # Penalty for very long URLs (often less useful)
            if len(url) > 100:
                score -= 10

            return score

        # Sort by priority score (descending)
        prioritized_urls = sorted(clean_urls, key=priority_score, reverse=True)

        # Limit total URLs
        return prioritized_urls[:self.config.max_urls_per_site]


async def main():
    """Test the discovery system"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Test institutions
    test_institutions = [
        "https://www.williams.edu",
        "https://www.asu.edu",
        "https://www.uchicago.edu"
    ]

    config = DiscoveryConfig(max_concurrent=3, max_urls_per_site=20)

    async with UniversityDiscovery(config) as discovery:
        for institution_url in test_institutions:
            print(f"\n=== Discovering URLs for {institution_url} ===")
            urls = await discovery.discover_admissions_urls(institution_url)

            for i, url in enumerate(urls[:10], 1):  # Show top 10
                print(f"{i:2d}. {url}")

            if len(urls) > 10:
                print(f"    ... and {len(urls) - 10} more URLs")


if __name__ == "__main__":
    asyncio.run(main())