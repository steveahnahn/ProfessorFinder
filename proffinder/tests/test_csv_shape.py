import pytest
import sys
import os
from datetime import datetime

# Add the parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    AuthorProfile, AuthorEvidence, AuthorResult, Institution, 
    Publication, Grant, RecruitmentSignal, ScoreComponents
)
from core.csvio import (
    convert_results_to_csv_rows, write_csv_to_string, validate_csv_structure
)


@pytest.fixture
def sample_result():
    """Create a sample AuthorResult for testing."""
    institution = Institution(
        name="Test University",
        ror_id="12345",
        display_name="Test University",
        country="USA"
    )
    
    author = AuthorProfile(
        openalex_id="A123456789",
        name="Dr. Jane Smith",
        orcid_id="0000-0000-0000-0000",
        current_title="Professor",
        department="Computer Science",
        homepage_url="https://example.com",
        primary_topics=["AI", "machine learning"],
        institution=institution
    )
    
    publications = [
        Publication(
            id="P1",
            title="Deep Learning Methods",
            year=2023,
            url="https://example.com/paper1",
            matched_keywords=["AI", "deep learning"]
        )
    ]
    
    grants = [
        Grant(
            id="NSF-123",
            title="AI Research Grant",
            funder="NSF",
            start_date="2023-01-01",
            end_date="2026-12-31",
            is_active=True,
            url="https://nsf.gov/award/123",
            pi_names=["Dr. Jane Smith"]
        )
    ]
    
    recruitment = RecruitmentSignal(
        is_recruiting=True,
        snippet="We are hiring PhD students",
        url="https://example.com/jobs"
    )
    
    evidence = AuthorEvidence(
        profile=author,
        recent_publications=publications,
        grants=grants,
        recruitment=recruitment,
        matched_keywords=["AI", "machine learning", "deep learning"],
        evidence_urls=[
            "https://openalex.org/A123456789",
            "https://orcid.org/0000-0000-0000-0000",
            "https://example.com"
        ],
        sources_used=["OpenAlex", "ORCID", "NSF"],
        last_seen_utc=datetime.utcnow()
    )
    
    scores = ScoreComponents(
        concept_score=0.8,
        recent_works_score=0.7,
        grant_score=0.6,
        final_score=0.74,
        rationale="Strong topic match; relevant recent work; good funding"
    )
    
    return AuthorResult(evidence=evidence, scores=scores)


class TestCSVExport:
    """Test CSV export functionality."""
    
    def test_convert_results_to_csv_rows(self, sample_result):
        """Test conversion of results to CSV rows."""
        results = [sample_result]
        csv_rows = convert_results_to_csv_rows(results)
        
        assert len(csv_rows) == 1
        row = csv_rows[0]
        
        # Test required fields
        assert row.author_name == "Dr. Jane Smith"
        assert row.openalex_id == "A123456789"
        assert row.institution_name == "Test University"
        assert row.institution_ror == "12345"
        
        # Test ORCID
        assert row.orcid_id == "0000-0000-0000-0000"
        
        # Test employment info
        assert row.current_title == "Professor"
        assert row.department == "Computer Science"
        
        # Test scores (should be rounded to 3 decimal places)
        assert row.concept_score == 0.8
        assert row.recent_works_score == 0.7
        assert row.grant_score == 0.6
        assert row.final_score == 0.74
        
        # Test boolean fields
        assert row.is_recruiting is True
        
        # Test counts
        assert row.recent_pubs_count == 1
        assert row.active_grants_count == 1
    
    def test_csv_column_order(self, sample_result):
        """Test that CSV columns are in the correct order."""
        results = [sample_result]
        csv_string = write_csv_to_string(convert_results_to_csv_rows(results))
        
        lines = csv_string.strip().split('\n')
        header = lines[0]
        
        # Expected column order from specification
        expected_columns = [
            'institution_name', 'institution_ror',
            'author_name', 'openalex_id', 'orcid_id',
            'current_title', 'department',
            'homepage_url',
            'primary_topics_or_concepts',
            'matched_keywords',
            'recent_pubs_count', 'example_pub_titles',
            'active_grants_count', 'funders', 'grant_ids', 'grant_urls',
            'is_recruiting', 'recruiting_snippet', 'recruiting_url',
            'concept_score', 'recent_works_score', 'grant_score', 'final_score',
            'evidence_urls',
            'last_seen_utc', 'sources_used'
        ]
        
        actual_columns = [col.strip() for col in header.split(',')]
        assert actual_columns == expected_columns
    
    def test_semicolon_separation(self, sample_result):
        """Test that multi-value fields use semicolon separation."""
        results = [sample_result]
        csv_rows = convert_results_to_csv_rows(results)
        row = csv_rows[0]
        
        # Test topics separation
        assert ";" in row.primary_topics_or_concepts or len(sample_result.evidence.profile.primary_topics) == 1
        
        # Test keywords separation
        assert ";" in row.matched_keywords or len(sample_result.evidence.matched_keywords) == 1
        
        # Test evidence URLs separation
        assert ";" in row.evidence_urls or len(sample_result.evidence.evidence_urls) == 1
        
        # Test sources separation
        assert ";" in row.sources_used or len(sample_result.evidence.sources_used) == 1
    
    def test_validate_csv_structure(self, sample_result):
        """Test CSV structure validation."""
        results = [sample_result]
        csv_rows = convert_results_to_csv_rows(results)
        
        validation = validate_csv_structure(csv_rows)
        
        assert validation["valid"] is True
        assert validation["total_rows"] == 1
        assert validation["authors_with_orcid"] == 1
        assert validation["authors_recruiting"] == 1
        assert validation["authors_with_active_grants"] == 1
        assert len(validation["missing_data"]) == 0
        assert len(validation["url_issues"]) == 0
    
    def test_empty_results(self):
        """Test handling of empty results."""
        csv_rows = convert_results_to_csv_rows([])
        assert len(csv_rows) == 0
        
        validation = validate_csv_structure(csv_rows)
        assert validation["valid"] is False
        assert "No data to validate" in validation["error"]
    
    def test_csv_string_format(self, sample_result):
        """Test that CSV string is properly formatted."""
        results = [sample_result]
        csv_string = write_csv_to_string(convert_results_to_csv_rows(results))
        
        lines = csv_string.strip().split('\n')
        
        # Should have header + 1 data row
        assert len(lines) == 2
        
        # Each line should have the same number of fields
        header_fields = len(lines[0].split(','))
        data_fields = len(lines[1].split(','))
        assert header_fields == data_fields
        
        # Should have 27 columns as specified
        assert header_fields == 27
    
    def test_evidence_urls_format(self, sample_result):
        """Test that evidence URLs are properly formatted."""
        results = [sample_result]
        csv_rows = convert_results_to_csv_rows(results)
        row = csv_rows[0]
        
        urls = row.evidence_urls.split(';')
        for url in urls:
            url = url.strip()
            if url:  # Skip empty URLs
                assert url.startswith('http://') or url.startswith('https://')


if __name__ == "__main__":
    pytest.main([__file__])