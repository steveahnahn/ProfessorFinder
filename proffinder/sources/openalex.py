import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from core.models import Institution, AuthorProfile, Publication, ExpandedKeywords
from core.config import API_ENDPOINTS, OPENALEX_MAILTO
from core.cache import cached_get_json
from util.http import get_client
from util.text import extract_keywords_from_text, deduplicate_preserving_order

logger = logging.getLogger(__name__)


async def find_authors_by_institution(institution: Institution, 
                                    expanded_keywords: ExpandedKeywords,
                                    years_window: int = 5) -> List[AuthorProfile]:
    """Find authors associated with an institution."""
    import os
    
    client = get_client()
    authors = []
    
    try:
        # Method 1: Direct author search by institution
        institution_authors = await _search_authors_by_institution(
            client, institution, expanded_keywords, years_window
        )
        authors.extend(institution_authors)
        
        # Method 2: Find authors through their works at the institution
        # Skip if in simple mode to reduce API calls
        simple_mode = os.getenv("SIMPLE_MODE", "false").lower() == "true"
        if not simple_mode:
            works_authors = await _search_authors_through_works(
                client, institution, expanded_keywords, years_window
            )
            authors.extend(works_authors)
        else:
            # logger.info(f"Skipping works-based search for {institution.display_name} (SIMPLE_MODE=true)")  # Reduced verbosity
            pass  # Skip works-based search in simple mode
        
        # Deduplicate by OpenAlex ID
        unique_authors = _deduplicate_authors(authors)
        
        # NEW: Score and rank all authors instead of arbitrary filtering
        from core.scoring import calculate_author_scores
        from core.models import AuthorEvidence
        
        # Skip grant search entirely - grants are not used in ranking
        # (See core/scoring.py line 22: grants excluded from ranking as too unreliable)
        authors_with_grants = unique_authors
        logger.info(f"Skipping grant search for {len(unique_authors)} authors - grants not used in ranking")
        
        scored_authors = []
        for author in authors_with_grants:
            # Apply final filtering check to ensure no unqualified authors slip through
            if not _author_matches_keywords(author, expanded_keywords):
                logger.debug(f"Final filter: excluding {author.name}")
                continue
                
            # Create evidence object with grants (if available)
            # Ensure data types are properly converted for Pydantic validation
            try:
                evidence = AuthorEvidence(
                    profile=author,
                    recent_publications=author.recent_publications if hasattr(author, 'recent_publications') and author.recent_publications else [],
                    grants=author.grants if hasattr(author, 'grants') and author.grants else [],
                    matched_keywords=expanded_keywords.original
                )
            except Exception as e:
                logger.error(f"Failed to create AuthorEvidence for {author.name}: {e}")
                continue
            
            # Calculate comprehensive score
            scores = calculate_author_scores(evidence, expanded_keywords)
            
            scored_authors.append((author, scores, evidence))
        
        # Step 2: Sort by score and take top candidates
        scored_authors.sort(key=lambda x: x[1].final_score, reverse=True)
        
        # Step 3: Return top-scoring authors (quality-based limit)
        top_count = min(25, len(scored_authors))  # Top 25 or all if fewer
        min_score_threshold = 0.05  # Lower threshold for testing
        
        top_authors = []
        for author, scores, evidence in scored_authors[:top_count]:
            if scores.final_score >= min_score_threshold:
                # Add scoring info to author for display
                author.scores = scores
                author.evidence = evidence
                top_authors.append(author)
        
        # Only log summary if authors found, reduce noise
        if len(top_authors) > 0:
            logger.warning(f"Found {len(top_authors)} top authors at {institution.display_name}")
        return top_authors
        
    except Exception as e:
        logger.error(f"Author search failed for {institution.display_name}: {e}")
        return []


async def _search_authors_by_institution(client, institution: Institution, 
                                       expanded_keywords: ExpandedKeywords,
                                       years_window: int) -> List[AuthorProfile]:
    """Search authors directly by institution affiliation."""
    authors = []
    cursor = "*"
    
    page_count = 0
    # Cast wider net initially - we'll score and filter later
    while cursor and page_count < 5:  # Get more candidates for scoring
        try:
            # Use OpenAlex Institution ID if available, fallback to ROR ID
            institution_filter = None
            if institution.openalex_id:
                institution_filter = f"last_known_institutions.id:https://openalex.org/{institution.openalex_id}"
            else:
                institution_filter = f"last_known_institutions.id:https://ror.org/{institution.ror_id}"
                logger.warning(f"No OpenAlex ID for {institution.display_name}, using ROR ID")
                
            params = {
                "filter": institution_filter,
                "per_page": 50,  # Smaller page size
                "cursor": cursor,
                "mailto": OPENALEX_MAILTO,
                "select": "id,display_name,orcid,last_known_institutions,x_concepts,topics,works_count"
            }
            
            # logger.info(f"Searching authors at {institution.display_name} (page {page_count + 1})")  # Reduced verbosity
            response = await cached_get_json(
                client, 
                f"{API_ENDPOINTS['openalex']}/authors",
                params
            )
            page_count += 1
            
            if not response or "results" not in response:
                logger.warning(f"No response or results for {institution.display_name}")
                break
            
            results_count = len(response.get("results", []))
            # logger.info(f"OpenAlex returned {results_count} raw authors for {institution.display_name}")  # Reduced verbosity
                
            for author_data in response["results"]:
                author = _parse_author_profile(author_data, institution)
                if author:
                    logger.debug(f"Parsed author: {author.name} with topics: {author.primary_topics}")
                    if _author_matches_keywords(author, expanded_keywords):
                        # Enrich with recent works
                        await _enrich_author_with_recent_works(
                            client, author, expanded_keywords, years_window
                        )
                        authors.append(author)
                        # logger.info(f"Added author: {author.name}")  # Reduced verbosity
                    else:
                        logger.debug(f"Author {author.name} filtered out by keywords")
                else:
                    logger.debug("Failed to parse author data")
            
            # Get next cursor
            cursor = response.get("meta", {}).get("next_cursor")
            if not cursor:
                break
                
            # Add delay between requests to avoid rate limiting
            await asyncio.sleep(1)
            
            # Stop if we have a reasonable candidate pool for scoring
            if len(authors) >= 200:  # Larger pool for better scoring
                # logger.info(f"Collected sufficient candidates ({len(authors)}) for scoring at {institution.display_name}")  # Reduced verbosity
                break
                
        except Exception as e:
            logger.warning(f"Author search page failed: {e}")
            break
    
    return authors


async def _search_authors_through_works(client, institution: Institution, 
                                      expanded_keywords: ExpandedKeywords,
                                      years_window: int) -> List[AuthorProfile]:
    """Find authors by searching their works at the institution."""
    authors = []
    current_year = datetime.now().year
    from_year = current_year - years_window
    
    # Search works by institution and keywords - limit to prevent rate limiting
    keyword_batches = _batch_keywords(expanded_keywords.all_expanded, batch_size=3)[:5]  # Only first 5 batches
    for keyword_batch in keyword_batches:
        try:
            keyword_query = " OR ".join([f'"{kw}"' for kw in keyword_batch])
            
            # Use OpenAlex Institution ID if available, fallback to ROR ID
            institution_filter = None
            if institution.openalex_id:
                institution_filter = f"institutions.id:https://openalex.org/{institution.openalex_id}"
            else:
                institution_filter = f"institutions.id:https://ror.org/{institution.ror_id}"
                logger.warning(f"No OpenAlex ID for works search at {institution.display_name}, using ROR ID")
            
            params = {
                "filter": f"{institution_filter},publication_year:{from_year}-{current_year}",
                "search": keyword_query,
                "per_page": 200,
                "mailto": OPENALEX_MAILTO,
                "select": "id,title,publication_year,authorships,doi,topics,concepts"
            }
            
            response = await cached_get_json(
                client,
                f"{API_ENDPOINTS['openalex']}/works",
                params
            )
            
            if response and "results" in response:
                for work in response["results"]:
                    work_authors = _extract_authors_from_work(work, institution)
                    # Apply the same keyword filtering to works-based authors
                    for author in work_authors:
                        if _author_matches_keywords(author, expanded_keywords):
                            authors.append(author)
                            logger.debug(f"Added works-based author: {author.name}")
                        else:
                            logger.debug(f"Works-based author {author.name} filtered out by keywords")
                    
        except Exception as e:
            logger.warning(f"Works search failed for keywords {keyword_batch}: {e}")
        
        # Add delay between keyword batch requests
        await asyncio.sleep(2)
    
    return authors


def _parse_author_profile(author_data: Dict[str, Any], institution: Institution) -> Optional[AuthorProfile]:
    """Parse OpenAlex author data into AuthorProfile."""
    try:
        openalex_id = author_data.get("id", "").replace("https://openalex.org/", "")
        if not openalex_id:
            return None
        
        name = author_data.get("display_name", "")
        if not name:
            return None
        
        orcid_id = author_data.get("orcid")
        if orcid_id:
            orcid_id = orcid_id.replace("https://orcid.org/", "")
        
        # Extract topics/concepts
        topics = []
        x_concepts = author_data.get("x_concepts", [])
        for concept in x_concepts[:10]:  # Top 10 concepts
            if concept.get("display_name"):
                topics.append(concept["display_name"])
        
        # Also get topics if available
        author_topics = author_data.get("topics", [])
        for topic in author_topics[:10]:  # Top 10 topics
            if topic.get("display_name"):
                topics.append(topic["display_name"])
        
        topics = deduplicate_preserving_order(topics)
        
        return AuthorProfile(
            openalex_id=openalex_id,
            name=name,
            orcid_id=orcid_id,
            primary_topics=topics,
            institution=institution
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse author data: {e}")
        return None


def _extract_authors_from_work(work: Dict[str, Any], institution: Institution) -> List[AuthorProfile]:
    """Extract author profiles from a work's authorship data."""
    authors = []
    
    authorships = work.get("authorships", [])
    for authorship in authorships:
        # Check if this authorship is from our target institution
        institutions = authorship.get("institutions", [])
        institution_match = False
        
        for inst in institutions:
            inst_id = inst.get("id", "")
            # Check OpenAlex ID first, fallback to ROR ID
            if institution.openalex_id and f"openalex.org/{institution.openalex_id}" in inst_id:
                institution_match = True
                break
            elif f"ror.org/{institution.ror_id}" in inst_id:
                institution_match = True
                break
        
        if not institution_match:
            continue
        
        author = authorship.get("author", {})
        if not author:
            continue
        
        author_profile = _parse_author_profile(author, institution)
        if author_profile:
            authors.append(author_profile)
    
    return authors


async def _enrich_author_with_recent_works(client, author: AuthorProfile, 
                                         expanded_keywords: ExpandedKeywords,
                                         years_window: int) -> None:
    """Enrich author profile with recent matching works."""
    try:
        current_year = datetime.now().year
        from_year = current_year - years_window
        
        params = {
            "filter": f"author.id:https://openalex.org/{author.openalex_id},"
                     f"publication_year:{from_year}-{current_year}",
            "per_page": 50,
            "mailto": OPENALEX_MAILTO,
            "select": "id,title,publication_year,doi,abstract_inverted_index,topics,concepts"
        }
        
        response = await cached_get_json(
            client,
            f"{API_ENDPOINTS['openalex']}/works",
            params
        )
        
        if response and "results" in response:
            recent_works = []
            for work in response["results"]:
                pub = _parse_publication(work, expanded_keywords)
                if pub:
                    recent_works.append(pub)
            
            # Store works info in the author profile (we'll need this for scoring)
            author.recent_publications = recent_works
            
    except Exception as e:
        logger.warning(f"Failed to enrich author {author.name} with recent works: {e}")


def _parse_publication(work: Dict[str, Any], expanded_keywords: ExpandedKeywords) -> Optional[Publication]:
    """Parse OpenAlex work into Publication model."""
    try:
        openalex_id = work.get("id", "").replace("https://openalex.org/", "")
        title = work.get("title", "")
        year = work.get("publication_year")
        doi = work.get("doi")
        
        if not openalex_id or not title:
            return None
        
        # Reconstruct abstract from inverted index
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index", {}))
        
        # Find matching keywords in title, abstract, concepts, topics
        matched_keywords = []
        search_text = f"{title} {abstract}".lower()
        
        # Check concepts and topics
        concepts = work.get("concepts", [])
        topics = work.get("topics", [])
        
        all_work_terms = [title, abstract]
        for concept in concepts:
            if concept.get("display_name"):
                all_work_terms.append(concept["display_name"])
        for topic in topics:
            if topic.get("display_name"):
                all_work_terms.append(topic["display_name"])
        
        work_text = " ".join(all_work_terms).lower()
        matched_keywords = extract_keywords_from_text(work_text, expanded_keywords.all_expanded)
        
        return Publication(
            id=openalex_id,
            title=title,
            year=year or datetime.now().year,
            doi=doi,
            url=f"https://openalex.org/{openalex_id}",
            matched_keywords=matched_keywords
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse publication: {e}")
        return None


def _reconstruct_abstract(inverted_index: Dict[str, List[int]]) -> str:
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inverted_index:
        return ""
    
    try:
        # Create list of (position, word) pairs
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        # Sort by position and join
        word_positions.sort(key=lambda x: x[0])
        return " ".join([word for _, word in word_positions])
        
    except Exception:
        return ""


def _author_matches_keywords(author: AuthorProfile, expanded_keywords: ExpandedKeywords) -> bool:
    """Check if author matches keywords AND is likely a good graduate advisor."""
    import os
    
    # Step 1: Keyword matching (make this more restrictive for advisor search)
    if not author.primary_topics:
        return False  # Skip authors without research topics
    
    # Disable keyword filter only for debugging
    if os.getenv("DISABLE_KEYWORD_FILTER", "false").lower() == "true":
        return True
    
    # Step 1: Keyword matching for graduate advisor candidates
    # USER'S ORIGINAL KEYWORDS are the primary filter - no hardcoded exclusions
    
    author_text = " ".join(author.primary_topics).lower()
    
    # PRIORITY SYSTEM: Original keywords matter most
    
    # Count matches for ORIGINAL keywords (user's specific intent)
    # Use word boundary matching to avoid false positives
    import re
    author_words = set(re.findall(r'\b\w+\b', author_text))
    
    original_matches = 0
    for keyword in expanded_keywords.original:
        keyword_words = set(re.findall(r'\b\w+\b', keyword.lower()))
        # Count if ANY word from the keyword phrase appears in author topics
        if keyword_words.intersection(author_words):
            original_matches += 1
    
    # Count matches for EXPANDED keywords (broader discovery) 
    expanded_matches = 0
    for keyword in expanded_keywords.all_expanded:
        keyword_words = set(re.findall(r'\b\w+\b', keyword.lower()))
        if keyword_words.intersection(author_words):
            expanded_matches += 1
    
    # SIMPLIFIED FILTERING RULES - USER'S ORIGINAL KEYWORDS ARE KING:
    
    # Rule 1: MUST match a high percentage of original keywords
    required_original_matches = max(1, int(len(expanded_keywords.original) * 0.75))  # 75% of original keywords
    if original_matches < required_original_matches:
        logger.debug(f"Excluding {author.name}: only {original_matches}/{len(expanded_keywords.original)} original keyword matches (need {required_original_matches})")
        return False
    
    # Rule 2: Expanded keywords are just a bonus - only require basic coverage  
    if len(expanded_keywords.all_expanded) > 0:
        min_expanded_ratio = 0.15  # Just 15% of expanded terms needed
        if (expanded_matches / len(expanded_keywords.all_expanded)) < min_expanded_ratio:
            logger.debug(f"Excluding {author.name}: low expanded keyword coverage ({expanded_matches}/{len(expanded_keywords.all_expanded)} = {expanded_matches/len(expanded_keywords.all_expanded):.1%})")
            return False
    
    # TODO: Add advisor-specific filters here:
    # - Active grants (indicates capacity)
    # - Recent PhD students (indicates mentorship)  
    # - Career stage (not too junior, not retiring)
    # - Lab website signals (will be checked separately)
    
    return True


def _deduplicate_authors(authors: List[AuthorProfile]) -> List[AuthorProfile]:
    """Remove duplicate authors by OpenAlex ID."""
    seen_ids = set()
    unique_authors = []
    
    for author in authors:
        if author.openalex_id not in seen_ids:
            seen_ids.add(author.openalex_id)
            unique_authors.append(author)
    
    return unique_authors


def _batch_keywords(keywords: List[str], batch_size: int = 3) -> List[List[str]]:
    """Batch keywords for API calls."""
    batches = []
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        if batch:
            batches.append(batch)
    return batches