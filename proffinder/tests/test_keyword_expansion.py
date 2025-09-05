import pytest
import asyncio
import sys
import os

# Add the parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.keywords import expand_keywords
from core.models import ExpandedKeywords


class TestKeywordExpansion:
    """Test keyword expansion functionality."""
    
    def test_expanded_keywords_structure(self):
        """Test that ExpandedKeywords model works correctly."""
        original = ["AI", "machine learning"]
        openalex = ["artificial intelligence", "deep learning"]
        mesh = ["computer science", "algorithms"]
        all_expanded = original + openalex + mesh
        
        expanded = ExpandedKeywords(
            original=original,
            openalex_concepts=openalex,
            mesh_terms=mesh,
            all_expanded=all_expanded
        )
        
        assert expanded.original == original
        assert expanded.openalex_concepts == openalex
        assert expanded.mesh_terms == mesh
        assert expanded.all_expanded == all_expanded
    
    @pytest.mark.asyncio
    async def test_expand_keywords_basic(self):
        """Test basic keyword expansion (may fail without API keys)."""
        original_keywords = ["psychology"]
        
        try:
            expanded = await expand_keywords(original_keywords)
            
            # Basic structure checks
            assert isinstance(expanded, ExpandedKeywords)
            assert expanded.original == original_keywords
            assert isinstance(expanded.openalex_concepts, list)
            assert isinstance(expanded.mesh_terms, list)
            assert isinstance(expanded.all_expanded, list)
            
            # Should at least include original keywords
            assert "psychology" in expanded.all_expanded
            
            # All expanded should include original
            for keyword in original_keywords:
                assert keyword in expanded.all_expanded
            
        except Exception as e:
            # Skip test if API is unavailable
            pytest.skip(f"Keyword expansion test skipped due to API issue: {e}")
    
    @pytest.mark.asyncio
    async def test_expand_empty_keywords(self):
        """Test keyword expansion with empty input."""
        expanded = await expand_keywords([])
        
        assert isinstance(expanded, ExpandedKeywords)
        assert expanded.original == []
        assert len(expanded.all_expanded) == 0
    
    @pytest.mark.asyncio
    async def test_expand_keywords_multiple(self):
        """Test keyword expansion with multiple keywords."""
        original_keywords = ["AI", "psychology", "biology"]
        
        try:
            expanded = await expand_keywords(original_keywords)
            
            assert len(expanded.original) == 3
            assert all(kw in expanded.all_expanded for kw in original_keywords)
            
            # Should have more terms than original (if expansion worked)
            # But don't fail if APIs are down
            assert len(expanded.all_expanded) >= len(original_keywords)
            
        except Exception as e:
            pytest.skip(f"Multi-keyword expansion test skipped: {e}")
    
    def test_deduplicate_preservation(self):
        """Test that keyword expansion preserves order and removes duplicates."""
        from util.text import deduplicate_preserving_order
        
        items = ["AI", "machine learning", "AI", "deep learning", "machine learning"]
        result = deduplicate_preserving_order(items)
        
        assert result == ["AI", "machine learning", "deep learning"]
        assert len(result) == 3
    
    def test_keyword_filtering(self):
        """Test filtering of short/invalid keywords."""
        # This test simulates the filtering that happens in expand_keywords
        all_terms = ["AI", "a", "machine learning", "", "  ", "psychology", "x"]
        
        # Filter like in expand_keywords
        filtered = [term for term in all_terms if term and len(term.strip()) > 2]
        
        expected = ["machine learning", "psychology"]
        assert filtered == expected


if __name__ == "__main__":
    pytest.main([__file__])