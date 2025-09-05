import asyncio
import logging
import os
from typing import List, Set, Dict, Any
import xml.etree.ElementTree as ET

from core.models import ExpandedKeywords
from core.config import API_ENDPOINTS, NCBI_API_KEY
from core.cache import cached_get_json, cached_get_text
from util.http import get_client
from util.text import deduplicate_preserving_order, normalize_text

logger = logging.getLogger(__name__)


async def expand_keywords_openalex(keywords: List[str]) -> List[str]:
    """Expand keywords using OpenAlex Concepts/Topics API."""
    client = get_client()
    expanded = []
    
    for keyword in keywords:
        concept_url = f"{API_ENDPOINTS['openalex']}/concepts"
        params = {
            "search": keyword,
            "per_page": 10
        }
        
        try:
            response = await cached_get_json(client, concept_url, params)
            if response and "results" in response:
                for concept in response["results"]:
                    # Add the concept display name
                    display_name = concept.get("display_name", "")
                    if display_name:
                        expanded.append(display_name)
                    
                    # Add related concepts
                    related_concepts = concept.get("related_concepts", [])
                    for related in related_concepts[:3]:  # Limit to top 3
                        related_name = related.get("display_name", "")
                        if related_name:
                            expanded.append(related_name)
                    
                    # Add ancestors/children if available
                    ancestors = concept.get("ancestors", [])
                    for ancestor in ancestors[:2]:  # Limit to top 2
                        ancestor_name = ancestor.get("display_name", "")
                        if ancestor_name:
                            expanded.append(ancestor_name)
                        
        except Exception as e:
            logger.warning(f"OpenAlex concept expansion failed for '{keyword}': {e}")
    
    return deduplicate_preserving_order(expanded)


async def expand_keywords_mesh(keywords: List[str]) -> List[str]:
    """Expand keywords using PubMed/MeSH API."""
    client = get_client()
    expanded = []
    
    for keyword in keywords:
        try:
            # Search for MeSH terms
            search_params = {
                "db": "mesh",
                "term": keyword,
                "retmax": 5,
                "retmode": "json",  # Explicitly request JSON
                "usehistory": "n"
            }
            if NCBI_API_KEY:
                search_params["api_key"] = NCBI_API_KEY
            
            search_response = await cached_get_json(
                client, 
                API_ENDPOINTS["ncbi_esearch"], 
                search_params
            )
            
            if search_response and "esearchresult" in search_response:
                id_list = search_response["esearchresult"].get("idlist", [])
                
                if id_list:
                    # Fetch detailed MeSH records
                    fetch_params = {
                        "db": "mesh",
                        "id": ",".join(id_list),
                        "rettype": "xml",
                        "retmode": "xml"
                    }
                    if NCBI_API_KEY:
                        fetch_params["api_key"] = NCBI_API_KEY
                    
                    mesh_xml = await cached_get_text(
                        client,
                        API_ENDPOINTS["ncbi_efetch"],
                        fetch_params
                    )
                    
                    if mesh_xml:
                        expanded.extend(_parse_mesh_xml(mesh_xml))
                        
        except Exception as e:
            logger.debug(f"MeSH expansion failed for '{keyword}': {e}")
            # Continue with other keywords - MeSH is optional enhancement
    
    return deduplicate_preserving_order(expanded)


def _parse_mesh_xml(xml_content: str) -> List[str]:
    """Parse MeSH XML to extract entry terms and synonyms."""
    terms = []
    try:
        root = ET.fromstring(xml_content)
        
        for descriptor in root.findall(".//DescriptorRecord"):
            # Main heading
            descriptor_name = descriptor.find(".//DescriptorName/String")
            if descriptor_name is not None and descriptor_name.text:
                terms.append(descriptor_name.text)
            
            # Entry terms (synonyms)
            for concept in descriptor.findall(".//Concept"):
                for term in concept.findall(".//Term"):
                    term_string = term.find("String")
                    if term_string is not None and term_string.text:
                        terms.append(term_string.text)
                        
    except ET.ParseError as e:
        logger.warning(f"Failed to parse MeSH XML: {e}")
    
    return terms


async def expand_keywords(original_keywords: List[str]) -> ExpandedKeywords:
    """Expand keywords using both OpenAlex and MeSH."""
    logger.info(f"Expanding keywords: {original_keywords}")
    
    # Run both expansions concurrently
    openalex_task = expand_keywords_openalex(original_keywords)
    
    # Skip MeSH for now if causing issues
    skip_mesh = os.getenv("SKIP_MESH", "false").lower() == "true"
    
    if skip_mesh:
        openalex_concepts = await openalex_task
        mesh_terms = []
        logger.info("Skipping MeSH expansion (SKIP_MESH=true)")
    else:
        mesh_task = expand_keywords_mesh(original_keywords)
        openalex_concepts, mesh_terms = await asyncio.gather(
            openalex_task, mesh_task, return_exceptions=True
        )
    
    # Handle exceptions
    if isinstance(openalex_concepts, Exception):
        logger.error(f"OpenAlex expansion failed: {openalex_concepts}")
        openalex_concepts = []
    if isinstance(mesh_terms, Exception):
        logger.error(f"MeSH expansion failed: {mesh_terms}")
        mesh_terms = []
    
    # Combine all terms
    all_terms = original_keywords + openalex_concepts + mesh_terms
    all_expanded = deduplicate_preserving_order([
        term for term in all_terms if term and len(term.strip()) > 2
    ])
    
    logger.info(f"Expanded {len(original_keywords)} keywords to {len(all_expanded)} terms")
    
    return ExpandedKeywords(
        original=original_keywords,
        openalex_concepts=openalex_concepts,
        mesh_terms=mesh_terms,
        all_expanded=all_expanded
    )