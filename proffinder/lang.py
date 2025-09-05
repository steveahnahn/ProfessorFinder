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
    }
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text for the given key and language."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text