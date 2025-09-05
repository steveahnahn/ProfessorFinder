import pytest
from datetime import datetime
import sys
import os

# Add the parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    AuthorProfile, AuthorEvidence, Institution, Publication, Grant, 
    RecruitmentSignal, ExpandedKeywords
)
from core.scoring import (
    calculate_author_scores, score_concepts, score_recent_works, score_grants
)


@pytest.fixture
def sample_institution():
    return Institution(
        name="Test University",
        ror_id="12345",
        display_name="Test University",
        country="USA"
    )


@pytest.fixture
def sample_author(sample_institution):
    return AuthorProfile(
        openalex_id="A123456789",
        name="Dr. Jane Smith",
        orcid_id="0000-0000-0000-0000",
        current_title="Professor",
        department="Computer Science",
        homepage_url="https://example.com",
        primary_topics=["machine learning", "artificial intelligence", "data science"],
        institution=sample_institution
    )


@pytest.fixture
def sample_keywords():
    return ExpandedKeywords(
        original=["AI", "machine learning"],
        openalex_concepts=["artificial intelligence", "deep learning", "neural networks"],
        mesh_terms=["artificial intelligence", "computer science"],
        all_expanded=["AI", "machine learning", "artificial intelligence", "deep learning", "neural networks", "computer science"]
    )


@pytest.fixture
def sample_publications():
    current_year = datetime.now().year
    return [
        Publication(
            id="P1",
            title="Deep Learning for Healthcare",
            year=current_year,
            url="https://example.com/paper1",
            matched_keywords=["machine learning", "deep learning"]
        ),
        Publication(
            id="P2", 
            title="AI in Education",
            year=current_year - 1,
            url="https://example.com/paper2",
            matched_keywords=["artificial intelligence", "AI"]
        )
    ]


@pytest.fixture
def sample_grants():
    return [
        Grant(
            id="NSF-123",
            title="Machine Learning for Climate Modeling",
            funder="NSF",
            start_date="2023-01-01",
            end_date="2026-12-31",
            is_active=True,
            url="https://nsf.gov/award/123",
            pi_names=["Dr. Jane Smith"]
        ),
        Grant(
            id="NIH-456",
            title="AI for Medical Diagnosis",
            funder="NIH",
            start_date="2020-01-01", 
            end_date="2023-12-31",
            is_active=False,
            url="https://nih.gov/award/456",
            pi_names=["Dr. Jane Smith"]
        )
    ]


def test_score_concepts_perfect_match(sample_author, sample_keywords):
    """Test concept scoring with perfect topic match."""
    evidence = AuthorEvidence(profile=sample_author, matched_keywords=sample_keywords.all_expanded)
    score = score_concepts(evidence, sample_keywords)
    
    assert score > 0.5  # Should be high since topics match well
    assert score <= 1.0  # Should not exceed 1.0


def test_score_concepts_no_match(sample_institution, sample_keywords):
    """Test concept scoring with no topic match."""
    author = AuthorProfile(
        openalex_id="A999",
        name="Dr. Bob Jones", 
        primary_topics=["biology", "genetics", "molecular science"],
        institution=sample_institution
    )
    evidence = AuthorEvidence(profile=author, matched_keywords=sample_keywords.all_expanded)
    score = score_concepts(evidence, sample_keywords)
    
    assert score == 0.0  # No matching topics


def test_score_recent_works(sample_author, sample_publications, sample_keywords):
    """Test recent works scoring."""
    evidence = AuthorEvidence(
        profile=sample_author,
        recent_publications=sample_publications,
        matched_keywords=sample_keywords.all_expanded
    )
    score = score_recent_works(evidence, sample_keywords)
    
    assert score > 0.0  # Should have some score due to matching publications
    assert score <= 1.0


def test_score_recent_works_no_publications(sample_author, sample_keywords):
    """Test recent works scoring with no publications."""
    evidence = AuthorEvidence(profile=sample_author, matched_keywords=sample_keywords.all_expanded)
    score = score_recent_works(evidence, sample_keywords)
    
    assert score == 0.0


def test_score_grants_with_active(sample_author, sample_grants, sample_keywords):
    """Test grant scoring with active grants."""
    evidence = AuthorEvidence(
        profile=sample_author,
        grants=sample_grants,
        matched_keywords=sample_keywords.all_expanded
    )
    score = score_grants(evidence)
    
    assert score > 0.0  # Should have positive score due to active grant
    assert score <= 1.0


def test_score_grants_no_grants(sample_author, sample_keywords):
    """Test grant scoring with no grants."""
    evidence = AuthorEvidence(profile=sample_author, matched_keywords=sample_keywords.all_expanded)
    score = score_grants(evidence)
    
    assert score == 0.0


def test_calculate_author_scores_complete(sample_author, sample_publications, sample_grants, sample_keywords):
    """Test complete author scoring with all components."""
    recruitment = RecruitmentSignal(is_recruiting=True, snippet="We are hiring PhD students", url="https://example.com")
    
    evidence = AuthorEvidence(
        profile=sample_author,
        recent_publications=sample_publications,
        grants=sample_grants,
        recruitment=recruitment,
        matched_keywords=sample_keywords.all_expanded
    )
    
    scores = calculate_author_scores(evidence, sample_keywords)
    
    # Check all score components exist and are in valid range
    assert 0 <= scores.concept_score <= 1.0
    assert 0 <= scores.recent_works_score <= 1.0 
    assert 0 <= scores.grant_score <= 1.0
    assert 0 <= scores.final_score <= 1.0
    
    # Final score should be weighted combination
    expected_final = (0.5 * scores.concept_score + 
                     0.3 * scores.recent_works_score + 
                     0.2 * scores.grant_score)
    assert abs(scores.final_score - expected_final) < 0.001
    
    # Rationale should exist
    assert scores.rationale
    assert isinstance(scores.rationale, str)
    assert len(scores.rationale) > 0


if __name__ == "__main__":
    pytest.main([__file__])