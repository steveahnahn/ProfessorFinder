"""
Language translations for the ProfFinder application.
Supports English and Korean.
"""

TRANSLATIONS = {
    "en": {
        # Main UI
        "app_title": "🎓 Professor Finder - Graduate Advisor Discovery",
        "app_subtitle": "Welcome, Shin Ha Eun! Find your perfect graduate advisor based on research expertise and availability",
        "language_toggle": "Language",
        
        # Search Form
        "search_form_title": "🔍 Search Parameters",
        "keywords_label": "Research Keywords (comma-separated)",
        "keywords_help": "Enter 2-5 keywords separated by commas describing your research interests",
        "keywords_placeholder": "machine learning, neural networks, artificial intelligence",
        "institutions_label": "Select Universities",
        "institutions_help": "Choose universities to search. Select multiple institutions for broader results.",
        "years_label": "Recent Publications Window (Years)",
        "years_help": "Number of years back to search for recent publications that match your keywords",
        "max_per_uni_label": "Max Professors per University",
        "max_per_uni_help": "Limit results to top X professors per university for easier selection",
        "search_button": "🚀 Find Advisors",
        
        # University Categories
        "curated_unis": "🏆 Top Programs",
        "northeast": "🗽 Northeast",
        "southeast": "🌴 Southeast", 
        "midwest": "🌾 Midwest",
        "southwest": "🌵 Southwest",
        "west": "🏔️ West Coast",
        "intl_friendly": "🌎 International Friendly",
        "psychology_top": "🧠 Psychology Programs",
        
        # Results
        "results_title": "📊 Search Results for Shin Ha Eun",
        "results_subtitle": "Great job, Shin Ha Eun! Found {count} professors ranked by research relevance for your search",
        "no_results": "No professors found matching your criteria. Try different keywords or universities.",
        
        # Metrics
        "total_authors": "Total Authors",
        "likely_recruiting": "Likely Recruiting",
        "with_grants": "With Grants Found",
        "avg_score": "Average Relevance",
        
        # Table Headers
        "name": "Name",
        "institution": "Institution", 
        "final_score": "Relevance Score",
        "recent_pubs": "Recent Pubs",
        "active_grants": "Active Grants",
        "recruiting_status": "Recruiting",
        "contact_info": "Contact/Info",
        "research_match": "Research Match",
        
        # Download
        "download_csv": "📥 Download Shin Ha Eun's Results (CSV)",
        "download_help": "Export all results to CSV for Shin Ha Eun's further analysis",
        
        # Status Messages
        "searching": "🔍 Searching for professors for Shin Ha Eun...",
        "found_authors": "✅ Found {count} relevant professors for Shin Ha Eun",
        "processing": "⚙️ Processing Shin Ha Eun's results...",
        "complete": "🎉 Search complete for Shin Ha Eun!",
        
        # Recruiting Status
        "recruiting_yes": "✅",
        "recruiting_no": "❌", 
        "recruiting_unknown": "❓",
        
        # Errors
        "error_no_keywords": "Please enter at least 2 research keywords",
        "error_no_universities": "Please select at least one university",
        "error_search_failed": "Search failed. Please try again.",
        
        # Additional UI Elements
        "how_it_works_title": "🎯 **How Professor Finder Works**",
        "how_it_works_description": "**Professor Finder** helps graduate students discover potential advisors by intelligently matching your research interests with faculty expertise and recent activity.",
        "ranking_process": "**📊 Our Ranking Process:**",
        "concept_matching": "- **Concept Matching (62.5%)**: Semantic analysis of research topics using OpenAlex and MeSH databases",
        "recent_publications": "- **Recent Publications (37.5%)**: Activity in your field based on papers from the past 5 years",
        "smart_filtering": "- **Smart Filtering**: Excludes medical doctors when searching non-medical fields",
        "grant_info": "- **Grant Info**: Funding data shown for reference only (not used in ranking due to reliability issues)",
        "max_professors_label": "Max professors",
        "universities_multiselect": "Universities",
        "search_progress": "Search in progress...",
        "start_search": "Start the intelligent professor search!",
        "complete_form": "Please complete the form above",
        "resolving_institutions": "🏛️ Resolving institutions to ROR IDs...",
        "could_not_resolve": "Could not resolve any institutions. Please check institution names.",
        "resolved_institutions": "Resolved {count} institutions",
        "discovering_researchers": "👥 Discovering researchers...",
        "found_authors_at": "Found {count} authors at {institution}",
        "checking_recruitment": "📢 Checking recruitment signals...",
        "calculating_scores": "📊 Calculating scores...",
        "what_we_care_about": "**🔍 What We Care About:**",
        "research_relevance": "- **Research Relevance**: How closely their work aligns with your keywords", 
        "recent_activity": "- **Recent Activity**: Publications in the last 5 years showing current engagement",
        "university_diversity": "- **University Diversity**: We search across top institutions to give you options",
        "transparency": "- **Transparency**: Every result includes direct links to verify their expertise",
        "limitations_title": "**⚠️ Important Limitations:**",
        "grant_reliability": "- **Grant Data**: May be incomplete or outdated - verify directly with professors",
        "department_gaps": "- **Department Data**: Some professors may not have complete department information",
        "publication_limit": "- **Publications**: Limited to 50 most recent papers per author",
        "manual_verification": "- **Always verify**: Contact professors directly to confirm current availability and interests",
    },
    
    "ko": {
        # Main UI
        "app_title": "🎓 프로페서 파인더 - 대학원 지도교수 발견",
        "app_subtitle": "환영합니다, 신하은님! 연구 전문성과 가용성을 바탕으로 완벽한 대학원 지도교수를 찾아보세요",
        "language_toggle": "언어",
        
        # Search Form
        "search_form_title": "🔍 검색 조건",
        "keywords_label": "연구 키워드 (쉼표로 구분)",
        "keywords_help": "연구 관심사를 설명하는 2-5개의 키워드를 쉼표로 구분하여 입력하세요",
        "keywords_placeholder": "기계학습, 신경망, 인공지능",
        "institutions_label": "대학 선택",
        "institutions_help": "검색할 대학을 선택하세요. 더 넓은 결과를 위해 여러 대학을 선택할 수 있습니다.",
        "years_label": "최근 논문 검색 범위 (년)",
        "years_help": "키워드와 일치하는 최근 논문을 검색할 과거 년수",
        "max_per_uni_label": "대학당 최대 교수 수",
        "max_per_uni_help": "대학별로 상위 X명의 교수만 표시하여 선택을 용이하게 함",
        "search_button": "🚀 지도교수 찾기",
        
        # University Categories  
        "curated_unis": "🏆 최고 프로그램",
        "northeast": "🗽 동북부",
        "southeast": "🌴 남동부", 
        "midwest": "🌾 중서부",
        "southwest": "🌵 남서부",
        "west": "🏔️ 서부",
        "intl_friendly": "🌎 국제학생 친화적",
        "psychology_top": "🧠 심리학 프로그램",
        
        # Results
        "results_title": "📊 신하은님을 위한 검색 결과",
        "results_subtitle": "잘하셨어요, 신하은님! 당신의 검색에 대해 연구 관련성으로 순위를 매긴 {count}명의 교수를 찾았습니다",
        "no_results": "검색 조건에 맞는 교수를 찾지 못했습니다. 다른 키워드나 대학을 시도해보세요.",
        
        # Metrics
        "total_authors": "총 교수 수",
        "likely_recruiting": "학생 모집 가능성",
        "with_grants": "연구비 보유",
        "avg_score": "평균 관련성",
        
        # Table Headers
        "name": "이름",
        "institution": "소속 대학",
        "final_score": "관련성 점수", 
        "recent_pubs": "최근 논문",
        "active_grants": "활성 연구비",
        "recruiting_status": "학생 모집",
        "contact_info": "연락처/정보",
        "research_match": "연구 일치도",
        
        # Download
        "download_csv": "📥 신하은님의 결과 다운로드 (CSV)",
        "download_help": "신하은님의 추가 분석을 위해 모든 결과를 CSV로 내보내기",
        
        # Status Messages
        "searching": "🔍 신하은님을 위한 교수 검색 중...",
        "found_authors": "✅ 신하은님을 위한 {count}명의 관련 교수를 찾았습니다",
        "processing": "⚙️ 신하은님의 결과 처리 중...",
        "complete": "🎉 신하은님의 검색이 완료되었습니다!",
        
        # Recruiting Status
        "recruiting_yes": "✅",
        "recruiting_no": "❌",
        "recruiting_unknown": "❓",
        
        # Errors
        "error_no_keywords": "최소 2개의 연구 키워드를 입력해주세요",
        "error_no_universities": "최소 하나의 대학을 선택해주세요", 
        "error_search_failed": "검색에 실패했습니다. 다시 시도해주세요.",
        
        # Additional UI Elements
        "how_it_works_title": "🎯 프로페서 파인더의 작동 원리",
        "how_it_works_description": "프로페서 파인더는 연구 관심사를 교수진 전문성 및 최근 활동과 지능적으로 매칭하여 대학원생들이 잠재적 지도교수를 발견할 수 있도록 도와줍니다.",
        "ranking_process": "📊 순위 매기기 과정:",
        "concept_matching": "개념 매칭 (62.5%): OpenAlex 및 MeSH 데이터베이스를 사용한 연구 주제의 의미적 분석",
        "recent_publications": "최근 논문 (37.5%): 지난 5년간 논문을 기반으로 한 해당 분야 활동",
        "smart_filtering": "스마트 필터링: 비의료 분야 검색 시 의사 제외",
        "grant_info": "연구비 정보: 신뢰성 문제로 순위에는 사용되지 않고 참고용으로만 표시",
        "max_professors_label": "최대 교수 수",
        "universities_multiselect": "대학교",
        "search_progress": "검색 진행 중...",
        "start_search": "지능형 교수 검색을 시작하세요!",
        "complete_form": "위의 양식을 완성해주세요",
        "resolving_institutions": "🏛️ 대학을 ROR ID로 변환 중...",
        "could_not_resolve": "대학을 확인할 수 없습니다. 대학 이름을 확인해주세요.",
        "resolved_institutions": "{count}개 대학을 확인했습니다",
        "discovering_researchers": "👥 연구자 발견 중...",
        "found_authors_at": "{institution}에서 {count}명의 교수를 찾았습니다",
        "checking_recruitment": "📢 모집 신호 확인 중...",
        "calculating_scores": "📊 점수 계산 중...",
        "what_we_care_about": "**🔍 중요하게 고려하는 요소:**",
        "research_relevance": "- **연구 관련성**: 그들의 연구가 당신의 키워드와 얼마나 밀접하게 일치하는지",
        "recent_activity": "- **최근 활동**: 현재 참여도를 보여주는 지난 5년간의 논문 발표",
        "university_diversity": "- **대학 다양성**: 최고의 기관들을 검색하여 다양한 선택지를 제공",
        "transparency": "- **투명성**: 모든 결과에는 전문성을 확인할 수 있는 직접 링크 포함",
        "limitations_title": "**⚠️ 중요한 제한사항:**",
        "grant_reliability": "- **연구비 데이터**: 불완전하거나 오래된 정보일 수 있음 - 교수에게 직접 확인 필요",
        "department_gaps": "- **소속 부서 데이터**: 일부 교수의 소속 부서 정보가 불완전할 수 있음",
        "publication_limit": "- **논문**: 저자당 최근 50편의 논문으로 제한",
        "manual_verification": "- **항상 확인**: 현재 가용성과 관심사를 확인하기 위해 교수에게 직접 연락"
    }
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text for the given key and language."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text