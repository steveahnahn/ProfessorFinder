"""
Recruitment signal detection - find professors actively seeking graduate students.
"""

import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from core.models import AuthorProfile, RecruitmentSignal
from util.http import get_client
from util.text import clean_html, extract_text_from_html

logger = logging.getLogger(__name__)

# Keywords that indicate graduate student recruitment
RECRUITMENT_KEYWORDS = [
    # Direct recruitment signals
    "seeking graduate students", "graduate student positions", "phd positions available",
    "graduate openings", "prospective students", "accepting graduate students",
    "graduate student opportunities", "phd opportunities", "doctoral positions",
    
    # Lab/group recruitment
    "join our lab", "join our research group", "lab positions", "research positions",
    "graduate research assistants", "research opportunities",
    
    # Application language
    "applications invited", "now accepting applications", "apply to join",
    "interested students should contact", "prospective applicants",
    
    # Funding indicators
    "funded positions", "graduate fellowships", "research assistantships",
    "full funding available", "funded phd positions"
]

# Career stage indicators (suggests established professor who can take students)
CAREER_INDICATORS = [
    "professor", "associate professor", "assistant professor",
    "principal investigator", "lab director", "research director"
]

async def detect_recruitment_signals(authors: List[AuthorProfile]) -> List[AuthorProfile]:
    """
    Check each author for recruitment signals by examining their web presence.
    This is the key function that differentiates professors looking for students.
    """
    client = get_client()
    enriched_authors = []
    
    logger.info(f"Checking recruitment signals for {len(authors)} potential advisors...")
    
    for author in authors:
        try:
            # Get homepage URL from author profile or search for it
            homepage_url = await _find_author_homepage(client, author)
            
            if homepage_url:
                logger.info(f"Checking recruitment signals for {author.name} at {homepage_url}")
                recruitment = await _check_website_for_recruitment(client, homepage_url)
                
                if recruitment.is_recruiting:
                    author.recruitment = recruitment
                    enriched_authors.append(author)
                    logger.info(f"✅ {author.name} is seeking graduate students!")
                else:
                    logger.debug(f"No recruitment signals found for {author.name}")
            else:
                logger.debug(f"No homepage found for {author.name}")
                
        except Exception as e:
            logger.warning(f"Failed to check recruitment for {author.name}: {e}")
        
        # Rate limiting
        await asyncio.sleep(2)
        
        # Prevent overwhelming with too many web requests
        if len(enriched_authors) >= 50:
            logger.info("Reached recruitment check limit (50)")
            break
    
    # Don't close the client here - it's a shared instance!
    # await client.close()  # REMOVED: This was closing the shared HTTP client
    logger.info(f"Found {len(enriched_authors)} professors actively seeking graduate students")
    return enriched_authors

async def _find_author_homepage(client, author: AuthorProfile) -> Optional[str]:
    """Find the author's homepage/lab website."""
    try:
        # Method 1: Check OpenAlex for homepage
        if author.homepage_url:
            return author.homepage_url
        
        # Method 2: Search for "[Name] [Institution] lab" or "[Name] [Institution] homepage"
        if author.institution:
            search_queries = [
                f'"{author.name}" {author.institution.display_name} lab',
                f'"{author.name}" {author.institution.display_name} homepage',
                f'"{author.name}" {author.institution.display_name} faculty'
            ]
            
            # For now, construct likely URLs based on common patterns
            # This is a simplified approach - in practice, you'd use web search
            
            # Common academic URL patterns
            institution_domain = _guess_institution_domain(author.institution.display_name)
            if institution_domain:
                possible_urls = [
                    f"https://{institution_domain}/~{author.name.lower().replace(' ', '')}",
                    f"https://{institution_domain}/faculty/{author.name.lower().replace(' ', '_')}",
                    f"https://{institution_domain}/people/{author.name.lower().replace(' ', '-')}"
                ]
                
                for url in possible_urls:
                    if await _url_exists(client, url):
                        return url
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to find homepage for {author.name}: {e}")
        return None

async def _check_website_for_recruitment(client, url: str) -> RecruitmentSignal:
    """Check a website for graduate student recruitment signals."""
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 200:
            html_content = response.text
            text_content = extract_text_from_html(html_content).lower()
            
            # Look for recruitment keywords
            for keyword in RECRUITMENT_KEYWORDS:
                if keyword in text_content:
                    # Extract surrounding context
                    snippet = _extract_snippet_around_keyword(text_content, keyword)
                    return RecruitmentSignal(
                        is_recruiting=True,
                        snippet=snippet,
                        url=url
                    )
            
            # Also check for general indicators of an active lab
            active_indicators = [
                "current projects", "recent publications", "news", "updates",
                "graduate students", "phd students", "current members"
            ]
            
            active_signals = sum(1 for indicator in active_indicators if indicator in text_content)
            
            # If many active signals, might be recruiting even without explicit mention
            if active_signals >= 3:
                return RecruitmentSignal(
                    is_recruiting=True,
                    snippet=f"Active lab website with {active_signals} activity indicators",
                    url=url
                )
        
        return RecruitmentSignal(is_recruiting=False)
        
    except Exception as e:
        logger.debug(f"Failed to check website {url}: {e}")
        return RecruitmentSignal(is_recruiting=False)

def _guess_institution_domain(institution_name: str) -> Optional[str]:
    """Guess the web domain for an institution."""
    # This is a simplified mapping - in practice, you'd have a more comprehensive database
    domain_mapping = {
        "harvard university": "harvard.edu",
        "stanford university": "stanford.edu", 
        "mit": "mit.edu",
        "yale university": "yale.edu",
        "columbia university": "columbia.edu",
        "university of california, berkeley": "berkeley.edu",
        "university of california, los angeles": "ucla.edu",
        "university of michigan": "umich.edu",
        "princeton university": "princeton.edu",
        "university of chicago": "uchicago.edu"
    }
    
    name_lower = institution_name.lower()
    return domain_mapping.get(name_lower)

async def _url_exists(client, url: str) -> bool:
    """Check if a URL exists without downloading full content."""
    try:
        response = await client.head(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def _extract_snippet_around_keyword(text: str, keyword: str, context_chars: int = 200) -> str:
    """Extract text snippet around a keyword for context."""
    try:
        pos = text.find(keyword.lower())
        if pos == -1:
            return keyword
        
        start = max(0, pos - context_chars // 2)
        end = min(len(text), pos + len(keyword) + context_chars // 2)
        
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
            
        return snippet
        
    except Exception:
        return keyword