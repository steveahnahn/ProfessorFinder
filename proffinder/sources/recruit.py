import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

try:
    from selectolax.parser import HTMLParser
except ImportError:
    from bs4 import BeautifulSoup
    HTMLParser = None

from core.models import AuthorProfile, RecruitmentSignal
from core.config import RECRUITING_PHRASES, MAX_RECRUITING_SNIPPET
from core.cache import cached_get_text
from util.http import get_client
from util.text import normalize_text, truncate_with_ellipsis

logger = logging.getLogger(__name__)


async def detect_recruitment_signals(authors: List[AuthorProfile]) -> None:
    """Detect recruitment signals for authors with homepage URLs."""
    homepage_authors = [author for author in authors if author.homepage_url]
    
    if not homepage_authors:
        logger.info("No authors with homepage URLs to check for recruitment signals")
        return
    
    logger.info(f"Checking recruitment signals for {len(homepage_authors)} authors with homepages")
    
    # Process in batches to avoid overwhelming servers
    batch_size = 5
    for i in range(0, len(homepage_authors), batch_size):
        batch = homepage_authors[i:i + batch_size]
        tasks = [_check_author_recruitment(author) for author in batch]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Recruitment check failed for {batch[j].name}: {result}")
            elif result:
                batch[j].recruitment = result
                logger.info(f"Found recruitment signal for {batch[j].name}")
        
        # Small delay between batches
        if i + batch_size < len(homepage_authors):
            await asyncio.sleep(2)


async def _check_author_recruitment(author: AuthorProfile) -> Optional[RecruitmentSignal]:
    """Check a single author's homepage for recruitment signals."""
    if not author.homepage_url:
        return None
    
    try:
        # Check robots.txt first
        if not await _check_robots_permission(author.homepage_url):
            logger.debug(f"Robots.txt disallows fetching {author.homepage_url}")
            return RecruitmentSignal(is_recruiting=False)
        
        # Fetch the homepage
        client = get_client()
        html_content = await cached_get_text(client, author.homepage_url)
        
        if not html_content:
            return RecruitmentSignal(is_recruiting=False)
        
        # Parse and analyze content
        text_content = _extract_text_content(html_content)
        recruitment_info = _analyze_text_for_recruitment(text_content)
        
        if recruitment_info["is_recruiting"]:
            return RecruitmentSignal(
                is_recruiting=True,
                snippet=recruitment_info["snippet"],
                url=author.homepage_url
            )
        else:
            return RecruitmentSignal(is_recruiting=False)
            
    except Exception as e:
        logger.warning(f"Recruitment detection failed for {author.name}: {e}")
        return RecruitmentSignal(is_recruiting=False)


async def _check_robots_permission(url: str) -> bool:
    """Check if robots.txt allows fetching the URL."""
    try:
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        client = get_client()
        robots_content = await cached_get_text(client, robots_url)
        
        if not robots_content:
            return True  # No robots.txt, assume allowed
        
        # Simple robots.txt parsing
        user_agent_section = False
        for line in robots_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                user_agent_section = (agent == '*' or 'proffinder' in agent.lower())
            elif user_agent_section and line.lower().startswith('disallow:'):
                disallowed_path = line.split(':', 1)[1].strip()
                if disallowed_path == '/' or parsed_url.path.startswith(disallowed_path):
                    return False
        
        return True
        
    except Exception as e:
        logger.debug(f"Robots.txt check failed for {url}: {e}")
        return True  # Default to allowed if check fails


def _extract_text_content(html_content: str) -> str:
    """Extract clean text content from HTML."""
    try:
        if HTMLParser:
            # Use selectolax for faster parsing
            tree = HTMLParser(html_content)
            
            # Remove script and style elements
            for tag in tree.css('script, style, nav, footer, header'):
                tag.decompose()
            
            # Get text from main content areas
            main_content = ""
            for selector in ['main', '[role="main"]', '.content', '.main-content', 'body']:
                elements = tree.css(selector)
                if elements:
                    main_content = elements[0].text()
                    break
            
            return main_content if main_content else tree.text()
        else:
            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text from main content
            main = soup.find(['main', 'div'], {'role': 'main'}) or soup.find(['div'], class_=re.compile(r'content|main'))
            if main:
                return main.get_text()
            else:
                return soup.get_text()
                
    except Exception as e:
        logger.warning(f"HTML parsing failed: {e}")
        return html_content  # Return raw HTML as fallback


def _analyze_text_for_recruitment(text_content: str) -> dict:
    """Analyze text content for recruitment phrases."""
    if not text_content:
        return {"is_recruiting": False, "snippet": None}
    
    normalized_text = normalize_text(text_content)
    
    # Look for recruiting phrases
    for phrase in RECRUITING_PHRASES:
        phrase_pattern = re.compile(r'\b' + re.escape(phrase.lower()) + r'\b', re.IGNORECASE)
        match = phrase_pattern.search(normalized_text)
        
        if match:
            # Extract context around the match
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(normalized_text), match.end() + 100)
            snippet = normalized_text[start_pos:end_pos].strip()
            
            # Clean up the snippet
            snippet = re.sub(r'\s+', ' ', snippet)
            snippet = truncate_with_ellipsis(snippet, MAX_RECRUITING_SNIPPET)
            
            return {
                "is_recruiting": True,
                "snippet": snippet
            }
    
    # Look for other recruiting indicators
    recruiting_indicators = [
        r'\bposition[s]?\s+available\b',
        r'\bhiring\b',
        r'\bapplication[s]?\s+welcome\b',
        r'\bstudent[s]?\s+wanted\b',
        r'\bopening[s]?\s+for\b',
        r'\bgraduate\s+student[s]?\s+position[s]?\b',
        r'\bpostdoc[a-z]*\s+position[s]?\b',
        r'\bra\s+position[s]?\b',
        r'\bresearch\s+assistant[s]?\s+position[s]?\b'
    ]
    
    for pattern in recruiting_indicators:
        match = re.search(pattern, normalized_text, re.IGNORECASE)
        if match:
            # Extract context
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(normalized_text), match.end() + 100)
            snippet = normalized_text[start_pos:end_pos].strip()
            
            snippet = re.sub(r'\s+', ' ', snippet)
            snippet = truncate_with_ellipsis(snippet, MAX_RECRUITING_SNIPPET)
            
            return {
                "is_recruiting": True,
                "snippet": snippet
            }
    
    return {"is_recruiting": False, "snippet": None}