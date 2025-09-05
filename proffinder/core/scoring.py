import math
import logging
from typing import List, Dict, Any
from datetime import datetime

from core.models import AuthorEvidence, ScoreComponents, ExpandedKeywords, Grant
from core.config import WEIGHT_CONCEPT, WEIGHT_WORKS, WEIGHT_GRANT
from util.text import extract_keywords_from_text

logger = logging.getLogger(__name__)


def calculate_author_scores(evidence: AuthorEvidence, 
                          expanded_keywords: ExpandedKeywords) -> ScoreComponents:
    """Calculate comprehensive scores for an author with rationale."""
    
    # Calculate individual score components
    concept_score = score_concepts(evidence, expanded_keywords)
    recent_works_score = score_recent_works(evidence, expanded_keywords)
    grant_score = score_grants(evidence)
    
    # Calculate weighted final score (grants excluded from ranking - too unreliable)
    # Renormalize concept and works weights to sum to 1.0
    concept_weight = WEIGHT_CONCEPT / (WEIGHT_CONCEPT + WEIGHT_WORKS)
    works_weight = WEIGHT_WORKS / (WEIGHT_CONCEPT + WEIGHT_WORKS)
    
    final_score = (
        concept_weight * concept_score +
        works_weight * recent_works_score
        # grant_score excluded from ranking but kept for informational display
    )
    
    # Generate rationale
    rationale = _generate_rationale(
        concept_score, recent_works_score, grant_score, evidence
    )
    
    return ScoreComponents(
        concept_score=concept_score,
        recent_works_score=recent_works_score,
        grant_score=grant_score,
        final_score=final_score,
        rationale=rationale
    )


def score_concepts(evidence: AuthorEvidence, expanded_keywords: ExpandedKeywords) -> float:
    """Score based on overlap between author's topics/concepts and target keywords."""
    if not evidence.profile.primary_topics:
        return 0.0
    
    # Combine all author topics into searchable text
    author_topics_text = " ".join(evidence.profile.primary_topics)
    
    # Find matches with expanded keywords
    matched_concepts = extract_keywords_from_text(author_topics_text, expanded_keywords.all_expanded)
    
    if not matched_concepts:
        return 0.0
    
    # Score based on number and quality of matches
    num_matches = len(matched_concepts)
    total_topics = len(evidence.profile.primary_topics)
    
    # Base score from match ratio
    match_ratio = min(num_matches / max(total_topics, 1), 1.0)
    
    # Bonus for matching original (non-expanded) keywords
    original_matches = extract_keywords_from_text(author_topics_text, expanded_keywords.original)
    original_bonus = len(original_matches) * 0.1  # 10% bonus per original keyword match
    
    # Normalize to [0, 1]
    score = min(match_ratio + original_bonus, 1.0)
    
    return score


def score_recent_works(evidence: AuthorEvidence, expanded_keywords: ExpandedKeywords) -> float:
    """Score based on recent publications matching keywords."""
    if not evidence.recent_publications:
        return 0.0
    
    total_pubs = len(evidence.recent_publications)
    current_year = datetime.now().year
    
    # Calculate score based on matching publications with recency weighting
    weighted_score = 0.0
    total_weight = 0.0
    
    for pub in evidence.recent_publications:
        # Recency weight (more recent = higher weight)
        years_ago = max(current_year - pub.year, 0)
        recency_weight = math.exp(-years_ago * 0.2)  # Exponential decay
        
        # Match score for this publication
        pub_matches = len(pub.matched_keywords)
        if pub_matches > 0:
            # Score based on keyword matches (more matches = better)
            match_score = min(pub_matches / 3.0, 1.0)  # Normalize around 3 matches
            
            # Bonus for original keyword matches
            original_matches = extract_keywords_from_text(
                pub.title, expanded_keywords.original
            )
            if original_matches:
                match_score = min(match_score + 0.3, 1.0)  # 30% bonus
            
            weighted_score += match_score * recency_weight
        
        total_weight += recency_weight
    
    if total_weight == 0:
        return 0.0
    
    # Normalize by total weight
    avg_weighted_score = weighted_score / total_weight
    
    # Adjust based on number of matching publications
    matching_pubs = len([pub for pub in evidence.recent_publications if pub.matched_keywords])
    quantity_factor = min(matching_pubs / 5.0, 1.0)  # Normalize around 5 matching pubs
    
    final_score = avg_weighted_score * (0.7 + 0.3 * quantity_factor)
    
    return min(final_score, 1.0)


def score_grants(evidence: AuthorEvidence) -> float:
    """Score based on active grants."""
    if not evidence.grants:
        return 0.0
    
    active_grants = [g for g in evidence.grants if g.is_active]
    
    if not active_grants:
        # Small score for having any grants (even inactive)
        return min(len(evidence.grants) * 0.05, 0.2)  # Max 0.2 for inactive grants
    
    # Score based on number of active grants
    num_active = len(active_grants)
    
    # Base score from number of active grants
    base_score = min(num_active / 3.0, 0.8)  # Normalize around 3 grants, max 0.8
    
    # Bonus for prestigious funders
    prestigious_funders = {"NIH", "NSF", "DOE", "NASA", "DARPA"}
    prestigious_count = sum(
        1 for grant in active_grants 
        if any(funder in grant.funder for funder in prestigious_funders)
    )
    
    prestige_bonus = min(prestigious_count * 0.1, 0.2)  # Max 20% bonus
    
    final_score = min(base_score + prestige_bonus, 1.0)
    
    return final_score


def _generate_rationale(concept_score: float, works_score: float, 
                       grant_score: float, evidence: AuthorEvidence) -> str:
    """Generate human-readable rationale with specific research details."""
    rationale_parts = []
    
    # 1. SPECIFIC RESEARCH AREAS - What they actually work on
    if evidence.profile.primary_topics:
        main_topics = evidence.profile.primary_topics[:3]  # Top 3 topics
        topic_str = ", ".join(main_topics)
        rationale_parts.append(f"🔬 Research areas: {topic_str}")
    
    # 2. RECENT WORK DETAILS - Specific publications and years
    matching_pubs = [pub for pub in evidence.recent_publications if pub.matched_keywords]
    if matching_pubs:
        # Show most recent publication
        latest_pub = max(matching_pubs, key=lambda p: p.year)
        matched_keywords_str = ", ".join(latest_pub.matched_keywords[:3])  # Top 3 matched keywords
        rationale_parts.append(f"📄 Recent match: '{latest_pub.title[:60]}...' ({latest_pub.year}) - keywords: {matched_keywords_str}")
        
        # Publication activity summary
        recent_years = [pub.year for pub in matching_pubs]
        year_range = f"{min(recent_years)}-{max(recent_years)}" if len(set(recent_years)) > 1 else str(max(recent_years))
        rationale_parts.append(f"📈 {len(matching_pubs)} relevant publications ({year_range})")
    
    # 3. GRANT ACTIVITY - More specific about funding
    active_grants = [g for g in evidence.grants if g.is_active]
    if active_grants:
        funders = list(set([g.funder for g in active_grants]))
        funder_str = ", ".join(funders[:3])  # Top 3 funders
        
        known_grants = [g for g in active_grants if getattr(g, 'confidence', 'unknown') == 'known']
        if known_grants:
            rationale_parts.append(f"💰 Active funding from {funder_str} ({len(known_grants)} confirmed)")
        else:
            rationale_parts.append(f"💰 Likely active funding from {funder_str} ({len(active_grants)} estimated)")
    elif evidence.grants:
        historical_funders = list(set([g.funder for g in evidence.grants]))
        funder_str = ", ".join(historical_funders[:3])
        rationale_parts.append(f"💰 Previous funding from {funder_str}")
    
    # 4. POSITION/DEPARTMENT INFO
    if evidence.profile.current_title and evidence.profile.department:
        rationale_parts.append(f"👤 {evidence.profile.current_title} in {evidence.profile.department}")
    elif evidence.profile.current_title:
        rationale_parts.append(f"👤 {evidence.profile.current_title}")
    elif evidence.profile.department:
        rationale_parts.append(f"🏛️ {evidence.profile.department}")
    
    # 5. RECRUITING STATUS
    if hasattr(evidence, 'recruitment') and evidence.recruitment and evidence.recruitment.is_recruiting:
        rationale_parts.append("🎯 Currently recruiting students")
    
    return " | ".join(rationale_parts)


def rank_authors_by_score(authors_with_scores: List[tuple]) -> List[tuple]:
    """Rank authors by their final scores in descending order."""
    return sorted(authors_with_scores, key=lambda x: x[1].scores.final_score, reverse=True)


def filter_authors_by_threshold(authors_with_scores: List[tuple], 
                               min_score: float = 0.1) -> List[tuple]:
    """Filter authors by minimum score threshold."""
    return [(author, result) for author, result in authors_with_scores 
            if result.scores.final_score >= min_score]