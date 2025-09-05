import asyncio
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from core.models import AuthorProfile
from core.config import API_ENDPOINTS
from core.cache import cached_get_json
from util.http import get_client
from util.text import is_valid_url, ensure_absolute_url

logger = logging.getLogger(__name__)


async def enrich_author_with_orcid(author: AuthorProfile) -> None:
    """Enrich author profile with ORCID data."""
    if not author.orcid_id:
        return
    
    client = get_client()
    
    try:
        # Get ORCID profile
        orcid_url = f"{API_ENDPOINTS['orcid']}/{author.orcid_id}/record"
        headers = {
            "Accept": "application/json"
        }
        
        response = await cached_get_json(client, orcid_url, headers=headers)
        
        if not response:
            logger.warning(f"No ORCID data for {author.orcid_id}")
            return
        
        # Extract employment information
        _extract_employment_info(author, response)
        
        # Extract websites/homepage
        _extract_websites(author, response)
        
        logger.debug(f"Enriched {author.name} with ORCID data")
        
    except Exception as e:
        logger.warning(f"ORCID enrichment failed for {author.name}: {e}")


def _extract_employment_info(author: AuthorProfile, orcid_data: Dict[str, Any]) -> None:
    """Extract employment information from ORCID data."""
    try:
        activities_summary = orcid_data.get("activities-summary", {})
        employments = activities_summary.get("employments", {}).get("employment-summary", [])
        
        if not employments:
            return
        
        # Find the most recent employment
        current_employment = None
        latest_end_date = None
        
        for employment in employments:
            # Check if this is current (no end date or future end date)
            end_date = employment.get("end-date")
            
            if not end_date:  # Current position
                current_employment = employment
                break
            
            # Track latest end date
            if not latest_end_date or _compare_dates(end_date, latest_end_date) > 0:
                latest_end_date = end_date
                current_employment = employment
        
        if current_employment:
            # Extract title
            role_title = current_employment.get("role-title")
            if role_title:
                author.current_title = role_title
            
            # Extract department
            department = current_employment.get("department-name")
            if department:
                author.department = department
                
    except Exception as e:
        logger.warning(f"Failed to extract employment info: {e}")


def _extract_websites(author: AuthorProfile, orcid_data: Dict[str, Any]) -> None:
    """Extract website/homepage URLs from ORCID data."""
    try:
        person = orcid_data.get("person", {})
        
        # Check researcher URLs
        researcher_urls = person.get("researcher-urls", {}).get("researcher-url", [])
        
        homepage_candidates = []
        
        for url_entry in researcher_urls:
            url_name = url_entry.get("url-name", "").lower()
            url_value = url_entry.get("url", {}).get("value", "")
            
            if not url_value or not is_valid_url(url_value):
                continue
            
            # Prioritize homepage-like URLs
            if any(keyword in url_name for keyword in ["homepage", "website", "personal", "lab", "group"]):
                homepage_candidates.insert(0, url_value)
            else:
                homepage_candidates.append(url_value)
        
        # Also check websites section if available
        websites = person.get("websites", {}).get("website", [])
        for website in websites:
            url_value = website.get("url", {}).get("value", "")
            if url_value and is_valid_url(url_value):
                homepage_candidates.append(url_value)
        
        # Use the first valid homepage candidate
        if homepage_candidates:
            author.homepage_url = homepage_candidates[0]
            logger.debug(f"Found homepage for {author.name}: {author.homepage_url}")
            
    except Exception as e:
        logger.warning(f"Failed to extract websites: {e}")


def _compare_dates(date1: Dict[str, Any], date2: Dict[str, Any]) -> int:
    """Compare two ORCID date objects. Returns 1 if date1 > date2, -1 if date1 < date2, 0 if equal."""
    try:
        # Extract year, month, day
        year1 = date1.get("year", {}).get("value", 0)
        month1 = date1.get("month", {}).get("value", 1)
        day1 = date1.get("day", {}).get("value", 1)
        
        year2 = date2.get("year", {}).get("value", 0)
        month2 = date2.get("month", {}).get("value", 1)
        day2 = date2.get("day", {}).get("value", 1)
        
        # Convert to comparable tuples
        tuple1 = (int(year1), int(month1), int(day1))
        tuple2 = (int(year2), int(month2), int(day2))
        
        if tuple1 > tuple2:
            return 1
        elif tuple1 < tuple2:
            return -1
        else:
            return 0
            
    except Exception:
        return 0


async def enrich_authors_with_orcid(authors: List[AuthorProfile]) -> None:
    """Enrich multiple authors with ORCID data concurrently."""
    orcid_authors = [author for author in authors if author.orcid_id]
    
    if not orcid_authors:
        logger.info("No authors with ORCID IDs to enrich")
        return
    
    logger.info(f"Enriching {len(orcid_authors)} authors with ORCID data")
    
    # Process in batches to avoid overwhelming the ORCID API
    batch_size = 10
    for i in range(0, len(orcid_authors), batch_size):
        batch = orcid_authors[i:i + batch_size]
        tasks = [enrich_author_with_orcid(author) for author in batch]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"ORCID enrichment failed for {batch[j].name}: {result}")
        
        # Small delay between batches
        if i + batch_size < len(orcid_authors):
            await asyncio.sleep(1)