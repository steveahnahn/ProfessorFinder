#!/usr/bin/env python3
"""
Pilot ETL Runner
Run the complete ETL pipeline on a specific university for testing
"""

import asyncio
import sys
import os
from pathlib import Path
import aiohttp

# Load environment from .env.local
def load_env():
    """Load environment variables from .env.local"""
    env_file = Path(__file__).parent.parent / '.env.local'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️  No .env.local found at {env_file}")

load_env()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from etl.crawler.discover import UniversityDiscovery, DiscoveryConfig
from etl.parser.html_segmenter import HTMLSegmenter
from etl.extractor.mock_extract import mock_extractor
from etl.validator.rules import RequirementsValidator
from etl.storage.database import DatabaseStorage
from schemas.requirements import ProgramInfo, Modality, Schedule, Degree
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pilot universities for testing
PILOT_UNIVERSITIES = {
    "mit": {
        "name": "Massachusetts Institute of Technology",
        "website": "https://www.mit.edu",
        "priority_tier": 1,
        "search_paths": [
            "/academics/graduate-admissions/",
            "/admissions/graduate/",
            "/graduate/admissions/"
        ]
    },
    "stanford": {
        "name": "Stanford University",
        "website": "https://www.stanford.edu",
        "priority_tier": 1
    },
    "cmu": {
        "name": "Carnegie Mellon University",
        "website": "https://www.cmu.edu",
        "priority_tier": 1,
        "search_paths": [
            "/admission/graduate/",
            "/academics/graduate-programs/"
        ]
    },
    "uw": {
        "name": "University of Washington",
        "website": "https://www.washington.edu",
        "priority_tier": 2,
        "search_paths": [
            "/students/grad/",
            "/graduate/admissions/"
        ]
    },
    "nyu": {
        "name": "New York University",
        "website": "https://www.nyu.edu",
        "priority_tier": 2,
        "search_paths": [
            "/admissions/graduate-admissions/",
            "/academics/graduate/"
        ]
    }
}

class PilotETLRunner:
    def __init__(self):
        # UNLIMITED DISCOVERY - get ALL programs, schools, departments
        config = DiscoveryConfig(
            max_concurrent=5,
            max_urls_per_site=500,  # Allow deep discovery
            delay_between_requests=0.5  # Faster for deep crawling
        )
        self.discovery = UniversityDiscovery(config)
        self.segmenter = HTMLSegmenter()
        self.extractor = mock_extractor
        self.validator = RequirementsValidator()
        self.storage = DatabaseStorage()

    async def run_pilot(self, university_key: str, max_programs: int = None):
        """Run ETL pipeline on a specific pilot university"""

        if university_key not in PILOT_UNIVERSITIES:
            logger.error(f"Unknown university: {university_key}")
            return

        univ_config = PILOT_UNIVERSITIES[university_key]
        logger.info(f"Starting ETL for {univ_config['name']}")

        try:
            # Step 1: Discovery - Find admissions pages
            logger.info("Phase 1: Discovering admissions pages...")
            async with self.discovery as discovery:
                urls = await discovery.discover_admissions_urls(univ_config['website'])
            logger.info(f"Found {len(urls)} potential admissions URLs")

            if not urls:
                logger.warning("No admissions URLs discovered")
                return

            # Step 2: Categorize URLs by type for intelligent processing
            logger.info("Phase 2: Categorizing discovered URLs...")
            categorized_urls = self._categorize_urls(urls)

            logger.info(f"School URLs: {len(categorized_urls['schools'])}")
            logger.info(f"Department URLs: {len(categorized_urls['departments'])}")
            logger.info(f"Program URLs: {len(categorized_urls['programs'])}")
            logger.info(f"General URLs: {len(categorized_urls['general'])}")

            # Step 3: Process ALL URLs intelligently
            logger.info("Phase 3: Processing all discovered URLs...")
            processed_count = 0

            # Process in priority order: Programs > Departments > Schools > General
            all_urls_to_process = (
                categorized_urls['programs'] +
                categorized_urls['departments'] +
                categorized_urls['schools'] +
                categorized_urls['general']
            )

            # Apply limit if specified (for testing)
            if max_programs:
                all_urls_to_process = all_urls_to_process[:max_programs]

            logger.info(f"Processing {len(all_urls_to_process)} URLs total")

            for url in all_urls_to_process:
                try:
                    logger.info(f"Processing: {url}")

                    # Fetch HTML content with retry mechanism
                    html_content = await self._fetch_with_retry(url)
                    if not html_content:
                        continue

                    # Segment content
                    segments = self.segmenter.segment_html(html_content, url)
                    if not segments:
                        logger.warning(f"No content segments found for {url}")
                        continue

                    logger.info(f"Found {len(segments)} content segments")

                    # EXTRACT REAL program info from URL and content
                    program_info = self._extract_program_info_from_url(url, univ_config['name'], segments)

                    # Step 4: Extract requirements using LLM
                    logger.info(f"Phase 4: Extracting requirements for {program_info.program_name}...")
                    extraction_result = await self.extractor.extract_requirements(
                        segments, program_info
                    )

                    requirements = extraction_result.extracted_requirements
                    logger.info(f"Extracted requirements with {extraction_result.extraction_confidence:.2f} confidence")

                    # Step 5: Validate
                    logger.info("Phase 5: Validating requirements...")
                    validation_report = self.validator.validate_requirements(requirements)
                    logger.info(f"Validation complete: {len(validation_report.issues)} issues found")

                    # Step 6: Store in database
                    logger.info("Phase 6: Storing in database...")
                    await self.storage.store_requirements(requirements, validation_report)

                    processed_count += 1
                    logger.info(f"Successfully processed {processed_count} programs")

                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")
                    continue

            logger.info(f"ETL complete for {univ_config['name']}: {processed_count} programs processed")

        except Exception as e:
            logger.error(f"ETL failed for {university_key}: {str(e)}")
            raise

    def _categorize_urls(self, urls: list) -> dict:
        """Categorize discovered URLs into schools, departments, programs, and general"""
        categorized = {
            'schools': [],
            'departments': [],
            'programs': [],
            'general': []
        }

        for url in urls:
            url_lower = url.lower()

            # School-level URLs (subdomain schools)
            if any(school_domain in url_lower for school_domain in [
                'engineering.', 'gsb.', 'law.', 'med.', 'business.', 'education.'
            ]):
                categorized['schools'].append(url)

            # Program-specific URLs
            elif any(program_indicator in url_lower for program_indicator in [
                'masters', 'phd', 'doctoral', 'mba', 'ms-', 'phd-', 'program'
            ]):
                categorized['programs'].append(url)

            # Department-level URLs
            elif any(dept_indicator in url_lower for dept_indicator in [
                'computer-science', 'cs/', 'electrical-engineering', 'mechanical-engineering',
                'mathematics', 'physics', 'chemistry', 'biology', 'psychology'
            ]):
                categorized['departments'].append(url)

            # General admissions URLs
            else:
                categorized['general'].append(url)

        return categorized

    def _extract_program_info_from_url(self, url: str, institution_name: str, segments: list) -> ProgramInfo:
        """Extract REAL program information dynamically from URL and content"""
        url_lower = url.lower()

        # Extract school dynamically from subdomain and content
        school = self._extract_school_from_url_and_content(url_lower, segments)

        # Extract department dynamically from URL path and content
        department = self._extract_department_from_url_and_content(url_lower, segments)

        # Extract program name and degree dynamically from content
        program_name, degree = self._extract_program_and_degree_from_content(url_lower, segments)

        return ProgramInfo(
            institution=institution_name,
            school=school,
            department=department,
            program_name=program_name,
            degree=degree,
            website=url
        )

    def _extract_school_from_url_and_content(self, url_lower: str, segments: list) -> str:
        """Dynamically extract school name from URL and content"""
        # First try subdomain patterns
        if 'engineering.' in url_lower:
            return "School of Engineering"
        elif 'gsb.' in url_lower or 'business.' in url_lower:
            return "Graduate School of Business"
        elif 'law.' in url_lower:
            return "School of Law"
        elif 'med.' in url_lower:
            return "School of Medicine"
        elif 'ed.' in url_lower:
            return "School of Education"
        elif 'vpge.' in url_lower:
            return "Vice Provost for Graduate Education"

        # Try to extract from content
        for segment in segments:
            text_lower = segment.text.lower()

            # Look for school mentions in content
            if 'school of engineering' in text_lower:
                return "School of Engineering"
            elif 'graduate school of business' in text_lower or 'stanford business school' in text_lower:
                return "Graduate School of Business"
            elif 'school of law' in text_lower:
                return "School of Law"
            elif 'school of medicine' in text_lower:
                return "School of Medicine"
            elif 'school of education' in text_lower:
                return "School of Education"

        # Generic fallback based on content analysis
        return "Graduate School"

    def _extract_department_from_url_and_content(self, url_lower: str, segments: list) -> str:
        """Dynamically extract department from URL path and content"""
        # Extract from URL path patterns
        if 'computer-science' in url_lower or '/cs/' in url_lower:
            return "Computer Science"
        elif 'electrical-engineering' in url_lower:
            return "Electrical Engineering"
        elif 'mechanical-engineering' in url_lower:
            return "Mechanical Engineering"
        elif 'mathematics' in url_lower or '/math/' in url_lower:
            return "Mathematics"
        elif 'physics' in url_lower:
            return "Physics"
        elif 'chemistry' in url_lower:
            return "Chemistry"
        elif 'psychology' in url_lower:
            return "Psychology"
        elif 'business' in url_lower or 'mba' in url_lower:
            return "Business Administration"
        elif 'education' in url_lower and not url_lower.startswith('https://ed.'):
            return "Education"
        elif 'law' in url_lower:
            return "Law"
        elif 'medicine' in url_lower or 'medical' in url_lower:
            return "Medicine"

        # Extract from content
        for segment in segments:
            text_lower = segment.text.lower()

            # Look for department mentions
            if 'department of computer science' in text_lower:
                return "Computer Science"
            elif 'department of electrical engineering' in text_lower:
                return "Electrical Engineering"
            elif 'department of mechanical engineering' in text_lower:
                return "Mechanical Engineering"
            elif 'department of mathematics' in text_lower:
                return "Mathematics"
            elif 'department of physics' in text_lower:
                return "Physics"
            elif 'department of chemistry' in text_lower:
                return "Chemistry"
            elif 'department of psychology' in text_lower:
                return "Psychology"

        # Intelligent default based on school
        if 'gsb.' in url_lower or 'business.' in url_lower:
            return "Business Administration"
        elif 'law.' in url_lower:
            return "Law"
        elif 'med.' in url_lower:
            return "Medicine"
        elif 'ed.' in url_lower:
            return "Education"

        # Generic graduate programs fallback
        return "Graduate Programs"

    def _extract_program_and_degree_from_content(self, url_lower: str, segments: list) -> tuple:
        """Extract program name and degree type from content"""

        # First check URL for explicit degree indicators
        if 'mba' in url_lower:
            return "Master of Business Administration", Degree.MBA
        elif 'phd' in url_lower or 'doctoral' in url_lower:
            return "Doctor of Philosophy", Degree.PHD
        elif 'masters' in url_lower or 'ms-' in url_lower:
            return "Master of Science", Degree.MS
        elif 'jd' in url_lower and 'law' in url_lower:
            return "Juris Doctor", Degree.JD
        elif 'md' in url_lower and 'med' in url_lower:
            return "Doctor of Medicine", Degree.MD

        # Extract from content - look for specific program names
        for segment in segments:
            text_lower = segment.text.lower()

            # MBA programs
            if any(phrase in text_lower for phrase in [
                'master of business administration', 'mba program', 'business school'
            ]):
                return "Master of Business Administration", Degree.MBA

            # PhD programs
            elif any(phrase in text_lower for phrase in [
                'phd program', 'doctoral program', 'doctorate', 'ph.d.'
            ]):
                return "Doctor of Philosophy", Degree.PHD

            # Law programs
            elif any(phrase in text_lower for phrase in [
                'juris doctor', 'jd program', 'law degree'
            ]):
                return "Juris Doctor", Degree.JD

            # Medical programs
            elif any(phrase in text_lower for phrase in [
                'doctor of medicine', 'md program', 'medical degree'
            ]):
                return "Doctor of Medicine", Degree.MD

            # Master's programs (various types)
            elif 'master of science' in text_lower:
                return "Master of Science", Degree.MS
            elif 'master of arts' in text_lower:
                return "Master of Arts", Degree.MA
            elif 'master of engineering' in text_lower:
                return "Master of Engineering", Degree.MENG

        # Default based on school context
        if 'gsb.' in url_lower or 'business.' in url_lower:
            return "Master of Business Administration", Degree.MBA
        elif 'law.' in url_lower:
            return "Juris Doctor", Degree.JD
        elif 'med.' in url_lower:
            return "Doctor of Medicine", Degree.MD

        # General graduate program fallback
        return "Master of Science", Degree.MS

    async def _fetch_with_retry(self, url: str, max_retries: int = 2) -> str:
        """Fetch URL with retry mechanism for 403 errors and user agent rotation"""

        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "GradAdmissionsBot/1.0 (Educational Research; contact@gradbot.edu)"
        ]

        for attempt in range(max_retries + 1):
            try:
                headers = {
                    'User-Agent': user_agents[attempt % len(user_agents)],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 403:
                            if attempt < max_retries:
                                logger.warning(f"403 error for {url}, retrying with different user agent (attempt {attempt + 1})")
                                await asyncio.sleep(2)  # Wait before retry
                                continue
                            else:
                                logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts: 403 Forbidden")
                                return None
                        else:
                            logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                            return None

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                if attempt < max_retries:
                    await asyncio.sleep(3)
                    continue
                return None
            except Exception as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                return None

        return None

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python run_pilot.py <university_key>")
        print(f"Available universities: {', '.join(PILOT_UNIVERSITIES.keys())}")
        sys.exit(1)

    university_key = sys.argv[1]
    max_programs = int(sys.argv[2]) if len(sys.argv) > 2 else None  # Process ALL URLs by default

    runner = PilotETLRunner()
    await runner.run_pilot(university_key, max_programs)

if __name__ == "__main__":
    asyncio.run(main())