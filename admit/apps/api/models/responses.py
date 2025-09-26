from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    database: bool


class ProgramSearchResult(BaseModel):
    """Program search result item."""
    program_id: UUID
    program_name: str
    degree: str
    department_name: str
    school_name: str
    institution_name: str
    country: str
    institution_website: Optional[str] = None
    program_website: Optional[str] = None
    priority_tier: int
    modalities: List[str]
    schedules: List[str]
    last_updated: datetime
    avg_confidence: float
    requirement_count: int


class ProgramSearchResponse(PaginatedResponse):
    """Program search response."""
    items: List[ProgramSearchResult]
    filters_applied: Dict[str, Any]
    search_query: Optional[str] = None


class TestRequirementDetail(BaseModel):
    """Detailed test requirement."""
    test_name: str
    status: str  # required, optional, recommended, not_accepted, waived, unknown
    min_score: Optional[int] = None
    section_minima: Optional[Dict[str, int]] = None
    institution_code: Optional[str] = None
    validity_months: Optional[int] = None


class DeadlineDetail(BaseModel):
    """Deadline information."""
    deadline_type: str
    deadline_date: datetime
    is_rolling: bool
    audience: str  # domestic, international, both


class ContactDetail(BaseModel):
    """Contact information."""
    contact_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ProgramDetailResponse(BaseModel):
    """Detailed program information."""
    program_id: UUID
    program_name: str
    degree: str
    department_name: str
    school_name: str
    institution_name: str
    country: str

    # URLs
    institution_website: Optional[str] = None
    program_website: Optional[str] = None

    # Program details
    priority_tier: int
    modalities: List[str]
    schedules: List[str]
    cip_code: Optional[str] = None

    # Requirements
    test_requirements: List[TestRequirementDetail]
    deadlines: List[DeadlineDetail]
    contacts: List[ContactDetail]

    # Application components
    sop_required: Optional[bool] = None
    recommendation_letters_min: Optional[int] = None
    recommendation_letters_max: Optional[int] = None
    resume_required: Optional[bool] = None
    portfolio_required: Optional[bool] = None
    writing_sample_required: Optional[bool] = None
    prerequisites: List[str] = Field(default_factory=list)
    min_gpa: Optional[float] = None
    min_experience_years: Optional[int] = None
    application_fee: Optional[float] = None

    # International requirements
    transcript_evaluation_required: bool = False
    funding_documentation_required: bool = True
    english_exemptions: Optional[str] = None

    # Metadata
    last_verified: datetime
    confidence_score: float
    source_url: str
    status: str


class FitCheckRequest(BaseModel):
    """Fit check request."""
    degree_level: str = Field(..., description="Target degree level")
    field_of_study: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0, le=4.0)

    # Test scores
    gre_total: Optional[int] = Field(None, ge=260, le=340)
    gre_verbal: Optional[int] = Field(None, ge=130, le=170)
    gre_quant: Optional[int] = Field(None, ge=130, le=170)
    gre_writing: Optional[float] = Field(None, ge=0, le=6)

    gmat_total: Optional[int] = Field(None, ge=200, le=800)

    toefl_total: Optional[int] = Field(None, ge=0, le=120)
    ielts_total: Optional[float] = Field(None, ge=0, le=9)
    det_total: Optional[int] = Field(None, ge=10, le=160)

    # Background
    work_experience_years: Optional[int] = Field(None, ge=0)
    research_experience: bool = False
    publications: int = Field(default=0, ge=0)

    # Preferences
    preferred_countries: List[str] = Field(default_factory=list)
    preferred_modalities: List[str] = Field(default_factory=list)
    max_application_fee: Optional[float] = None


class FitScore(BaseModel):
    """Program fit score."""
    overall_score: float = Field(..., ge=0, le=100)
    test_score_match: float = Field(..., ge=0, le=100)
    gpa_match: float = Field(..., ge=0, le=100)
    experience_match: float = Field(..., ge=0, le=100)
    preference_match: float = Field(..., ge=0, le=100)
    missing_requirements: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class FitCheckResponse(BaseModel):
    """Fit check response."""
    program_id: UUID
    program_name: str
    institution_name: str
    degree: str
    fit_score: FitScore
    estimated_admission_probability: float = Field(..., ge=0, le=1)


class ReviewRequest(BaseModel):
    """Requirement set review request."""
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = None
    confidence_override: Optional[float] = Field(None, ge=0, le=1)


class ReviewResponse(BaseModel):
    """Review action response."""
    requirement_set_id: UUID
    action: str
    reviewer_id: Optional[UUID] = None
    timestamp: datetime
    notes: Optional[str] = None