"""
Enhanced Graduate Program Finder with Social Psychology Focus
Includes top universities, program requirements, and faculty information
"""

import asyncio
import streamlit as st
import pandas as pd
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import csv
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import existing functionality
from app_original_backup import run_search_pipeline, _build_evidence_urls, _build_sources_list
from lang import get_text

# Import new social psychology modules
from core.social_psych_programs import (
    ProgramDetails, InternationalRequirements, FacultyMember,
    TOP_30_UNIVERSITIES, TOP_30_SOCIAL_PSYCH_PROGRAMS,
    program_db, DataSource
)
from sources.program_scraper import (
    update_program_data, get_data_documentation,
    UNIVERSITY_URL_PATTERNS
)
from sources.fetch_program_data import (
    populate_all_programs, initialize_program_data
)
from sources.verified_requirements_2025 import (
    get_accurate_requirements, get_suicide_faculty,
    get_data_verification_status, VERIFIED_REQUIREMENTS
)
from sources.complete_verified_requirements import (
    COMPLETE_REQUIREMENTS, get_all_requirements, has_clinical_program
)
from sources.psychology_department_rankings import (
    get_psychology_rank, get_ranking_source_info, NO_CLINICAL_PROGRAMS
)

# Add sample data for demonstration
def initialize_sample_data():
    """Initialize with sample data for key universities"""
    sample_programs = {
        "Stanford University": {
            "ranking_overall": 4,
            "ranking_social_psych": 1,
            "gpa_min": 3.5,
            "gre_required": False,
            "gre_waived": "GRE not required as of 2024",
            "toefl_min": 100,
            "ielts_min": 7.0,
            "letters": 3,
            "fee": 125,
            "deadline": "December 1",
            "acceptance_rate": 2.3,
            "faculty": [
                {"name": "Jennifer Eberhardt", "research": "Racial bias, Criminal justice, Social cognition"},
                {"name": "Hazel Markus", "research": "Culture and self, Social class, Identity"},
                {"name": "Jamil Zaki", "research": "Empathy, Social neuroscience, Prosocial behavior"}
            ],
            "website": "https://psychology.stanford.edu/graduate/program-areas/social-psychology"
        },
        "University of Michigan": {
            "ranking_overall": 20,
            "ranking_social_psych": 2,
            "gpa_min": 3.3,
            "gre_required": False,
            "gre_waived": "GRE optional for 2024-2025",
            "toefl_min": 100,
            "ielts_min": 7.0,
            "letters": 3,
            "fee": 90,
            "deadline": "December 1",
            "acceptance_rate": 5.1,
            "faculty": [
                {"name": "Phoebe Ellsworth", "research": "Emotion, Law and psychology, Culture"},
                {"name": "Ethan Kross", "research": "Self-control, Emotion regulation, Social rejection"},
                {"name": "Oscar Ybarra", "research": "Social cognition, Intergroup relations, Well-being"}
            ],
            "website": "https://lsa.umich.edu/psych/program/graduate-program/program-areas/social.html"
        },
        "Harvard University": {
            "ranking_overall": 3,
            "ranking_social_psych": 3,
            "gpa_min": 3.7,
            "gre_required": False,
            "gre_waived": "GRE not required",
            "toefl_min": 104,
            "ielts_min": 7.5,
            "letters": 3,
            "fee": 105,
            "deadline": "December 1",
            "acceptance_rate": 1.8,
            "faculty": [
                {"name": "Daniel Gilbert", "research": "Happiness, Affective forecasting, Decision making"},
                {"name": "Mahzarin Banaji", "research": "Implicit bias, Social cognition, Ethics"},
                {"name": "Joshua Greene", "research": "Moral psychology, Decision making, Neuroscience"}
            ],
            "website": "https://psychology.fas.harvard.edu/graduate"
        }
    }
    
    # Create ProgramDetails objects from sample data
    for uni_name, data in sample_programs.items():
        program = ProgramDetails(
            university_name=uni_name,
            program_name=f"PhD in Psychology - Social Psychology",
            degree_type="PhD",
            department="Department of Psychology",
            overall_university_ranking=data["ranking_overall"],
            social_psych_ranking=data["ranking_social_psych"],
            acceptance_rate=data["acceptance_rate"],
            program_website=data["website"]
        )
        
        # Set requirements
        reqs = program.international_requirements
        reqs.gpa_min = data["gpa_min"]
        reqs.gre_required = data["gre_required"]
        reqs.gre_waived_conditions = data["gre_waived"]
        reqs.toefl_min = data["toefl_min"]
        reqs.ielts_min = data["ielts_min"]
        reqs.letters_of_rec = data["letters"]
        reqs.application_fee = data["fee"]
        reqs.deadline_fall = data["deadline"]
        reqs.funding_guaranteed = True
        reqs.f1_eligible = True
        
        # Add faculty
        for fac_data in data["faculty"]:
            faculty = FacultyMember(
                name=fac_data["name"],
                title="Professor",
                research_areas=fac_data["research"].split(", ")
            )
            program.top_faculty.append(faculty)
        
        program.data_sources["sample"] = DataSource.MANUAL_VERIFICATION
        program.verification_status = "sample_data"
        
        program_db.add_program(program)

def display_program_card(program: ProgramDetails, lang='en', track='social', verified=False):
    """Display program information in an attractive card format"""
    with st.container():
        # Header with rankings
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            # Show if data is verified
            verified_badge = "✅ " if verified else ""
            st.markdown(f"### {verified_badge}🎓 {program.university_name}")
            if lang == 'ko':
                track_name = "임상심리학" if track == 'clinical' else "사회심리학"
                st.markdown(f"**심리학 박사 - {track_name}**")
            else:
                track_name = "Clinical Psychology" if track == 'clinical' else "Social Psychology"
                st.markdown(f"**PhD in Psychology - {track_name}**")
        with col2:
            # Show actual psychology department ranking based on track
            psych_rank, rank_source = get_psychology_rank(program.university_name, track if track != 'overall' else 'overall')
            if psych_rank != 999:
                label = "심리학과 순위" if lang == 'ko' else "Psych Dept Rank"
                st.metric(label, f"#{psych_rank}")
                st.caption(rank_source.split(' ')[0])  # Show abbreviated source
            else:
                st.metric("Rank", "Not Ranked")
                st.caption("No dept ranking available")
        with col3:
            # Always show acceptance rate if available (consistent for both tracks)
            if program.acceptance_rate:
                label = "합격률" if lang == 'ko' else "Accept Rate"
                st.metric(label, f"{program.acceptance_rate:.1f}%")
        with col4:
            # Show data verification status
            if verified:
                verified_text = "✅ 검증됨" if lang == 'ko' else "✅ Verified"
                verified_caption = "요건 검증됨" if lang == 'ko' else "Requirements verified"
                st.success(verified_text)
                st.caption(verified_caption)
            else:
                estimated_text = "⚠️ 추정" if lang == 'ko' else "⚠️ Estimated"
                estimated_caption = "일반적 패턴 기반" if lang == 'ko' else "Based on typical patterns"
                st.warning(estimated_text)
                st.caption(estimated_caption)
        
        # Requirements section
        if lang == 'ko':
            st.markdown("#### 📋 국제학생 입학 요건")
        else:
            st.markdown("#### 📋 International Student Requirements")
        
        req_cols = st.columns(4)
        reqs = program.international_requirements
        
        with req_cols[0]:
            st.markdown(f"**{get_text('academic', lang)}**")
            if reqs.gpa_min:
                st.write(f"• GPA: {reqs.gpa_min}+")
            else:
                st.write(f"• {get_text('gpa_no_minimum', lang)}")
            if reqs.gre_required:
                st.write(f"• {get_text('gre_required', lang)}")
            else:
                st.write(f"• GRE: {reqs.gre_waived_conditions or get_text('gre_not_required', lang)}")
        
        with req_cols[1]:
            st.markdown(f"**{get_text('english', lang)}**")
            if reqs.toefl_min:
                st.write(f"• TOEFL: {reqs.toefl_min}+")
            if reqs.ielts_min:
                st.write(f"• IELTS: {reqs.ielts_min}+")
        
        with req_cols[2]:
            st.markdown(f"**{get_text('application', lang)}**")
            st.write(f"• {get_text('letters', lang)}: {reqs.letters_of_rec}")
            if reqs.application_fee:
                st.write(f"• {get_text('fee', lang)}: ${reqs.application_fee}")
        
        with req_cols[3]:
            st.markdown(f"**{get_text('deadline', lang)}**")
            if reqs.deadline_fall:
                st.write(f"• {get_text('fall', lang)}: {reqs.deadline_fall}")
            if program.acceptance_rate:
                st.write(f"• {get_text('accept', lang)}: {program.acceptance_rate:.1f}%")
        
        # Faculty section
        if program.top_faculty:
            st.markdown(f"#### 👨‍🏫 {get_text('top_social_psychology_faculty', lang)}")
            
            for i, faculty in enumerate(program.top_faculty[:3], 1):
                with st.expander(f"{i}. {faculty.name} - {faculty.title}"):
                    st.write(f"**{get_text('research_areas', lang)}:** {', '.join(faculty.research_areas[:3])}")
                    if faculty.accepting_students is not None:
                        status = f"✅ {get_text('accepting', lang)}" if faculty.accepting_students else f"❌ {get_text('not_accepting', lang)}"
                        st.write(f"**{get_text('student_status', lang)}:** {status}")
                    if faculty.email:
                        st.write(f"**{get_text('email', lang)}:** {faculty.email}")
                    if faculty.website:
                        st.write(f"**{get_text('website', lang)}:** [{faculty.website}]({faculty.website})")
        
        # Additional info with data verification
        with st.expander(f"📌 {get_text('additional_information', lang)}"):
            if reqs.funding_guaranteed:
                st.success(f"✅ {get_text('funding_guaranteed', lang)}")
            if reqs.f1_eligible:
                st.info(f"✅ {get_text('f1_visa_eligible', lang)}")
            if program.program_website:
                st.write(f"🔗 [{get_text('program_website', lang)}]({program.program_website})")
            if program.admissions_website:
                st.write(f"🔗 [{get_text('admissions_info', lang)}]({program.admissions_website})")
            
            # Clinical program availability
            if track == 'clinical' and program.university_name in NO_CLINICAL_PROGRAMS:
                st.error(f"❌ {program.university_name} {get_text('no_clinical_program', lang)}")
            
            # Ranking source info with clickable links
            rank_info = get_ranking_source_info(track if track != 'overall' else 'overall')
            if rank_info:
                st.markdown(f"**{get_text('ranking_sources', lang)}:**")
                st.write(f"• {get_text('source', lang)}: {rank_info.get('source', 'Unknown')}")
                if rank_info.get('url'):
                    st.write(f"• {get_text('primary', lang)}: [{rank_info.get('url')}]({rank_info.get('url')})")
                if rank_info.get('secondary_url'):
                    st.write(f"• {get_text('secondary', lang)}: [{rank_info.get('secondary_url')}]({rank_info.get('secondary_url')})")
                if rank_info.get('apa_url'):
                    st.write(f"• {get_text('apa_database', lang)}: [{rank_info.get('apa_url')}]({rank_info.get('apa_url')})")
                st.write(f"• {get_text('confidence', lang)}: {rank_info.get('confidence', 'Unknown')}")
                st.write(f"• {get_text('methodology', lang)}: {rank_info.get('methodology', 'Not specified')}")
                st.write(f"• {get_text('last_verified', lang)}: {rank_info.get('last_verified', 'Unknown')}")
            
            # Data source info
            if program.data_sources:
                sources = ", ".join([s.value for s in program.data_sources.values()])
                st.caption(f"Data sources: {sources}")
            st.caption(f"Last updated: {program.last_updated.strftime('%Y-%m-%d')}")
            
            # Disclaimer
            st.warning(f"⚠️ **{get_text('always_verify_important', lang)}**")
        
        st.divider()

def export_to_csv(programs: List[ProgramDetails], track: str = "social") -> str:
    """Export programs to CSV format"""
    output = StringIO()
    
    fieldnames = [
        'University', 'Program', 'Psychology Dept Rank', 'Track Specific Rank',
        'GPA Min', 'GRE Required', 'GRE Notes', 'TOEFL Min', 'IELTS Min',
        'Letters Required', 'Application Fee', 'Fall Deadline',
        'Acceptance Rate', 'Funding Guaranteed',
        'Faculty 1 Name', 'Faculty 1 Research',
        'Faculty 2 Name', 'Faculty 2 Research',
        'Faculty 3 Name', 'Faculty 3 Research',
        'Program Website', 'Last Updated'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for program in programs:
        reqs = program.international_requirements
        
        row = {
            'University': program.university_name,
            'Program': program.program_name,
            'Psychology Dept Rank': get_psychology_rank(program.university_name, 'overall')[0],
            'Track Specific Rank': get_psychology_rank(program.university_name, track.lower() if track and track != 'overall' else 'social')[0],
            'GPA Min': reqs.gpa_min,
            'GRE Required': 'Yes' if reqs.gre_required else 'No',
            'GRE Notes': reqs.gre_waived_conditions,
            'TOEFL Min': reqs.toefl_min,
            'IELTS Min': reqs.ielts_min,
            'Letters Required': reqs.letters_of_rec,
            'Application Fee': reqs.application_fee,
            'Fall Deadline': reqs.deadline_fall,
            'Acceptance Rate': f"{program.acceptance_rate:.1f}%" if program.acceptance_rate else "",
            'Funding Guaranteed': 'Yes' if reqs.funding_guaranteed else 'No',
            'Program Website': program.program_website,
            'Last Updated': program.last_updated.strftime('%Y-%m-%d')
        }
        
        # Add faculty info
        for i, faculty in enumerate(program.top_faculty[:3], 1):
            row[f'Faculty {i} Name'] = faculty.name
            row[f'Faculty {i} Research'] = ', '.join(faculty.research_areas[:3])
        
        writer.writerow(row)
    
    return output.getvalue()

def main():
    st.set_page_config(
        page_title="Social Psychology Graduate Programs",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize with real data
    if 'initialized' not in st.session_state or len(program_db.programs) == 0:
        with st.spinner("🔄 Loading program data for all universities... This may take a moment on first load."):
            # First try to load real data
            success = initialize_program_data()
            if not success or len(program_db.programs) == 0:
                # Fallback to sample data if fetch fails
                st.warning("Using sample data. Click 'Refresh Data' to try fetching again.")
                initialize_sample_data()
        st.session_state.initialized = True
        st.session_state.programs_loaded = len(program_db.programs)
    
    # Custom CSS
    st.markdown("""
    <style>
        .main {
            padding-top: 1rem;
        }
        div[data-testid="stExpander"] {
            background-color: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 0.5rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #f0f2f6;
            border-radius: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #667eea;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Language toggle - persistent across all tabs
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        current_lang = st.session_state.get('language', 'en')
        if st.button("🇰🇷 한국어" if current_lang == 'en' else "🇺🇸 English", key="lang_toggle"):
            st.session_state.language = 'ko' if current_lang == 'en' else 'en'
            st.rerun()
    
    lang = st.session_state.get('language', 'en')
    
    # Header
    if lang == 'ko':
        st.title("🎓 사회심리학 대학원 프로그램")
        st.markdown("### 국제학생을 위한 완벽 가이드")
    else:
        st.title("🎓 Social Psychology Graduate Programs")
        st.markdown("### Complete International Student Guide")
    
    
    # Sidebar controls
    with st.sidebar:
        st.header(f"⚙️ {get_text('settings', lang)}" if lang == 'ko' else "⚙️ Settings")
        
        # Track selection (Clinical vs Social)
        st.subheader(f"🎯 {get_text('psych_track', lang)}")
        track = st.radio(
            get_text('select_track', lang) if lang == 'ko' else "Select track:",
            [get_text('social_psychology', lang), get_text('clinical_psychology', lang)],
            help=get_text('track_help', lang) if lang == 'ko' else "Clinical: Patient treatment, therapy, clinical research\nSocial: Population research, social factors, no patient contact",
            key="psych_track_selector"
        )
        
        # Removed research focus filter for simplicity
        focus = "General"  # Default value (no longer used in filtering)
        
        
        # Data options
        st.subheader(f"🔄 {get_text('data_management', lang)}")
        refresh_label = get_text('refresh_data', lang) if lang == 'ko' else "🔄 Refresh Data"
        refresh_help = get_text('refresh_help', lang) if lang == 'ko' else "Fetch latest data from university websites"
        if st.button(refresh_label, help=refresh_help):
            refresh_spinner = get_text('fetching_data', lang) if lang == 'ko' else "Fetching latest data... This may take a few minutes"
            with st.spinner(refresh_spinner):
                # Actually fetch real data
                success = initialize_program_data()
                if success:
                    success_msg = get_text('data_refresh_success', lang) if lang == 'ko' else "✅ Data refreshed successfully!"
                    st.success(success_msg)
                    st.rerun()
                else:
                    error_msg = get_text('data_refresh_error', lang) if lang == 'ko' else "Failed to refresh data. Please try again."
                    st.error(error_msg)
        
        # Export - simplified to CSV only
        st.subheader(f"📥 {get_text('export', lang)}")
        st.caption(get_text('csv_download_available', lang))
        
        # Info section
        info_label = get_text('data_sources_info', lang) if lang == 'ko' else "ℹ️ Data Sources"
        with st.expander(info_label):
            if lang == 'ko':
                st.markdown("""
                **데이터 수집 방법:**
                - 공식 대학 웹사이트
                - 대학원 입학 페이지  
                - 교수진 디렉토리
                - 연간 업데이트 (가을학기)
                
                **검증:**
                - 교차 참조된 소스
                - 수동 검증 플래그
                - 마지막 업데이트 타임스탬프
                """)
            else:
                st.markdown("""
                **How we collect data:**
                - Official university websites
                - Graduate admissions pages
                - Faculty directories
                - Annual updates (Fall)
                
                **Verification:**
                - Cross-referenced sources
                - Manual verification flags
                - Last update timestamps
                """)
    
    # Main content area
    if lang == 'ko':
        tab_labels = ["📋 프로그램", "🔍 교수 검색", "📊 비교", "📖 문서"]
    else:
        tab_labels = ["📋 Programs", "🔍 Search Faculty", "📊 Compare", "📖 Documentation"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_labels)
    
    with tab1:
        # Display title based on track
        track_name = "Clinical" if track == "Clinical Psychology" else "Social"
        if lang == 'ko':
            if track == "Clinical Psychology":
                st.header(f"📚 임상심리학 프로그램 (상위 대학)")
            else:
                st.header(f"📚 사회심리학 프로그램 (미국 상위 30개 대학)")
        else:
            if track == "Clinical Psychology":
                st.header(f"📚 Clinical Psychology Programs (Top Universities)")
            else:
                st.header(f"📚 Social Psychology Programs (Top 30 US Universities)")
        
        # Data verification disclaimer - CRITICAL!
        if lang == 'ko':
            st.info("""
            📊 **순위 및 데이터 이해하기**
            
            **표시된 순위**: 심리학과 순위 (전체 대학 순위가 아님)
            • 사회심리학 프로그램은 연구 영향력과 교수진 품질로 순위
            • 임상심리학 프로그램은 APA 인증과 훈련 품질로 순위
            • 이 순위는 귀하의 특정 관심 분야에서의 프로그램 강점을 반영
            
            **지원 요건**: 2024년 12월 업데이트
            • 대부분의 요건이 대학 입학 사무실 페이지에서 직접 확인됨
            • 일부 데이터는 일반적인 프로그램 패턴을 기반으로 추정됨 - 항상 대학에 확인하세요
            • 요건은 매년 변경됩니다 - 지원 전에 현재 세부사항을 확인하세요
            
            ⚠️ **중요**: 최신 정보는 입학 사무실에 직접 문의하세요
            """)
        else:
            st.info("""
            📊 **Understanding Our Rankings & Data**
            
            **Rankings Shown**: Psychology Department Rankings (not overall university prestige)
            • Social Psychology programs ranked by research impact and faculty quality
            • Clinical Psychology programs ranked by APA accreditation and training quality
            • These rankings reflect program strength in your specific field of interest
            
            **Application Requirements**: Updated December 2024
            • Most requirements verified directly from university admissions pages
            • Some data estimated based on typical program patterns - always verify with universities
            • Requirements change annually - confirm current details before applying
            
            ⚠️ **Important**: Contact admissions offices directly for the most current information
            """)
        
        # Show track differences
        if track == "Clinical Psychology":
            if lang == 'ko':
                st.warning("""
                **임상심리학 전공:**
                • 🎯 초점: 환자 치료, 치료법, 임상 연구
                • 📊 합격률: 2-5% (극도로 경쟁적)
                • 📚 필수: 임상 경험 (위기 상담 전화, 클리닉 자원봉사)
                • 🎓 학점: 3.7+ 일반적
                • 💼 진로: 면허 심리학자, 치료사, 임상 연구자
                
                ❗ **참고**: 일부 대학(프린스턴, MIT 등)은 임상 프로그램이 없습니다!
                """)
            else:
                st.warning("""
                **Clinical Psychology Track:**
                • 🎯 Focus: Patient treatment, therapy, clinical research
                • 📊 Acceptance Rate: 2-5% (EXTREMELY competitive)
                • 📚 Required: Clinical experience (crisis hotlines, clinics)
                • 🎓 GPA: 3.7+ typical
                • 💼 Career: Licensed psychologist, therapist, clinical researcher
                
                ❗ **Note**: Some universities (Princeton, MIT, etc.) don't have clinical programs!
                """)
        else:
            if lang == 'ko':
                st.info("""
                **사회심리학 전공:**
                • 🎯 초점: 인구 연구, 사회적 요인, 집단 행동
                • 📊 합격률: 8-12% (경쟁적)
                • 📚 필수: 연구 경험 (실험실, 실험)
                • 🎓 학점: 3.5+ 일반적
                • 💼 진로: 교수, 연구자, 컨설턴트 (환자 치료 없음)
                """)
            else:
                st.info("""
                **Social Psychology Track:**
                • 🎯 Focus: Population research, social factors, group behavior
                • 📊 Acceptance Rate: 8-12% (competitive)
                • 📚 Required: Research experience (labs, experiments)
                • 🎓 GPA: 3.5+ typical
                • 💼 Career: Professor, researcher, consultant (no patient treatment)
                """)
        
        # Show data verification status
        if st.checkbox("Show data verification status"):
            st.info(get_data_verification_status())
        
        # Display programs based on selected track
        if track == "Clinical Psychology":
            # Show top universities with clinical programs (some top unis don't have clinical)
            universities = ["Harvard University", "Yale University", "Stanford University", 
                          "University of Michigan", "University of California, Los Angeles", "University of Pennsylvania",
                          "Columbia University", "Duke University", "Northwestern University",
                          "University of Wisconsin-Madison", "University of California, Berkeley",
                          "New York University", "University of Washington", "University of Minnesota",
                          "Ohio State University", "Arizona State University", "University of Virginia",
                          "University of Illinois at Urbana-Champaign", "University of California, San Diego",
                          "University of North Carolina at Chapel Hill", "University of Texas at Austin",
                          "University of Pittsburgh", "University of Colorado Boulder", "Vanderbilt University",
                          "University of California, Davis", "University of Kansas", "University of Nebraska-Lincoln",
                          "University of Missouri", "University of Delaware", "University of Vermont", "Temple University"]
        else:
            # For social psychology, show all TOP 30 US universities with their psych dept ranks
            # This allows users to see gaps in psychology rankings vs overall university prestige
            universities = TOP_30_UNIVERSITIES
        
        # Add sorting option
        st.subheader(f"🔢 {get_text('sort_order', lang)}")
        sort_by = st.selectbox(
            "Sort programs by:" if lang == 'en' else "프로그램 정렬 기준:",
            [get_text('psych_dept_ranking', lang), get_text('overall_university_ranking', lang), get_text('acceptance_rate_competitive', lang), get_text('alphabetical', lang)],
            help="Choose how to order the programs in the list",
            key="sort_programs_selector"
        )
        
        # Get programs with verified data
        programs = []
        skipped_no_clinical = []
        
        for uni in universities:
            # Skip universities without clinical programs when Clinical track selected
            if track == "Clinical Psychology" and not has_clinical_program(uni):
                skipped_no_clinical.append(uni)
                continue
                
            program = program_db.get_program(uni)
            if program:
                # Get complete verified requirements for ALL universities
                verified = get_all_requirements(uni, track_name.lower())
                if verified and 'error' not in verified:
                    # Update requirements with verified data
                    reqs = program.international_requirements
                    reqs.gre_required = verified.get('gre_required', reqs.gre_required)
                    reqs.gre_waived_conditions = verified.get('gre_notes', reqs.gre_waived_conditions)
                    reqs.toefl_min = verified.get('toefl_min', reqs.toefl_min)
                    reqs.gpa_min = verified.get('gpa_min', reqs.gpa_min)
                    reqs.application_fee = verified.get('application_fee', reqs.application_fee)
                    reqs.deadline_fall = verified.get('deadline', reqs.deadline_fall)
                    
                    # Update acceptance rate - THIS IS KEY DIFFERENCE
                    program.acceptance_rate = verified.get('acceptance_rate', program.acceptance_rate)
                
                # Use default faculty from program data (focus filtering removed for simplicity)
                
                programs.append(program)
        
        # Sort programs based on selected criteria
        if programs:
            if sort_by == get_text('psych_dept_ranking', lang):
                # Sort by psychology department ranking (lower number = better rank)
                programs.sort(key=lambda p: get_psychology_rank(p.university_name, track_name.lower())[0])
            elif sort_by == get_text('overall_university_ranking', lang):
                # Sort by overall university ranking (use original TOP_30 order)
                programs.sort(key=lambda p: TOP_30_UNIVERSITIES.index(p.university_name) if p.university_name in TOP_30_UNIVERSITIES else 999)
            elif sort_by == get_text('acceptance_rate_competitive', lang):
                # Sort by acceptance rate (lower = more competitive, put None at end)
                programs.sort(key=lambda p: p.acceptance_rate if p.acceptance_rate else 999)
            elif sort_by == get_text('alphabetical', lang):
                programs.sort(key=lambda p: p.university_name)
        
        # Display results
        st.markdown(f"### {get_text('showing_programs', lang, count=len(programs))}")
        
        # Show note about universities without clinical programs
        if skipped_no_clinical and track == "Clinical Psychology":
            with st.expander(f"ℹ️ {get_text('universities_no_clinical', lang, count=len(skipped_no_clinical))}"):
                st.warning(get_text('no_clinical_programs_explanation', lang, universities=', '.join(skipped_no_clinical)))
        
        if len(programs) == 0:
            st.warning(f"""
            {get_text('no_programs_found', lang)}. {get_text('no_programs_reasons', lang)}
            
            {get_text('database_contains', lang, count=len(program_db.programs))}
            {get_text('looking_for_universities', lang, group_type=track + " Psychology Programs")}
            """)
            
            # Show what universities we're looking for
            st.write("Universities being searched:", universities[:10])
        else:
            # Export button
            csv_data = export_to_csv(programs, track)
            download_label = "📥 CSV로 다운로드" if lang == 'ko' else "📥 Download as CSV"
            st.download_button(
                label=download_label,
                data=csv_data,
                file_name=f"social_psych_programs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Display each program
            for program in programs:
                # Check if this program has verified data - NOW ALL 30 HAVE IT!
                verified = program.university_name in COMPLETE_REQUIREMENTS
                display_program_card(program, lang, track_name.lower(), verified)
    
    with tab2:
        search_header = get_text('search_faculty_header', lang) if lang == 'ko' else "🔍 Search for Social Psychology Faculty"
        st.header(search_header)
        
        # Search interface
        col1, col2 = st.columns([3, 1])
        with col1:
            keyword_label = get_text('research_keywords_label', lang) if lang == 'ko' else "Research keywords:"
            keyword_placeholder = get_text('research_keywords_placeholder', lang) if lang == 'ko' else "e.g., implicit bias, social cognition, stereotyping"
            keyword_help = get_text('research_keywords_help', lang) if lang == 'ko' else "Enter research topics to find matching faculty"
            keywords = st.text_input(
                keyword_label,
                placeholder=keyword_placeholder,
                help=keyword_help
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            search_button_text = get_text('search_button_faculty', lang) if lang == 'ko' else "🔍 Search"
            search_button = st.button(search_button_text, type="primary")
        
        if search_button and keywords:
            # This would integrate with the existing search functionality
            info_text = get_text('searching_faculty_info', lang) if lang == 'ko' else "Searching for faculty... (This would use the existing search pipeline)"
            st.info(info_text)
            
            # For demo, show how it would work
            spinner_text = get_text('searching_spinner', lang) if lang == 'ko' else "Searching..."
            with st.spinner(spinner_text):
                # Would call: results = asyncio.run(run_search_pipeline(...))
                success_text = get_text('search_complete_demo', lang) if lang == 'ko' else "Search complete! (Demo mode - actual implementation would show results)"
                st.success(success_text)
    
    with tab3:
        compare_header = get_text('compare_programs_header', lang) if lang == 'ko' else "📊 Compare Programs"
        st.header(compare_header)
        
        # Program selection
        all_programs = [program_db.get_program(uni) for uni in universities if program_db.get_program(uni)]
        program_names = [p.university_name for p in all_programs]
        
        select_label = get_text('select_programs_compare', lang) if lang == 'ko' else "Select programs to compare (max 5):"
        selected_programs = st.multiselect(
            select_label,
            program_names,
            max_selections=5,
            key="compare_programs_selector"
        )
        
        if selected_programs:
            # Create comparison table
            comparison_data = []
            
            for uni_name in selected_programs:
                program = program_db.get_program(uni_name)
                if program:
                    reqs = program.international_requirements
                    comparison_data.append({
                        "University": program.university_name,
                        "Overall Rank": program.overall_university_ranking,
                        "Social Psych Rank": program.social_psych_ranking,
                        "GPA Min": reqs.gpa_min,
                        "GRE": "Required" if reqs.gre_required else "Not Required",
                        "TOEFL": reqs.toefl_min,
                        "IELTS": reqs.ielts_min,
                        "Letters": reqs.letters_of_rec,
                        "Fee": f"${reqs.application_fee}" if reqs.application_fee else "N/A",
                        "Deadline": reqs.deadline_fall,
                        "Acceptance": f"{program.acceptance_rate:.1f}%" if program.acceptance_rate else "N/A"
                    })
            
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
    
    with tab4:
        doc_header = get_text('documentation_header', lang) if lang == 'ko' else "📖 Documentation"
        st.header(doc_header)
        
        # Create sub-tabs for different documentation sections
        if lang == 'ko':
            doc_tab_labels = [get_text('ranking_methodology', lang), get_text('data_collection_tab', lang), get_text('data_freshness_tab', lang)]
        else:
            doc_tab_labels = ["📊 Ranking Methodology", "🔍 Data Collection", "📅 Data Freshness"]
        doc_tab1, doc_tab2, doc_tab3 = st.tabs(doc_tab_labels)
        
        with doc_tab1:
            st.markdown("""
            ## 🏆 How We Rank Universities
            
            ### Overall University Rankings (1-30)
            **Source**: US News & World Report National Universities Rankings 2024
            
            These rankings consider:
            - 📚 Academic reputation (peer assessment surveys)
            - 🎓 Graduation and retention rates (6-year graduation rate)
            - 👨‍🏫 Faculty resources (class size, faculty salary, student-faculty ratio)
            - 📈 Student selectivity (SAT/ACT scores, high school class standing)
            - 💰 Financial resources per student
            - 🤝 Alumni giving rate
            - 📊 Graduate rate performance
            
            ### Why Different Acceptance Rates for Clinical vs Social?
            
            #### **Clinical Psychology** (2-5% acceptance)
            - Extremely limited spots (4-8 students per year)
            - Requires extensive clinical training resources
            - Must maintain APA accreditation ratios
            - Includes paid internships and supervision
            - Higher cost per student to train
            
            #### **Social Psychology** (8-14% acceptance)
            - Larger cohorts (8-15 students per year)
            - Research-focused (less resource-intensive)
            - More flexible lab arrangements
            - No clinical supervision requirements
            - Standard research assistantships
            
            ### Important Notes on Rankings
            
            ⚠️ **Clinical Programs**: We don't provide clinical-specific rankings because:
            - Programs vary by theoretical orientation (CBT, psychodynamic, etc.)
            - APA accreditation status varies
            - Specializations differ (child, neuropsych, health)
            - **Use acceptance rates as quality indicator instead**
            
            ✅ **Social Psychology Programs**: Rankings based on:
            - Research output (40%) - publications in top journals
            - Faculty quality (30%) - awards, grants, citations
            - Student outcomes (20%) - job placements
            - Resources (10%) - funding, facilities
            
            ### Universities WITHOUT Clinical Programs
            These top universities don't offer clinical psychology PhDs:
            - Princeton, MIT, Caltech
            - University of Chicago, Dartmouth
            - Georgetown, Carnegie Mellon
            - Cornell (separate medical school program)
            - UC Davis
            
            💡 **Remember**: Faculty match matters MORE than ranking for PhD success!
            """)
        
        with doc_tab2:
            st.markdown(get_data_documentation())
            
            # Show URL patterns being used
            with st.expander("🔗 Data Source URLs"):
                st.json(UNIVERSITY_URL_PATTERNS)
        
        with doc_tab3:
            freshness_header = "📅 데이터 최신성 보고서" if lang == 'ko' else "📅 Data Freshness Report"
            st.subheader(freshness_header)
        
        freshness_data = []
        for uni in universities:
            program = program_db.get_program(uni)
            if program:
                days_old = (datetime.now() - program.last_updated).days
                freshness_data.append({
                    "University": program.university_name,
                    "Last Updated": program.last_updated.strftime("%Y-%m-%d"),
                    "Days Old": days_old,
                    "Status": "✅ Current" if days_old < 30 else "⚠️ Needs Update" if days_old < 365 else "❌ Outdated"
                })
        
        if freshness_data:
            freshness_df = pd.DataFrame(freshness_data)
            st.dataframe(freshness_df, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()