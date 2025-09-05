import asyncio
import streamlit as st
import pandas as pd
import logging
from typing import List, Optional
from datetime import datetime

# Configure logging - show important info but reduce noise
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language support
from lang import get_text

# Core imports
from core.models import SearchRequest, AuthorResult, AuthorEvidence, RecruitmentSignal
from core.keywords import expand_keywords
from core.scoring import calculate_author_scores, rank_authors_by_score
from core.csvio import convert_results_to_csv_rows, write_csv_to_string, create_csv_download
from core.config import DEFAULT_YEARS_WINDOW
from core.universities import (
    CURATED_UNIVERSITIES, get_universities_by_region, 
    get_psychology_sociology_top_programs, get_international_friendly_universities,
    get_northeast_universities, get_southeast_universities, get_midwest_universities,
    get_southwest_universities, get_west_universities
)

# Source imports
from sources.ror import resolve_institutions
from sources.openalex import find_authors_by_institution
from sources.orcid import enrich_authors_with_orcid
from sources.nih import search_grants_for_authors
from sources.nsf import search_nsf_grants_for_authors
from sources.recruit import detect_recruitment_signals

# Utility imports
from util.http import close_client


st.set_page_config(
    page_title="Professor Finder - Graduate Advisor Discovery",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def main():
    # Initialize session state for language
    if "language" not in st.session_state:
        st.session_state.language = "en"
    
    # Add custom CSS for fun, engaging design
    st.markdown("""
    <style>
        /* Main layout with fun background */
        .main > div {
            padding-top: 1rem;
            max-width: 900px;
            margin: 0 auto;
            background: linear-gradient(135deg, #f5f7ff 0%, #fff5f5 50%, #f0fff4 100%);
            min-height: 100vh;
        }
        
        /* Animated buttons */
        .stButton > button {
            border-radius: 25px;
            border: none;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .stButton > button:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }
        
        /* Simple form sections */
        .form-section {
            padding: 1.5rem 0;
            margin: 1rem 0;
        }
        
        /* Input styling */
        .stTextInput > div > div > input {
            border-radius: 20px;
            border: 3px solid #e8f2ff;
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 15px rgba(102, 126, 234, 0.3);
        }
        
        .stNumberInput > div > div > input {
            border-radius: 20px;
            border: 3px solid #e8f2ff;
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            text-align: center;
            font-weight: bold;
        }
        
        .stMultiSelect > div > div {
            border-radius: 20px;
            border: 3px solid #e8f2ff;
        }
        
        /* University preview styling */
        .university-preview {
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            padding: 1rem;
            margin: 0.5rem 0;
            max-height: 200px;
            overflow-y: auto;
            font-size: 0.9rem;
            line-height: 1.4;
        }
        
        /* Section headers */
        .section-header {
            font-size: 1.5rem;
            font-weight: bold;
            margin: 1.5rem 0 1rem 0;
            text-align: center;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Language toggle in elegant top corner
    col_spacer, col_lang = st.columns([5, 1])
    with col_lang:
        if st.button("🌐 한국어" if st.session_state.language == "en" else "🌐 English", 
                     key="lang_toggle", help="Switch language / 언어 변경"):
            st.session_state.language = "ko" if st.session_state.language == "en" else "en"
            st.rerun()
    
    lang = st.session_state.language
    
    # Fun, animated hero header
    st.markdown(f"""
    <div style="text-align: center; padding: 4rem 2rem; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 30px; margin-bottom: 2rem; color: white;
                box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
                position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; 
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                    animation: float 6s ease-in-out infinite;"></div>
        <h1 style="margin: 0; font-size: 3.2rem; font-weight: 800; margin-bottom: 1.5rem; 
                   text-shadow: 0 2px 4px rgba(0,0,0,0.3); position: relative; z-index: 1;">
            {get_text("app_title", lang)}
        </h1>
        <p style="margin: 0; font-size: 1.4rem; opacity: 0.95; line-height: 1.8; max-width: 650px; 
                  margin: 0 auto; position: relative; z-index: 1; font-weight: 300;">
            {get_text("app_subtitle", lang)}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # About section - using Streamlit info box to avoid HTML rendering issues
    with st.container():
        st.info("""
        🎯 **How Professor Finder Works**
        
        **Professor Finder** helps graduate students discover potential advisors by intelligently matching your research interests with faculty expertise and recent activity.
        
        **📊 Our Ranking Process:**
        - **Concept Matching (62.5%)**: Semantic analysis of research topics using OpenAlex and MeSH databases
        - **Recent Publications (37.5%)**: Activity in your field based on papers from the past 5 years  
        - **Smart Filtering**: Excludes medical doctors when searching non-medical fields
        - **Grant Info**: Funding data shown for reference only (not used in ranking due to reliability issues)
        
        **🔍 What We Care About:**
        - **Research Relevance**: How closely their work aligns with your keywords
        - **Recent Activity**: Publications in the last 5 years showing current engagement
        - **Accessibility**: Contact information and verification links for each professor
        - **Transparency**: Full provenance and explainable rankings you can trust
        
        💡 **Tip**: Use 2-5 specific keywords describing your research interests for best results. The system will automatically expand your search with related terms.
        """)
    
    # Keywords section
    st.markdown(f'<div class="section-header">🔤 {get_text("keywords_label", lang)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    keywords = st.text_input(
        "Keywords",  # Add label for accessibility
        placeholder=get_text("keywords_placeholder", lang),
        help=get_text("keywords_help", lang),
        key="keywords_input",
        label_visibility="hidden"  # Hide label visually but keep for screen readers
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Years and Max Professors section  
    st.markdown(f'<div class="section-header">⚙️ Search Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**📅 {get_text('years_label', lang)}**")
        years_window = st.number_input(
            "Years",  # Add label for accessibility
            min_value=1,
            max_value=10,
            value=DEFAULT_YEARS_WINDOW,
            help=get_text("years_help", lang),
            key="years_input",
            label_visibility="hidden"  # Hide label visually
        )
    
    with col2:
        st.markdown(f"**👥 {get_text('max_per_uni_label', lang)}**")
        max_per_university = st.number_input(
            "Max professors",  # Add label for accessibility
            min_value=1,
            max_value=20,
            value=5,
            help=get_text("max_per_uni_help", lang),
            key="max_per_uni_input",
            label_visibility="hidden"  # Hide label visually
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
        
    # University selection section
    st.markdown(f'<div class="section-header">🏫 {get_text("institutions_label", lang)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_unis' not in st.session_state:
        st.session_state['selected_unis'] = []
    if 'show_preview' not in st.session_state:
        st.session_state['show_preview'] = None
    
    # Quick filter buttons with preview functionality
    st.markdown('<p style="text-align: center; color: #666; margin-bottom: 1.5rem; font-size: 1.1rem;">Choose from curated university lists:</p>', unsafe_allow_html=True)
    
    # Top row: General categories
    col1, col2, col3 = st.columns(3, gap="medium")
    
    with col1:
        if st.button(get_text("curated_unis", lang), 
                     key="curated_btn",
                     type="secondary"):
            unis = CURATED_UNIVERSITIES[:15]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Top Programs", unis)
            st.rerun()
    
    with col2:
        if st.button(get_text("psychology_top", lang), 
                     key="psych_btn",
                     type="secondary"):
            unis = get_psychology_sociology_top_programs()[:15]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Psychology Programs", unis)
            st.rerun()
            
    with col3:
        if st.button(get_text("intl_friendly", lang), 
                     key="intl_btn",
                     type="secondary"):
            unis = get_international_friendly_universities()[:15]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("International Friendly", unis)
            st.rerun()
    
    # Regional buttons
    st.markdown('<p style="text-align: center; color: #666; margin: 1.5rem 0 1rem 0; font-size: 1rem;">Or select by US region:</p>', unsafe_allow_html=True)
    
    col_a, col_b, col_c, col_d, col_e = st.columns(5, gap="small")
    
    with col_a:
        if st.button(get_text("northeast", lang), key="ne_btn", type="secondary"):
            all_unis = get_northeast_universities()
            # Only include universities that are in CURATED_UNIVERSITIES to avoid errors
            unis = [uni for uni in all_unis if uni in CURATED_UNIVERSITIES]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Northeast", all_unis)  # Show all in preview
            st.rerun()
    
    with col_b:
        if st.button(get_text("southeast", lang), key="se_btn", type="secondary"):
            all_unis = get_southeast_universities()
            unis = [uni for uni in all_unis if uni in CURATED_UNIVERSITIES]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Southeast", all_unis)
            st.rerun()
    
    with col_c:
        if st.button(get_text("midwest", lang), key="mw_btn", type="secondary"):
            all_unis = get_midwest_universities()
            unis = [uni for uni in all_unis if uni in CURATED_UNIVERSITIES]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Midwest", all_unis)
            st.rerun()
    
    with col_d:
        if st.button(get_text("southwest", lang), key="sw_btn", type="secondary"):
            all_unis = get_southwest_universities()
            unis = [uni for uni in all_unis if uni in CURATED_UNIVERSITIES]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("Southwest", all_unis)
            st.rerun()
    
    with col_e:
        if st.button(get_text("west", lang), key="w_btn", type="secondary"):
            all_unis = get_west_universities()
            unis = [uni for uni in all_unis if uni in CURATED_UNIVERSITIES]
            st.session_state['selected_unis'] = unis
            st.session_state['show_preview'] = ("West Coast", all_unis)
            st.rerun()
    
    # Show preview of selected universities if available
    if st.session_state.get('show_preview'):
        category, unis_list = st.session_state['show_preview']
        st.markdown(f"""
        <div class="university-preview">
            <strong>📋 {category} ({len(unis_list)} universities):</strong><br><br>
            {'<br>'.join([f"• {uni}" for uni in unis_list[:10]])}
            {f'<br><br><em>... and {len(unis_list) - 10} more</em>' if len(unis_list) > 10 else ''}
        </div>
        """, unsafe_allow_html=True)
    
    # Manual selection
    st.markdown('<p style="color: #666; margin: 1.5rem 0 0.5rem 0; text-align: center;">Or manually select universities:</p>', unsafe_allow_html=True)
    
    # Filter selected unis to only include those in CURATED_UNIVERSITIES to avoid errors
    valid_selected_unis = [uni for uni in st.session_state.get('selected_unis', []) if uni in CURATED_UNIVERSITIES]
    
    # Use a separate key to avoid session state conflicts
    selected_universities = st.multiselect(
        "Universities",  # Add label for accessibility
        options=CURATED_UNIVERSITIES,
        default=valid_selected_unis,
        help=get_text("institutions_help", lang),
        key="university_multiselect",  # Changed key to avoid conflicts
        label_visibility="hidden"  # Hide label visually
    )
    
    # Only update session state if multiselect actually changed to prevent race conditions
    if selected_universities != st.session_state.get('selected_unis', []):
        st.session_state['selected_unis'] = selected_universities
    
    # Show selection count
    if selected_universities:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; 
                    padding: 1.5rem; border-radius: 15px; margin: 1rem 0; text-align: center;
                    border: 2px solid #b1dfbb;">
            ✅ <strong style="font-size: 1.2rem;">{len(selected_universities)}</strong> universities selected
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
        
    # Validation and search section
    st.markdown(f'<div class="section-header">🚀 {get_text("search_button", lang)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    
    keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    can_search = len(keywords_list) >= 2 and len(selected_universities) >= 1
    
    # Show validation status with fun styling
    if not can_search:
        if len(keywords_list) < 2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f8d7da, #f5c6cb); color: #721c24; 
                        padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                        border-left: 5px solid #dc3545; text-align: center;">
                <strong>⚠️ {get_text("error_no_keywords", lang)}</strong>
            </div>
            """, unsafe_allow_html=True)
        if len(selected_universities) < 1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f8d7da, #f5c6cb); color: #721c24; 
                        padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                        border-left: 5px solid #dc3545; text-align: center;">
                <strong>⚠️ {get_text("error_no_universities", lang)}</strong>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #d1ecf1, #bee5eb); color: #0c5460; 
                    padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                    border-left: 5px solid #17a2b8; text-align: center;">
            <strong>✅ Ready to search!</strong><br>
            <em>We'll search {len(selected_universities)} universities for professors matching your {len(keywords_list)} keywords</em>
        </div>
        """, unsafe_allow_html=True)
    
    # Properly centered search button - prevent interference with running searches
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        # Check if search is currently running to prevent interruption
        search_running = st.session_state.get('search_running', False)
        
        search_clicked = st.button(
            f"🔄 Searching..." if search_running else (f"🎯 {get_text('search_button', lang)}" if can_search else f"⏳ {get_text('search_button', lang)}"),
            disabled=not can_search or search_running,
            type="primary",
            key="search_btn",
            help="Search in progress..." if search_running else ("Start the intelligent professor search!" if can_search else "Please complete the form above"),
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Execute search if button clicked
    if search_clicked:
        st.session_state['search_running'] = True
        try:
            run_search(selected_universities, keywords_list, years_window, lang, max_per_university)
        finally:
            st.session_state['search_running'] = False


async def run_search_pipeline(institutions: List[str], keywords: List[str], years_window: int):
    """Run the complete search pipeline."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.container()
    
    try:
        # Step 1: Resolve institutions to ROR IDs
        status_text.text("🏛️ Resolving institutions to ROR IDs...")
        progress_bar.progress(10)
        
        resolved_institutions = await resolve_institutions(institutions)
        
        if not resolved_institutions:
            st.error("Could not resolve any institutions. Please check institution names.")
            return []
        
        with log_container:
            st.success(f"Resolved {len(resolved_institutions)} institutions")
            for inst in resolved_institutions:
                st.text(f"✓ {inst.name} → {inst.display_name} (ROR: {inst.ror_id})")
        
        # Step 2: Expand keywords
        status_text.text("📚 Expanding keywords using OpenAlex and MeSH...")
        progress_bar.progress(20)
        
        expanded_keywords = await expand_keywords(keywords)
        
        with log_container:
            st.success(f"Expanded {len(keywords)} keywords to {len(expanded_keywords.all_expanded)} terms")
            if expanded_keywords.openalex_concepts:
                st.text(f"OpenAlex concepts: {len(expanded_keywords.openalex_concepts)}")
            if expanded_keywords.mesh_terms:
                st.text(f"MeSH terms: {len(expanded_keywords.mesh_terms)}")
        
        # Step 3: Find authors by institution
        status_text.text("👥 Discovering researchers...")
        progress_bar.progress(30)
        
        all_authors = []
        for i, institution in enumerate(resolved_institutions):
            institution_authors = await find_authors_by_institution(
                institution, expanded_keywords, years_window
            )
            all_authors.extend(institution_authors)
            
            progress = 30 + (40 * (i + 1) / len(resolved_institutions))
            progress_bar.progress(int(progress))
            
            with log_container:
                st.text(f"Found {len(institution_authors)} authors at {institution.display_name}")
        
        if not all_authors:
            st.error("No matching authors found.")
            return []
        
        with log_container:
            st.success(f"Total authors found: {len(all_authors)}")
        
        # Step 4: Enrich with ORCID data
        status_text.text("🆔 Enriching with ORCID profiles...")
        progress_bar.progress(70)
        
        await enrich_authors_with_orcid(all_authors)
        
        # Step 5: Search for grants
        status_text.text("💰 Searching for grants...")
        progress_bar.progress(80)
        
        # Initialize grants list for all authors
        for author in all_authors:
            author.grants = []
        
        # Search grants for each institution
        for institution in resolved_institutions:
            institution_authors = [a for a in all_authors if a.institution and a.institution.ror_id == institution.ror_id]
            if institution_authors:
                await search_grants_for_authors(institution_authors, institution)
                await search_nsf_grants_for_authors(institution_authors, institution)
        
        # Step 6: Check recruitment signals
        status_text.text("📢 Checking recruitment signals...")
        progress_bar.progress(85)
        
        await detect_recruitment_signals(all_authors)
        
        # Step 7: Build evidence and calculate scores
        status_text.text("📊 Calculating scores...")
        progress_bar.progress(90)
        
        # Debug: Check how many authors have grants (reduced logging)
        authors_with_grants = [a for a in all_authors if hasattr(a, 'grants') and a.grants]
        if len(authors_with_grants) > 0:
            logger.warning(f"Grant search completed: {len(authors_with_grants)}/{len(all_authors)} authors have grants")
        
        results = []
        for author in all_authors:
            # Build evidence
            evidence = AuthorEvidence(
                profile=author,
                recent_publications=getattr(author, 'recent_publications', []),
                grants=getattr(author, 'grants', []),
                recruitment=getattr(author, 'recruitment', RecruitmentSignal()),
                matched_keywords=expanded_keywords.all_expanded,  # Will be refined in scoring
                evidence_urls=_build_evidence_urls(author),
                sources_used=_build_sources_list(author)
            )
            
            # Calculate scores
            scores = calculate_author_scores(evidence, expanded_keywords)
            
            result = AuthorResult(evidence=evidence, scores=scores)
            results.append(result)
        
        # Step 8: Rank results
        status_text.text("🏆 Ranking results...")
        progress_bar.progress(95)
        
        # Convert to the format expected by rank_authors_by_score
        author_score_pairs = [(result.evidence, result) for result in results]
        ranked_pairs = rank_authors_by_score(author_score_pairs)
        ranked_results = [pair[1] for pair in ranked_pairs]
        
        progress_bar.progress(100)
        status_text.text("✅ Search completed!")
        
        return ranked_results
        
    except Exception as e:
        logger.exception("Search pipeline failed")
        st.error(f"Search failed: {str(e)}")
        return []


def _build_evidence_urls(author) -> List[str]:
    """Build list of evidence URLs for an author."""
    urls = []
    
    # OpenAlex author profile
    urls.append(f"https://openalex.org/{author.openalex_id}")
    
    # Google Scholar search (helps find homepage and email)
    if author.institution:
        scholar_query = f"{author.name} {author.institution.name}".replace(" ", "+")
    else:
        scholar_query = author.name.replace(" ", "+")
    urls.append(f"https://scholar.google.com/scholar?q={scholar_query}")
    
    # ORCID profile
    if author.orcid_id:
        urls.append(f"https://orcid.org/{author.orcid_id}")
    
    # Recent works (sample)
    recent_pubs = getattr(author, 'recent_publications', [])
    for pub in recent_pubs[:3]:  # First 3 publications
        urls.append(pub.url)
    
    # Grant URLs
    grants = getattr(author, 'grants', [])
    for grant in grants:
        urls.append(grant.url)
    
    # Homepage
    if author.homepage_url:
        urls.append(author.homepage_url)
    
    return list(set(urls))  # Remove duplicates


def _build_sources_list(author) -> List[str]:
    """Build list of data sources used for an author."""
    sources = ["OpenAlex"]
    
    if author.orcid_id:
        sources.append("ORCID")
    
    grants = getattr(author, 'grants', [])
    if any(g.funder == "NIH" for g in grants):
        sources.append("NIH")
    if any(g.funder == "NSF" for g in grants):
        sources.append("NSF")
    
    recruitment = getattr(author, 'recruitment', None)
    if recruitment and recruitment.is_recruiting:
        sources.append("Homepage")
    
    return sources


def run_search(institutions: List[str], keywords: List[str], years_window: int, lang: str = "en", max_per_university: int = 5):
    """Run the search and display results."""
    
    # Show search progress
    st.markdown(f"### {get_text('results_title', lang)}")
    
    # Run the async pipeline
    results = asyncio.run(run_search_pipeline(institutions, keywords, years_window))
    
    if not results:
        return
    
    # Apply max per university filter
    if max_per_university and max_per_university < 20:  # Only filter if reasonable limit
        filtered_results = []
        university_counts = {}
        
        for result in results:  # Results are already ranked by score
            institution_name = result.evidence.profile.institution.display_name if result.evidence.profile.institution else "Unknown"
            current_count = university_counts.get(institution_name, 0)
            
            if current_count < max_per_university:
                filtered_results.append(result)
                university_counts[institution_name] = current_count + 1
        
        results = filtered_results
    
    # Display results with engaging design
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); 
                padding: 2.5rem 1rem; border-radius: 25px; margin: 2rem 0; color: white; text-align: center;
                box-shadow: 0 10px 30px rgba(76, 175, 80, 0.3);">
        <h2 style="margin: 0; font-size: 2.2rem; font-weight: 700; margin-bottom: 1rem;">
            📊 {get_text('results_title', lang)}
        </h2>
        <p style="margin: 0; font-size: 1.2rem; opacity: 0.95; line-height: 1.5;">
            {get_text('results_subtitle', lang).format(count=len(results))}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary metrics with engaging cards
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Group results by university for better metrics
    university_stats = {}
    total_score = 0
    for result in results:
        university = result.evidence.profile.institution.display_name if result.evidence.profile.institution else "Unknown"
        if university not in university_stats:
            university_stats[university] = {"count": 0, "total_score": 0, "grants": 0}
        university_stats[university]["count"] += 1
        university_stats[university]["total_score"] += result.scores.final_score
        if result.evidence.grants:
            university_stats[university]["grants"] += len([g for g in result.evidence.grants if g.is_active])
        total_score += result.scores.final_score
    
    # Calculate averages - with safety check to prevent division by zero
    for uni in university_stats:
        count = university_stats[uni]["count"]
        if count > 0:
            university_stats[uni]["avg_score"] = university_stats[uni]["total_score"] / count
        else:
            university_stats[uni]["avg_score"] = 0  # Fallback for corrupted data
    
    overall_avg = total_score / len(results) if results else 0
    total_grants = sum(len([g for g in r.evidence.grants if g.is_active]) for r in results if r.evidence.grants)
    
    # Two-column layout for cleaner metrics
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1); border-left: 4px solid #667eea;">
            <h3 style="margin: 0; color: #667eea; font-size: 2rem; font-weight: bold;">{len(results)}</h3>
            <p style="margin: 0.5rem 0 0 0; color: #666; font-weight: 500;">{get_text("total_authors", lang)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1); border-left: 4px solid #FF9800;">
            <h3 style="margin: 0; color: #FF9800; font-size: 2rem; font-weight: bold;">{total_grants}</h3>
            <p style="margin: 0.5rem 0 0 0; color: #666; font-weight: 500;">{get_text("with_grants", lang)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # University breakdown - with safety checks
    if len(university_stats) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f8f9ff, #e8f2ff); 
                    padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
            <h4 style="margin: 0 0 1rem 0; color: #333; text-align: center;">Average Relevance by University</h4>
        """, unsafe_allow_html=True)
        
        # Create columns for university stats - safety check to prevent crashes
        num_cols = min(max(len(university_stats), 1), 3)  # Ensure at least 1, max 3
        uni_cols = st.columns(num_cols)
        
        for i, (uni, stats) in enumerate(university_stats.items()):
            with uni_cols[i % num_cols]:
                # Truncate long university names to prevent layout breaks
                display_uni = uni[:50] + "..." if len(uni) > 50 else uni
                # Ensure avg_score calculation is safe
                safe_avg = stats.get('avg_score', 0) or 0
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                    <strong style="color: #333;" title="{uni}">{display_uni}</strong><br>
                    <span style="color: #667eea; font-size: 1.2rem; font-weight: bold;">{safe_avg:.3f}</span><br>
                    <small style="color: #888;">{stats['count']} professors</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Results table with modern styling
    st.markdown("<br><br>", unsafe_allow_html=True)
    display_results_table(results, lang)
    
    # Download CSV with centered, modern button - with error handling
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        csv_data = create_csv_download(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ShinHaEun_professor_search_{timestamp}.csv"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label=get_text("download_csv", lang),
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                type="primary",
                help=get_text("download_help", lang),
                key="download_btn"
            )
        
        # Personalized completion message
        st.success(f"🎉 {get_text('complete', lang)}")
        
    except Exception as e:
        logger.error(f"CSV generation failed: {e}")
        st.error("Failed to generate CSV. Please try again or contact support.")


def display_results_table(results: List[AuthorResult], lang: str = "en"):
    """Display results in an interactive table with language support."""
    
    # Convert to display format
    display_data = []
    for result in results:
        evidence = result.evidence
        scores = result.scores
        profile = evidence.profile
        
        # Build multiple contact/info links for better accessibility - with URL safety
        links = []
        
        def safe_url(url):
            """Ensure URL is safe for markdown/HTML."""
            if not url:
                return ""
            # Basic safety: remove quotes and angle brackets that could break markdown
            return url.replace('"', '').replace("'", "").replace('<', '').replace('>', '').strip()
        
        # Prioritize homepage/lab website if available
        if profile.homepage_url and profile.homepage_url.strip():
            safe_homepage = safe_url(profile.homepage_url)
            if safe_homepage:
                links.append(f"[🏠 Website]({safe_homepage})")
        
        # Add ORCID if available and valid
        if profile.orcid_id and profile.orcid_id.strip():
            # Clean ORCID ID (remove any https:// prefix if present)
            clean_orcid = profile.orcid_id.replace("https://orcid.org/", "")
            if clean_orcid and len(clean_orcid) > 10:  # Basic validation
                safe_orcid = safe_url(clean_orcid)
                if safe_orcid:
                    links.append(f"[📋 ORCID](https://orcid.org/{safe_orcid})")
        
        # Always include OpenAlex as fallback
        if profile.openalex_id:
            safe_openalex = safe_url(profile.openalex_id)
            if safe_openalex:
                links.append(f"[📚 OpenAlex](https://openalex.org/{safe_openalex})")
        
        contact_info = " • ".join(links) if links else "No links available"
        
        display_data.append({
            get_text("name", lang): profile.name,
            get_text("institution", lang): profile.institution.display_name if profile.institution else "",
            "Department": profile.department or "",
            get_text("final_score", lang): f"{scores.final_score:.3f}",
            "Concept Score": f"{scores.concept_score:.3f}",
            "Works Score": f"{scores.recent_works_score:.3f}",
            "Grant Score": f"{scores.grant_score:.3f}",
            get_text("recent_pubs", lang): len(evidence.recent_publications),
            get_text("active_grants", lang): len([g for g in evidence.grants if g.is_active]),
            get_text("contact_info", lang): contact_info,
            get_text("research_match", lang): scores.rationale
        })
    
    df = pd.DataFrame(display_data)
    
    # Display with formatting and comprehensive help text
    column_configs = {}
    column_configs[get_text("final_score", lang)] = st.column_config.NumberColumn(
        format="%.3f",
        help="""**Relevance Score (0.0-1.0)**: Overall ranking score combining concept and works matching.
        
Formula: (0.625 × Concept Score) + (0.375 × Works Score)
• Higher = better match for your research interests
• Range: 0.000 (no match) to 1.000 (perfect match)
• Based on keyword matching and recent publication activity"""
    )
    column_configs["Concept Score"] = st.column_config.NumberColumn(
        format="%.3f",
        help="""**Concept Score (0.0-1.0)**: How well the professor's research topics match your keywords.
        
Algorithm: Semantic similarity between your keywords and their research areas
• 0.8-1.0: Excellent match (primary research area)
• 0.6-0.8: Good match (secondary research area) 
• 0.4-0.6: Fair match (adjacent field)
• 0.0-0.4: Poor match (different field)
• Uses OpenAlex concept matching and MeSH terms"""
    )
    column_configs["Works Score"] = st.column_config.NumberColumn(
        format="%.3f", 
        help="""**Recent Publications Score (0.0-1.0)**: Activity in your research area based on recent papers.
        
Algorithm: Keyword matches in recent publications (past 5 years)
• 0.8-1.0: Very active (many recent papers match your keywords)
• 0.6-0.8: Active (several matching papers)
• 0.4-0.6: Somewhat active (few matching papers)
• 0.0-0.4: Inactive or no matches in recent work
• Considers paper titles, abstracts, and keywords"""
    )
    column_configs["Grant Score"] = st.column_config.NumberColumn(
        format="%.3f", 
        help="""**Grant Score (0.0-1.0)**: INFORMATIONAL ONLY - Not used in ranking.
        
Shows current research funding status:
• 0.8-1.0: Multiple active major grants
• 0.4-0.8: Some active grants
• 0.0-0.4: Few or no active grants
• Sources: NIH, NSF databases
• NOTE: Grant data is unreliable, so excluded from final ranking"""
    )
    column_configs[get_text("contact_info", lang)] = st.column_config.TextColumn(
        help="Clickable links to professor's website, ORCID profile, Google Scholar, and institutional page for easy contact and research verification"
    )
    
    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config=column_configs
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        # Clean up HTTP client
        try:
            asyncio.run(close_client())
        except Exception:
            pass