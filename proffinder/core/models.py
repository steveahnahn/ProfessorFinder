from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Institution(BaseModel):
    name: str
    ror_id: str
    display_name: str
    country: Optional[str] = None
    openalex_id: Optional[str] = None


class Grant(BaseModel):
    id: str
    title: str
    funder: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = False
    confidence: str = "unknown"  # "known", "estimated", "unknown"
    url: str
    pi_names: List[str] = Field(default_factory=list)


class Publication(BaseModel):
    id: str
    title: str
    year: int
    doi: Optional[str] = None
    url: str
    matched_keywords: List[str] = Field(default_factory=list)


class AuthorProfile(BaseModel):
    openalex_id: str
    name: str
    orcid_id: Optional[str] = None
    current_title: Optional[str] = None
    department: Optional[str] = None
    homepage_url: Optional[str] = None
    primary_topics: List[str] = Field(default_factory=list)
    institution: Optional[Institution] = None
    recent_publications: List['Publication'] = Field(default_factory=list)
    recruitment: Optional['RecruitmentSignal'] = None
    grants: List['Grant'] = Field(default_factory=list)
    # Scoring fields
    scores: Optional['ScoreComponents'] = None
    evidence: Optional['AuthorEvidence'] = None


class RecruitmentSignal(BaseModel):
    is_recruiting: bool = False
    snippet: Optional[str] = None
    url: Optional[str] = None


class AuthorEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    profile: AuthorProfile
    recent_publications: List[Publication] = Field(default_factory=list)
    grants: List[Grant] = Field(default_factory=list)
    recruitment: Optional[RecruitmentSignal] = Field(default_factory=lambda: RecruitmentSignal())
    matched_keywords: List[str] = Field(default_factory=list)
    evidence_urls: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    last_seen_utc: datetime = Field(default_factory=datetime.utcnow)


class ScoreComponents(BaseModel):
    concept_score: float = 0.0
    recent_works_score: float = 0.0
    grant_score: float = 0.0
    final_score: float = 0.0
    rationale: str = ""


class AuthorResult(BaseModel):
    evidence: AuthorEvidence
    scores: ScoreComponents


class CSVRow(BaseModel):
    institution_name: str
    institution_ror: str
    author_name: str
    openalex_id: str
    orcid_id: Optional[str]
    current_title: Optional[str]
    department: Optional[str]
    homepage_url: Optional[str]
    primary_topics_or_concepts: str
    matched_keywords: str
    recent_pubs_count: int
    example_pub_titles: str
    active_grants_count: int
    funders: str
    grant_ids: str
    grant_urls: str
    grant_confidence: str
    is_recruiting: Optional[bool]  # None means unknown
    recruiting_snippet: Optional[str]
    recruiting_url: Optional[str]
    concept_score: float
    recent_works_score: float
    grant_score: float
    final_score: float
    evidence_urls: str
    last_seen_utc: str
    sources_used: str


class SearchRequest(BaseModel):
    institutions: List[str]
    keywords: List[str]
    years_window: int = 5


class ExpandedKeywords(BaseModel):
    original: List[str]
    openalex_concepts: List[str] = Field(default_factory=list)
    mesh_terms: List[str] = Field(default_factory=list)
    all_expanded: List[str] = Field(default_factory=list)