import asyncio
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from core.models import Institution
from core.config import API_ENDPOINTS
from core.cache import cached_get_json
from util.http import get_client
from util.text import normalize_text

logger = logging.getLogger(__name__)


async def resolve_institution_to_ror(institution_name: str) -> Optional[Institution]:
    """Resolve institution name to ROR ID and details."""
    client = get_client()
    
    try:
        # Search ROR API
        search_url = f"{API_ENDPOINTS['ror']}"
        params = {
            "query": institution_name
        }
        
        response = await cached_get_json(client, search_url, params)
        
        if not response or "items" not in response:
            logger.warning(f"No ROR response for institution: {institution_name}")
            return None
        
        items = response["items"]
        if not items:
            logger.warning(f"No ROR results for institution: {institution_name}")
            return None
        
        # Find best match
        best_match = _find_best_match(institution_name, items)
        if not best_match:
            logger.warning(f"No good ROR match for institution: {institution_name}")
            return None
        
        ror_id = best_match.get("id", "").replace("https://ror.org/", "")
        display_name = best_match.get("name", institution_name)
        country = None
        
        # Extract country
        country_info = best_match.get("country", {})
        if isinstance(country_info, dict):
            country = country_info.get("country_name")
        
        # Get OpenAlex Institution ID for this ROR ID
        openalex_id = await _get_openalex_id_for_ror(client, ror_id)
        
        return Institution(
            name=institution_name,
            ror_id=ror_id,
            display_name=display_name,
            country=country,
            openalex_id=openalex_id
        )
        
    except Exception as e:
        logger.error(f"ROR resolution failed for '{institution_name}': {e}")
        return None


def _find_best_match(query: str, items: List[dict]) -> Optional[dict]:
    """Find the best matching ROR record."""
    if not items:
        return None
    
    normalized_query = normalize_text(query)
    
    # Score each item
    scored_items = []
    for item in items:
        score = _calculate_match_score(normalized_query, item)
        if score > 0:
            scored_items.append((score, item))
    
    if not scored_items:
        return None
    
    # Return highest scored item
    scored_items.sort(key=lambda x: x[0], reverse=True)
    return scored_items[0][1]


def _calculate_match_score(query: str, ror_item: dict) -> float:
    """Calculate match score for a ROR item."""
    score = 0.0
    
    # Primary name match
    name = normalize_text(ror_item.get("name", ""))
    if query == name:
        score += 100.0
    elif query in name:
        score += 80.0
    elif name in query:
        score += 60.0
    elif _fuzzy_match(query, name):
        score += 40.0
    
    # Aliases match
    aliases = ror_item.get("aliases", [])
    for alias in aliases:
        normalized_alias = normalize_text(alias)
        if query == normalized_alias:
            score += 90.0
            break
        elif query in normalized_alias or normalized_alias in query:
            score += 50.0
            break
        elif _fuzzy_match(query, normalized_alias):
            score += 30.0
            break
    
    # Acronyms match
    acronyms = ror_item.get("acronyms", [])
    for acronym in acronyms:
        normalized_acronym = normalize_text(acronym)
        if query == normalized_acronym:
            score += 95.0
            break
        elif query in normalized_acronym or normalized_acronym in query:
            score += 70.0
            break
    
    # Prefer active status
    if ror_item.get("status") == "active":
        score += 10.0
    
    # Prefer educational institutions
    types = ror_item.get("types", [])
    if "Education" in types:
        score += 5.0
    
    return score


def _fuzzy_match(query: str, text: str, threshold: float = 0.7) -> bool:
    """Simple fuzzy matching based on common words."""
    if not query or not text:
        return False
    
    query_words = set(query.split())
    text_words = set(text.split())
    
    if not query_words or not text_words:
        return False
    
    intersection = query_words.intersection(text_words)
    union = query_words.union(text_words)
    
    return len(intersection) / len(union) >= threshold


async def resolve_institutions(institution_names: List[str]) -> List[Institution]:
    """Resolve multiple institutions concurrently."""
    # logger.info(f"Resolving {len(institution_names)} institutions to ROR IDs")  # Reduced verbosity
    
    tasks = [resolve_institution_to_ror(name) for name in institution_names]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    resolved = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to resolve institution '{institution_names[i]}': {result}")
        elif result is not None:
            resolved.append(result)
            # logger.info(f"Resolved '{institution_names[i]}' to ROR ID: {result.ror_id}")  # Reduced verbosity
        else:
            logger.warning(f"Could not resolve institution: {institution_names[i]}")
    
    return resolved


async def _get_openalex_id_for_ror(client, ror_id: str) -> Optional[str]:
    """Get OpenAlex Institution ID for a given ROR ID."""
    try:
        from core.config import OPENALEX_MAILTO
        
        # Search OpenAlex institutions by ROR ID
        url = f"{API_ENDPOINTS['openalex']}/institutions"
        params = {
            "filter": f"ror:https://ror.org/{ror_id}",
            "per_page": 1,
            "mailto": OPENALEX_MAILTO,
            "select": "id"
        }
        
        response = await cached_get_json(client, url, params)
        
        if response and response.get("results"):
            institution = response["results"][0]
            openalex_id = institution.get("id", "").replace("https://openalex.org/", "")
            if openalex_id:
                logger.info(f"Found OpenAlex ID {openalex_id} for ROR ID {ror_id}")
                return openalex_id
        
        logger.warning(f"No OpenAlex ID found for ROR ID {ror_id}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get OpenAlex ID for ROR {ror_id}: {e}")
        return None