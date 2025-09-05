import re
from typing import List, Set
from urllib.parse import urljoin, urlparse


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.lower().strip())


def extract_keywords_from_text(text: str, keywords: List[str]) -> List[str]:
    """Extract matching keywords from text."""
    if not text or not keywords:
        return []
    
    normalized_text = normalize_text(text)
    matched = []
    
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword in normalized_text:
            matched.append(keyword)
    
    return matched


def deduplicate_preserving_order(items: List[str]) -> List[str]:
    """Remove duplicates while preserving order."""
    seen: Set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def truncate_with_ellipsis(text: str, max_length: int) -> str:
    """Truncate text to max_length with ellipsis if needed."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def ensure_absolute_url(url: str, base_url: str) -> str:
    """Ensure URL is absolute, using base_url if needed."""
    if not url:
        return ""
    return urljoin(base_url, url) if not is_valid_url(url) else url


def clean_html(html: str) -> str:
    """Remove HTML tags and clean up text."""
    if not html:
        return ""
    
    try:
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception:
        return html


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
        
    except Exception:
        # Fallback to simple HTML cleaning
        return clean_html(html)