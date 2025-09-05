import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from urllib.parse import quote_plus

from core.models import AuthorProfile, Grant, Institution
from core.config import API_ENDPOINTS
from core.cache import cached_get_json
from util.http import get_client
from util.text import normalize_text

logger = logging.getLogger(__name__)


async def search_nsf_grants(author: AuthorProfile, institution: Institution) -> List[Grant]:
    """Search NSF Awards API for grants by PI name and institution."""
    client = get_client()
    grants = []
    
    try:
        # Search by PI name and institution
        # NSF API supports various query parameters
        params = {
            "printFields": "id,title,startDate,expDate,fundsObligatedAmt,agency,piFirstName,piLastName,institution",
            "piLastName": _extract_last_name(author.name),
            "institution": institution.display_name,
            "rpp": 200  # Results per page
        }
        
        response = await cached_get_json(
            client,
            API_ENDPOINTS["nsf_awards"],
            params
        )
        
        if response and "response" in response and "award" in response["response"]:
            awards = response["response"]["award"]
            
            for award in awards:
                grant = _parse_nsf_grant(award, author.name)
                if grant:
                    grants.append(grant)
        
        # Also search by first name if we have it
        first_name = _extract_first_name(author.name)
        if first_name and len(grants) < 10:  # Don't overwhelm with too many requests
            params_first = params.copy()
            params_first["piFirstName"] = first_name
            del params_first["piLastName"]  # Try just first name
            
            response2 = await cached_get_json(
                client,
                API_ENDPOINTS["nsf_awards"],
                params_first
            )
            
            if response2 and "response" in response2 and "award" in response2["response"]:
                awards2 = response2["response"]["award"]
                
                for award in awards2:
                    grant = _parse_nsf_grant(award, author.name)
                    if grant and not _is_duplicate_grant(grant, grants):
                        grants.append(grant)
        
        logger.debug(f"Found {len(grants)} NSF grants for {author.name}")
        
    except Exception as e:
        logger.warning(f"NSF grant search failed for {author.name}: {e}")
    
    return grants


def _parse_nsf_grant(award_data: Dict[str, Any], pi_name: str) -> Optional[Grant]:
    """Parse NSF award data into Grant model."""
    try:
        award_id = award_data.get("id")
        if not award_id:
            return None
        
        title = award_data.get("title", "")
        if not title:
            return None
        
        # Extract dates - DEBUG: Log what date fields are available
        raw_start = award_data.get("startDate")
        raw_end = award_data.get("expDate") 
        
        logger.debug(f"NSF Grant {award_id}: raw_start={raw_start}, raw_end={raw_end}")
        logger.debug(f"Available date fields: {[k for k in award_data.keys() if 'date' in k.lower()]}")
        
        start_date = _parse_nsf_date(raw_start)
        end_date = _parse_nsf_date(raw_end)
        
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
                logger.debug(f"NSF Grant {award_id}: KNOWN end_date={end_date}, future_active={is_active}")
            except ValueError:
                confidence = "unknown"
        
        elif start_date:
            # TIER 2: We have start date - ESTIMATED CONFIDENCE
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                years_since_start = (date.today() - start_date_obj).days / 365
                
                # NSF grants typically 3 years, some 5
                if years_since_start <= 3:
                    is_active = True
                    confidence = "estimated"
                    logger.debug(f"NSF Grant {award_id}: ESTIMATED from start={start_date}, years_ago={years_since_start:.1f}, likely_active={is_active}")
                else:
                    is_active = False
                    confidence = "estimated"
                    logger.debug(f"NSF Grant {award_id}: ESTIMATED from old start={start_date}, years_ago={years_since_start:.1f}, likely_expired")
            except ValueError:
                confidence = "unknown"
        
        else:
            # TIER 3: No dates - UNKNOWN CONFIDENCE
            is_active = False
            confidence = "unknown"
            logger.debug(f"NSF Grant {award_id}: UNKNOWN - has grant but no dates available")
        
        # Extract PI names
        pi_names = []
        pi_first = award_data.get("piFirstName", "")
        pi_last = award_data.get("piLastName", "")
        
        if pi_first and pi_last:
            pi_names.append(f"{pi_first} {pi_last}")
        elif pi_last:
            pi_names.append(pi_last)
        
        # If no PI names found, add the search name
        if not pi_names:
            pi_names.append(pi_name)
        
        grant_url = f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}"
        
        return Grant(
            id=str(award_id),
            title=title,
            funder="NSF",
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            confidence=confidence,
            url=grant_url,
            pi_names=pi_names
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse NSF grant: {e}")
        return None


def _parse_nsf_date(date_value: Any) -> Optional[str]:
    """Parse NSF date to YYYY-MM-DD format."""
    if not date_value:
        return None
    
    try:
        if isinstance(date_value, str):
            # NSF dates are typically in MM/dd/yyyy format
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        elif isinstance(date_value, (int, float)):
            # Sometimes dates are timestamps
            try:
                parsed_date = datetime.fromtimestamp(date_value)
                return parsed_date.strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass
    
    except Exception as e:
        logger.debug(f"Failed to parse NSF date {date_value}: {e}")
    
    return None


def _extract_first_name(full_name: str) -> str:
    """Extract first name from full name."""
    if not full_name:
        return ""
    
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def _extract_last_name(full_name: str) -> str:
    """Extract last name from full name."""
    if not full_name:
        return ""
    
    parts = full_name.strip().split()
    return parts[-1] if parts else ""


def _is_duplicate_grant(grant: Grant, existing_grants: List[Grant]) -> bool:
    """Check if grant is a duplicate of existing grants."""
    for existing in existing_grants:
        if (grant.id == existing.id or 
            (grant.title == existing.title and grant.funder == existing.funder)):
            return True
    return False


async def search_nsf_grants_for_authors(authors: List[AuthorProfile], 
                                       institution: Institution) -> None:
    """Search NSF grants for multiple authors concurrently."""
    if not authors:
        return
    
    logger.info(f"Searching NSF grants for {len(authors)} authors at {institution.display_name}")
    
    # Process in batches to be respectful to the API
    batch_size = 3  # NSF API is more restrictive
    for i in range(0, len(authors), batch_size):
        batch = authors[i:i + batch_size]
        tasks = [search_nsf_grants(author, institution) for author in batch]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"NSF grant search failed for {batch[j].name}: {result}")
            elif isinstance(result, list):
                # Store grants in author (extend existing grants if any)
                if hasattr(batch[j], 'grants'):
                    batch[j].grants.extend(result)
                else:
                    batch[j].grants = result
                
                active_grants = [g for g in result if g.is_active]
                if active_grants:
                    logger.info(f"Found {len(active_grants)} active NSF grants for {batch[j].name}")
        
        # Longer delay between batches for NSF
        if i + batch_size < len(authors):
            await asyncio.sleep(3)