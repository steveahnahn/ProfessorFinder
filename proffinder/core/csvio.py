import csv
import io
from typing import List, Dict, Any
from datetime import datetime

from core.models import AuthorResult, CSVRow


def convert_results_to_csv_rows(results: List[AuthorResult]) -> List[CSVRow]:
    """Convert author results to CSV row format."""
    csv_rows = []
    
    for result in results:
        evidence = result.evidence
        scores = result.scores
        profile = evidence.profile
        
        # Prepare publication info
        recent_pubs = evidence.recent_publications
        example_titles = "; ".join([pub.title for pub in recent_pubs[:3]])  # Top 3
        
        # Prepare grant info with confidence levels
        active_grants = [g for g in evidence.grants if g.is_active]
        funders = "; ".join(list(set([g.funder for g in active_grants])))
        grant_ids = "; ".join([g.id for g in active_grants])
        grant_urls = "; ".join([g.url for g in active_grants])
        
        # Grant confidence breakdown
        known_count = len([g for g in active_grants if getattr(g, 'confidence', 'unknown') == 'known'])
        estimated_count = len([g for g in active_grants if getattr(g, 'confidence', 'unknown') == 'estimated'])
        unknown_count = len([g for g in evidence.grants if getattr(g, 'confidence', 'unknown') == 'unknown'])
        
        grant_confidence = f"Known: {known_count}, Estimated: {estimated_count}, Unknown: {unknown_count}"
        
        # Prepare recruitment info
        recruitment = evidence.recruitment
        
        # Create Excel-compatible hyperlink formulas for better CSV experience
        def make_excel_link(url, display_text=None):
            """Create Excel HYPERLINK formula if URL exists."""
            if not url or not url.strip():
                return ""
            display = display_text or url
            return f'=HYPERLINK("{url}","{display}")'
        
        # Create CSV row with Excel-compatible hyperlinks and safe field access
        csv_row = CSVRow(
            institution_name=profile.institution.name if profile.institution else "",
            institution_ror=profile.institution.ror_id if profile.institution else "",
            author_name=profile.name or "",
            openalex_id=make_excel_link(f"https://openalex.org/{profile.openalex_id}", "OpenAlex Profile") if profile.openalex_id else "",
            orcid_id=make_excel_link(f"https://orcid.org/{profile.orcid_id.replace('https://orcid.org/', '')}", "ORCID Profile") if profile.orcid_id else "",
            current_title=profile.current_title or "",
            department=profile.department or "",
            homepage_url=make_excel_link(profile.homepage_url, "Website") if profile.homepage_url else "",
            primary_topics_or_concepts="; ".join(profile.primary_topics) if profile.primary_topics else "",
            matched_keywords="; ".join(evidence.matched_keywords) if evidence.matched_keywords else "",
            recent_pubs_count=len(recent_pubs),
            example_pub_titles=example_titles or "",
            active_grants_count=len(active_grants),
            funders=funders or "",
            grant_ids=grant_ids or "",
            grant_urls="; ".join([make_excel_link(url, f"Grant {i+1}") for i, url in enumerate(grant_urls.split("; ")) if url.strip()]) if grant_urls else "",
            grant_confidence=grant_confidence or "",
            is_recruiting=recruitment.is_recruiting if recruitment else None,  # None means unknown
            recruiting_snippet=recruitment.snippet if recruitment else "",
            recruiting_url=make_excel_link(recruitment.url, "Recruiting Page") if recruitment and recruitment.url else "",
            concept_score=round(scores.concept_score, 3) if scores.concept_score is not None else 0.0,
            recent_works_score=round(scores.recent_works_score, 3) if scores.recent_works_score is not None else 0.0,
            grant_score=round(scores.grant_score, 3) if scores.grant_score is not None else 0.0,
            final_score=round(scores.final_score, 3) if scores.final_score is not None else 0.0,
            evidence_urls="; ".join(evidence.evidence_urls) if evidence.evidence_urls else "",
            last_seen_utc=evidence.last_seen_utc.isoformat() if evidence.last_seen_utc else "",
            sources_used="; ".join(evidence.sources_used) if evidence.sources_used else ""
        )
        
        csv_rows.append(csv_row)
    
    return csv_rows


def write_csv_to_string(csv_rows: List[CSVRow]) -> str:
    """Write CSV rows to string format."""
    output = io.StringIO()
    
    # Define column order exactly as specified
    fieldnames = [
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
    
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(fieldnames)
    
    # Write data rows
    for row in csv_rows:
        row_dict = row.model_dump()
        writer.writerow([row_dict.get(field, '') for field in fieldnames])
    
    return output.getvalue()


def write_csv_to_file(csv_rows: List[CSVRow], filepath: str) -> None:
    """Write CSV rows to file."""
    csv_content = write_csv_to_string(csv_rows)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        f.write(csv_content)


def create_csv_download(results: List[AuthorResult]) -> bytes:
    """Create CSV download content as bytes."""
    csv_rows = convert_results_to_csv_rows(results)
    csv_string = write_csv_to_string(csv_rows)
    return csv_string.encode('utf-8')


def validate_csv_structure(csv_rows: List[CSVRow]) -> Dict[str, Any]:
    """Validate CSV structure and return summary."""
    if not csv_rows:
        return {"valid": False, "error": "No data to validate"}
    
    # Check required fields
    required_fields = ['institution_name', 'author_name', 'openalex_id']
    missing_data = []
    
    for i, row in enumerate(csv_rows):
        row_dict = row.model_dump()
        for field in required_fields:
            if not row_dict.get(field):
                missing_data.append(f"Row {i+1}: missing {field}")
    
    # Check evidence URLs format
    evidence_url_issues = []
    for i, row in enumerate(csv_rows):
        if row.evidence_urls:
            urls = row.evidence_urls.split(';')
            for url in urls:
                url = url.strip()
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    evidence_url_issues.append(f"Row {i+1}: invalid URL format: {url}")
    
    # Summary stats
    total_rows = len(csv_rows)
    authors_with_orcid = sum(1 for row in csv_rows if row.orcid_id)
    authors_recruiting = sum(1 for row in csv_rows if row.is_recruiting)
    authors_with_grants = sum(1 for row in csv_rows if row.active_grants_count > 0)
    
    validation_result = {
        "valid": len(missing_data) == 0 and len(evidence_url_issues) == 0,
        "total_rows": total_rows,
        "authors_with_orcid": authors_with_orcid,
        "authors_recruiting": authors_recruiting,
        "authors_with_active_grants": authors_with_grants,
        "missing_data": missing_data,
        "url_issues": evidence_url_issues,
        "avg_final_score": sum(row.final_score for row in csv_rows) / total_rows if total_rows > 0 else 0
    }
    
    return validation_result