"""
Grant integration - combine NIH and NSF grant searches.
"""

import asyncio
import logging
from typing import List, Optional

from core.models import AuthorProfile, Grant
from sources.nih import search_nih_grants
from sources.nsf import search_nsf_grants

logger = logging.getLogger(__name__)

async def find_grants_for_authors(authors: List[AuthorProfile]) -> List[AuthorProfile]:
    """Find grants for a list of authors from NIH and NSF."""
    logger.info(f"Searching grants for {len(authors)} authors...")
    
    enriched_authors = []
    
    for author in authors:
        try:
            # Search both NIH and NSF grants (need institution for both)
            grants = []
            
            if author.institution:
                # NIH grants
                try:
                    from sources.nih import search_nih_grants
                    nih_grants = await search_nih_grants(author, author.institution)
                    grants.extend(nih_grants)
                except Exception as e:
                    logger.debug(f"NIH grant search failed for {author.name}: {e}")
                
                # NSF grants  
                try:
                    from sources.nsf import search_nsf_grants
                    nsf_grants = await search_nsf_grants(author, author.institution)
                    grants.extend(nsf_grants)
                except Exception as e:
                    logger.debug(f"NSF grant search failed for {author.name}: {e}")
            else:
                logger.debug(f"No institution for {author.name}, skipping grant search")
            
            # Store grants directly on author
            author.grants = grants
            enriched_authors.append(author)
            
            if grants:
                logger.info(f"Found {len(grants)} grants for {author.name}")
            
        except Exception as e:
            logger.warning(f"Grant search failed for {author.name}: {e}")
            enriched_authors.append(author)  # Include anyway
    
    return enriched_authors

async def find_grants_for_author(author: AuthorProfile) -> List[Grant]:
    """Find grants for a single author."""
    results = await find_grants_for_authors([author])
    if results and hasattr(results[0], 'evidence') and results[0].evidence:
        return results[0].evidence.grants
    return []