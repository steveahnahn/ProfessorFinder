import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

from core.models import AuthorProfile, Grant, Institution
from core.config import API_ENDPOINTS
from core.cache import cached_get_json
from util.http import get_client
from util.text import normalize_text

logger = logging.getLogger(__name__)


async def search_nih_grants(author: AuthorProfile, institution: Institution) -> List[Grant]:
    """Search NIH RePORTER for grants by PI name and institution."""
    client = get_client()
    grants = []
    
    try:
        # Try multiple name variations for better matching
        name_variants = [
            author.name,  # "Thomas E. Joiner"
        ]
        
        # Add common variations
        name_parts = author.name.split()
        if len(name_parts) >= 2:
            # Try "Last, First Middle" format
            if len(name_parts) == 3:  # First Middle Last
                last_first = f"{name_parts[2]}, {name_parts[0]} {name_parts[1]}"
                name_variants.append(last_first)
            # Try without middle initial
            first_last = f"{name_parts[0]} {name_parts[-1]}"
            if first_last != author.name:
                name_variants.append(first_last)
        
        # Search by PI name variations (no institution filter - too restrictive)
        search_data = {
            "criteria": {
                "pi_names": [{"any_name": name} for name in name_variants]
            },
            "include_fields": [
                "ProjectTitle", "PrincipalInvestigators", "ProjectStartDate",
                "ProjectEndDate", "AwardAmount", "AgencyName", "ProjectNum",
                "OrgName", "FiscalYear"
            ],
            "offset": 0,
            "limit": 500
        }
        
        # Use the confirmed working NIH endpoint
        endpoint_url = f"{API_ENDPOINTS['nih_reporter']}/projects/search"
        # logger.info(f"Searching NIH grants for PI name variations: {name_variants}")  # Reduced verbosity
        logger.debug(f"NIH endpoint: {endpoint_url}")
        logger.debug(f"Request data: {search_data}")
        
        try:
            response = await client.post_json(endpoint_url, search_data)
            if response:
                logger.debug(f"NIH API success for {author.name}: {len(response.get('results', []))} grants")
            else:
                logger.debug(f"NIH API returned no data for {author.name}")
        except Exception as e:
            logger.warning(f"NIH API failed for {author.name}: {e}")
            response = None
        
        if response and "results" in response:
            # logger.info(f"Processing {len(response['results'])} NIH projects for {author.name}")  # Reduced verbosity
            for project in response["results"]:
                grant = _parse_nih_grant(project, author.name)
                if grant:
                    grants.append(grant)
                    # logger.info(f"Successfully parsed grant {grant.id} (confidence: {grant.confidence}) for {author.name}")  # Reduced verbosity
                # else:
                #     logger.info(f"Failed to parse a project for {author.name}")  # Reduced verbosity
        # else:
        #     logger.info(f"No valid NIH response or results for {author.name}")  # Reduced verbosity
        
        # Only log if many grants found to avoid spam
        if len(grants) > 10:
            logger.info(f"Found {len(grants)} NIH grants for {author.name}")
        
    except Exception as e:
        logger.warning(f"NIH grant search failed for {author.name}: {e}")
    
    return grants


def _parse_nih_grant(project_data: Dict[str, Any], pi_name: str) -> Optional[Grant]:
    """Parse NIH project data into Grant model."""
    try:
        project_num = project_data.get("project_num") or project_data.get("ProjectNum", "")
        if not project_num:
            return None
        
        title = project_data.get("project_title") or project_data.get("ProjectTitle", "")
        if not title:
            return None
        
        # Extract dates - DEBUG: Log what date fields are available
        raw_start = project_data.get("project_start_date") or project_data.get("ProjectStartDate")
        raw_end = project_data.get("project_end_date") or project_data.get("ProjectEndDate")
        
        logger.debug(f"NIH Grant {project_num}: raw_start={raw_start}, raw_end={raw_end}")
        logger.debug(f"Available date fields: {[k for k in project_data.keys() if 'date' in k.lower()]}")
        
        start_date = _parse_nih_date(raw_start)
        end_date = _parse_nih_date(raw_end)
        
        # Determine funding status with confidence levels
        is_active = False
        confidence = "unknown"
        
        if end_date:
            # TIER 1: We have an end date - HIGHEST CONFIDENCE
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                one_year_from_now = date.today() + timedelta(days=365)
                is_active = end_date_obj >= one_year_from_now
                confidence = "known"  # We KNOW the end date
                logger.debug(f"Grant {project_num}: KNOWN end_date={end_date}, future_active={is_active}")
            except ValueError:
                logger.warning(f"Failed to parse end date: {end_date}")
                confidence = "unknown"
        
        elif start_date:
            # TIER 2: We have start date - ESTIMATED CONFIDENCE  
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                years_since_start = (date.today() - start_date_obj).days / 365
                
                # More confident estimates since we have start date
                if years_since_start <= 3:  # Most grants are 3-5 years
                    is_active = True
                    confidence = "estimated"  # We're making an educated guess
                    logger.debug(f"Grant {project_num}: ESTIMATED from start={start_date}, years_ago={years_since_start:.1f}, likely_active={is_active}")
                else:
                    is_active = False
                    confidence = "estimated"  # Old grant, probably expired
                    logger.debug(f"Grant {project_num}: ESTIMATED from old start={start_date}, years_ago={years_since_start:.1f}, likely_expired")
            except ValueError:
                logger.warning(f"Failed to parse start date: {start_date}")
                confidence = "unknown"
        
        else:
            # TIER 3: No dates - UNKNOWN CONFIDENCE
            # We know they GOT a grant but can't determine timing
            is_active = False  # Conservative: don't assume active without dates
            confidence = "unknown"
            logger.debug(f"Grant {project_num}: UNKNOWN - has grant but no dates available")
        
        # Extract PI names
        pi_names = []
        pis = project_data.get("principal_investigators") or project_data.get("PrincipalInvestigators", [])
        for pi in pis:
            if isinstance(pi, dict):
                full_name = pi.get("full_name") or pi.get("FullName", "")
                if full_name:
                    pi_names.append(full_name)
            elif isinstance(pi, str):
                pi_names.append(pi)
        
        # If no PIs found in structured data, add the search name
        if not pi_names:
            pi_names.append(pi_name)
        
        grant_url = f"https://reporter.nih.gov/search/{project_num}"
        
        return Grant(
            id=project_num,
            title=title,
            funder="NIH",
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            confidence=confidence,
            url=grant_url,
            pi_names=pi_names
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse NIH grant: {e}")
        return None


def _parse_nih_date(date_value: Any) -> Optional[str]:
    """Parse various NIH date formats to YYYY-MM-DD."""
    if not date_value:
        return None
    
    try:
        if isinstance(date_value, str):
            # Try different formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        elif isinstance(date_value, dict):
            # Handle structured date objects
            year = date_value.get("year") or date_value.get("Year")
            month = date_value.get("month") or date_value.get("Month", 1)
            day = date_value.get("day") or date_value.get("Day", 1)
            
            if year:
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except (ValueError, TypeError):
                    pass
        
    except Exception as e:
        logger.debug(f"Failed to parse NIH date {date_value}: {e}")
    
    return None


async def search_grants_for_authors(authors: List[AuthorProfile], 
                                  institution: Institution) -> None:
    """Search NIH grants for multiple authors concurrently."""
    if not authors:
        return
    
    # logger.info(f"Searching NIH grants for {len(authors)} authors at {institution.display_name}")  # Reduced verbosity
    
    # Process in batches to be respectful to the API
    batch_size = 5
    for i in range(0, len(authors), batch_size):
        batch = authors[i:i + batch_size]
        tasks = [search_nih_grants(author, institution) for author in batch]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"NIH grant search failed for {batch[j].name}: {result}")
            elif isinstance(result, list):
                # logger.info(f"NIH API returned {len(result)} total grants for {batch[j].name}")  # Reduced verbosity
                
                # Store grants in author evidence (we'll add this field)
                if hasattr(batch[j], 'grants'):
                    batch[j].grants.extend(result)
                    # logger.info(f"Extended grants list for {batch[j].name}, now has {len(batch[j].grants)} total")  # Reduced verbosity
                else:
                    batch[j].grants = result
                    # logger.info(f"Set grants list for {batch[j].name} to {len(result)} grants")  # Reduced verbosity
                
                active_grants = [g for g in result if g.is_active]
                if len(active_grants) > 5:  # Only log significant grant counts
                    logger.info(f"Found {len(active_grants)} active NIH grants for {batch[j].name}")
                # else:
                #     logger.info(f"No active NIH grants found for {batch[j].name} (out of {len(result)} total)")  # Reduced verbosity
        
        # Small delay between batches
        if i + batch_size < len(authors):
            await asyncio.sleep(2)