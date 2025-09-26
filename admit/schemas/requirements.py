"""
Pydantic schemas for Graduate Admissions Requirements
Provides type safety and validation for the entire pipeline
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime, date
import uuid


# =========================================
# ENUMS for consistent values
# =========================================

class TestStatus(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    RECOMMENDED = "recommended"
    NOT_ACCEPTED = "not_accepted"
    WAIVED = "waived"
    UNKNOWN = "unknown"


class Modality(str, Enum):
    IN_PERSON = "in_person"
    ONLINE = "online"
    HYBRID = "hybrid"


class Schedule(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    EXECUTIVE = "executive"
    ACCELERATED = "accelerated"


class Degree(str, Enum):
    MS = "MS"
    MA = "MA"
    MENG = "MEng"
    MBA = "MBA"
    PHD = "PhD"
    EDD = "EdD"
    JD = "JD"
    MD = "MD"
    DDS = "DDS"
    PHARMD = "PharmD"
    DVM = "DVM"
    OTHER = "Other"


class RequirementStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    ARCHIVAL = "archival"


class DeadlineType(str, Enum):
    PRIORITY = "priority"
    REGULAR = "regular"
    FINAL = "final"
    SCHOLARSHIP = "scholarship"
    ROLLING = "rolling"


class Audience(str, Enum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    BOTH = "both"


class CitationKind(str, Enum):
    HTML = "html"
    PDF = "pdf"
    MANUAL = "manual"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# =========================================
# CORE DATA MODELS
# =========================================

class ProgramInfo(BaseModel):
    """Program identification information"""
    institution: str
    school: str
    department: str
    program_name: str
    degree: Degree
    track: str = "Full-Time"
    website: str


class TOEFLSectionMinima(BaseModel):
    """TOEFL section minimum scores"""
    reading: Optional[int] = Field(None, ge=0, le=30)
    listening: Optional[int] = Field(None, ge=0, le=30)
    speaking: Optional[int] = Field(None, ge=0, le=30)
    writing: Optional[int] = Field(None, ge=0, le=30)

    @field_validator('reading', 'listening', 'speaking', 'writing', mode='before')
    @classmethod
    def validate_section_scores(cls, v):
        if v is not None and (v < 0 or v > 30):
            raise ValueError("TOEFL section scores must be between 0 and 30")
        return v


class TestRequirements(BaseModel):
    """Test requirements and scores"""
    # Test statuses
    gre_status: TestStatus = TestStatus.UNKNOWN
    gmat_status: TestStatus = TestStatus.UNKNOWN
    lsat_status: TestStatus = TestStatus.UNKNOWN
    mcat_status: TestStatus = TestStatus.UNKNOWN

    # English proficiency minimums
    toefl_min: Optional[int] = Field(None, ge=0, le=120)
    toefl_section_min: Optional[TOEFLSectionMinima] = None
    ielts_min: Optional[float] = Field(None, ge=0, le=9)
    det_min: Optional[int] = Field(None, ge=0, le=160)  # Duolingo English Test

    # Institution codes
    code_toefl: Optional[str] = Field(None, pattern=r"^[0-9]{4}$")
    code_gre: Optional[str] = Field(None, pattern=r"^[0-9]{4}$")
    code_gmat: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{3,4}$")

    # Score validity
    score_validity_months: int = 24

    @field_validator('toefl_min')
    @classmethod
    def validate_toefl_total(cls, v):
        if v is not None and (v < 0 or v > 120):
            raise ValueError("TOEFL total score must be between 0 and 120")
        return v

    @field_validator('ielts_min')
    @classmethod
    def validate_ielts_score(cls, v):
        if v is not None and (v < 0 or v > 9):
            raise ValueError("IELTS score must be between 0 and 9")
        return v


class ApplicationComponents(BaseModel):
    """Required application components"""
    sop_required: Optional[bool] = None  # Statement of Purpose
    rec_min: Optional[int] = Field(None, ge=0, le=10)
    rec_max: Optional[int] = Field(None, ge=0, le=10)
    resume_required: Optional[bool] = None
    portfolio_required: Optional[bool] = None
    writing_sample_required: Optional[bool] = None
    prereq_list: List[str] = Field(default_factory=list)
    gpa_min: Optional[float] = Field(None, ge=0, le=4.0)
    experience_years_min: Optional[int] = Field(None, ge=0)

    # Fees
    fee_amount: Optional[float] = Field(None, ge=0, le=1000)
    fee_waiver_policy_url: Optional[str] = None

    @model_validator(mode='after')
    def validate_recommendation_counts(self):
        if self.rec_min is not None and self.rec_max is not None and self.rec_min > self.rec_max:
            raise ValueError("Minimum recommendations cannot exceed maximum")
        return self


class InternationalRequirements(BaseModel):
    """International student specific requirements"""
    wes_required: bool = False
    ece_required: bool = False
    transcript_policy: Optional[str] = None
    english_exemptions: Optional[str] = None
    funding_docs_required: bool = True
    i20_processing_time_days: Optional[int] = None
    intl_contact_email: Optional[str] = None


class Deadline(BaseModel):
    """Application deadline"""
    deadline_type: DeadlineType
    deadline_ts: datetime
    rolling_flag: bool = False
    audience: Audience = Audience.BOTH

    @field_validator('deadline_ts')
    @classmethod
    def validate_future_date(cls, v):
        # Allow past dates for archival purposes
        return v


class Contact(BaseModel):
    """Contact information"""
    contact_type: str = "general"
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class Citation(BaseModel):
    """Citation mapping field to source text"""
    field_name: str
    kind: CitationKind
    selector: Optional[str] = None  # For HTML (XPath/CSS)
    page_num: Optional[int] = None  # For PDF
    line_start: Optional[int] = None  # For PDF
    line_end: Optional[int] = None  # For PDF
    snippet: str  # The actual supporting text

    @model_validator(mode='after')
    def validate_citation_fields(self):
        if self.kind == CitationKind.HTML and not self.selector:
            raise ValueError("HTML citations must have a selector")
        elif self.kind == CitationKind.PDF and not self.page_num:
            raise ValueError("PDF citations must have a page number")
        return self


class Provenance(BaseModel):
    """Source and verification information"""
    source_url: str
    citations: List[Citation] = Field(default_factory=list)


class Audit(BaseModel):
    """Audit trail information"""
    last_verified_at: datetime
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    extraction_method: str = "unknown"
    parse_version: str = "1.0"
    rules_version: str = "1.0"
    notes: Optional[str] = None


# =========================================
# MAIN REQUIREMENT MODEL
# =========================================

class ExtractedRequirements(BaseModel):
    """Complete extracted requirements for a program track"""

    # Program identification
    program: ProgramInfo

    # Academic term/cycle
    term_name: str = "Fall"
    term_year: int = Field(..., ge=2024, le=2030)
    round_label: Optional[str] = None  # "Priority", "Round 1", etc.

    # Core requirements
    tests: TestRequirements = Field(default_factory=TestRequirements)
    components: ApplicationComponents = Field(default_factory=ApplicationComponents)
    intl: InternationalRequirements = Field(default_factory=InternationalRequirements)

    # Deadlines and contacts
    deadlines: List[Deadline] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)

    # Metadata
    provenance: Provenance
    audit: Audit

    @field_validator('term_year')
    @classmethod
    def validate_term_year(cls, v):
        current_year = datetime.now().year
        if v < current_year - 1 or v > current_year + 5:
            raise ValueError(f"Term year should be between {current_year-1} and {current_year+5}")
        return v

    model_config = {
        "use_enum_values": True,
        "validate_assignment": True
    }


# =========================================
# VALIDATION MODELS
# =========================================

class ValidationIssue(BaseModel):
    """Validation issue found in requirements"""
    field_name: str
    severity: ValidationSeverity
    message: str
    current_value: Optional[str] = None
    expected_value: Optional[str] = None
    citation_text: Optional[str] = None


class ValidationReport(BaseModel):
    """Complete validation report for a requirement set"""
    requirement_set_id: str
    issues: List[ValidationIssue] = Field(default_factory=list)
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    status_recommendation: RequirementStatus = RequirementStatus.NEEDS_REVIEW
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)


# =========================================
# SEARCH AND RESPONSE MODELS
# =========================================

class ProgramSearchResult(BaseModel):
    """Program search result for public API"""
    program_id: str
    program_name: str
    degree: Degree
    department_name: str
    school_name: str
    institution_name: str
    institution_website: str
    program_website: Optional[str] = None
    modalities: List[Modality] = Field(default_factory=list)
    schedules: List[Schedule] = Field(default_factory=list)
    last_updated: Optional[datetime] = None
    avg_confidence: Optional[float] = None
    priority_tier: int = 3


class FitCheckInput(BaseModel):
    """Input for fit check API"""
    # Test scores
    toefl_total: Optional[int] = Field(None, ge=0, le=120)
    toefl_reading: Optional[int] = Field(None, ge=0, le=30)
    toefl_listening: Optional[int] = Field(None, ge=0, le=30)
    toefl_speaking: Optional[int] = Field(None, ge=0, le=30)
    toefl_writing: Optional[int] = Field(None, ge=0, le=30)
    ielts_total: Optional[float] = Field(None, ge=0, le=9)
    duolingo_total: Optional[int] = Field(None, ge=0, le=160)
    gre_verbal: Optional[int] = Field(None, ge=130, le=170)
    gre_quantitative: Optional[int] = Field(None, ge=130, le=170)
    gre_analytical: Optional[float] = Field(None, ge=0, le=6)
    gmat_total: Optional[int] = Field(None, ge=200, le=800)

    # Academic background
    gpa: Optional[float] = Field(None, ge=0, le=4.0)
    degree_country: Optional[str] = None
    degree_language: Optional[str] = None
    work_experience_years: Optional[int] = Field(None, ge=0)

    # International status
    country_of_citizenship: str = "US"
    needs_visa: bool = False


class FitStatus(str, Enum):
    ELIGIBLE = "eligible"
    BORDERLINE = "borderline"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT_DATA = "insufficient_data"


class FitCheckResult(BaseModel):
    """Result of program fit check"""
    program_id: str
    program_name: str
    institution_name: str
    fit_status: FitStatus
    confidence: float = Field(0.0, ge=0.0, le=1.0)

    # Detailed analysis
    test_requirements_met: Dict[str, bool] = Field(default_factory=dict)
    missing_requirements: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    # Specific scores comparison
    score_analysis: Dict[str, Any] = Field(default_factory=dict)

    # English exemption eligibility
    english_exemption_eligible: bool = False
    exemption_reason: Optional[str] = None


# =========================================
# ETL PIPELINE MODELS
# =========================================

class CrawlResult(BaseModel):
    """Result of crawling a URL"""
    url: str
    status_code: int
    content_type: str
    content_length: int
    storage_path: str
    screenshot_path: Optional[str] = None
    dom_hash: str
    etag: Optional[str] = None
    robots_allowed: bool = True
    crawl_timestamp: datetime = Field(default_factory=datetime.now)


class ParsedSegment(BaseModel):
    """Parsed content segment"""
    source_url: str
    kind: CitationKind
    selector: Optional[str] = None  # For HTML
    page_num: Optional[int] = None  # For PDF
    line_start: Optional[int] = None  # For PDF
    line_end: Optional[int] = None  # For PDF
    text: str
    context_tags: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Result of LLM extraction"""
    extracted_requirements: ExtractedRequirements
    raw_response: str
    model_used: str
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)
    processing_time_seconds: float
    token_usage: Dict[str, int] = Field(default_factory=dict)


# =========================================
# UTILITY FUNCTIONS
# =========================================

def generate_json_schema():
    """Generate JSON schema for LLM validation"""
    return ExtractedRequirements.model_json_schema()


def create_example_requirements() -> ExtractedRequirements:
    """Create an example requirements object for testing"""
    return ExtractedRequirements(
        program=ProgramInfo(
            institution="Example University",
            school="School of Engineering",
            department="Computer Science",
            program_name="Master of Science in Computer Science",
            degree=Degree.MS,
            track="Full-Time",
            website="https://example.edu/cs/ms"
        ),
        term_name="Fall",
        term_year=2026,
        round_label="Priority",
        tests=TestRequirements(
            gre_status=TestStatus.OPTIONAL,
            toefl_min=100,
            toefl_section_min=TOEFLSectionMinima(
                reading=22, listening=22, speaking=22, writing=22
            ),
            ielts_min=7.0,
            code_toefl="1234"
        ),
        components=ApplicationComponents(
            sop_required=True,
            rec_min=2,
            rec_max=3,
            resume_required=True,
            gpa_min=3.0,
            fee_amount=125.0
        ),
        deadlines=[
            Deadline(
                deadline_type=DeadlineType.PRIORITY,
                deadline_ts=datetime(2025, 12, 1, 23, 59),
                audience=Audience.INTERNATIONAL
            )
        ],
        provenance=Provenance(
            source_url="https://example.edu/cs/ms/admissions",
            citations=[
                Citation(
                    field_name="toefl_min",
                    kind=CitationKind.HTML,
                    selector="//h2[text()='English Requirements']/following-sibling::p",
                    snippet="TOEFL minimum 100 with section minima of 22"
                )
            ]
        ),
        audit=Audit(
            last_verified_at=datetime.now(),
            confidence=0.95,
            extraction_method="llm"
        )
    )


if __name__ == "__main__":
    # Test schema generation
    schema = generate_json_schema()
    print("Generated JSON Schema successfully")

    # Test example creation
    example = create_example_requirements()
    print(f"Created example requirements for {example.program.program_name}")

    # Validate example
    try:
        ExtractedRequirements.model_validate(example.model_dump())
        print("Schema validation successful")
    except Exception as e:
        print(f"Schema validation failed: {e}")