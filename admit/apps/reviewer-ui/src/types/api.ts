// API Response Types matching our FastAPI backend

export interface ProgramSearchResult {
  program_id: string
  program_name: string
  degree: string
  department_name: string
  school_name: string
  institution_name: string
  country: string
  institution_website?: string
  program_website?: string
  priority_tier: number
  modalities: string[]
  schedules: string[]
  last_updated: string
  avg_confidence: number
  requirement_count: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface ProgramSearchResponse extends PaginatedResponse<ProgramSearchResult> {
  filters_applied: Record<string, any>
  search_query?: string
}

export interface TestRequirementDetail {
  test_name: string
  status: string
  min_score?: number
  section_minima?: Record<string, number>
  institution_code?: string
  validity_months?: number
}

export interface DeadlineDetail {
  deadline_type: string
  deadline_date: string
  is_rolling: boolean
  audience: string
}

export interface ContactDetail {
  contact_type: string
  email?: string
  phone?: string
  address?: string
}

export interface ProgramDetailResponse {
  program_id: string
  program_name: string
  degree: string
  department_name: string
  school_name: string
  institution_name: string
  country: string

  institution_website?: string
  program_website?: string

  priority_tier: number
  modalities: string[]
  schedules: string[]
  cip_code?: string

  test_requirements: TestRequirementDetail[]
  deadlines: DeadlineDetail[]
  contacts: ContactDetail[]

  sop_required?: boolean
  recommendation_letters_min?: number
  recommendation_letters_max?: number
  resume_required?: boolean
  portfolio_required?: boolean
  writing_sample_required?: boolean
  prerequisites: string[]
  min_gpa?: number
  min_experience_years?: number
  application_fee?: number

  transcript_evaluation_required: boolean
  funding_documentation_required: boolean
  english_exemptions?: string

  last_verified: string
  confidence_score: number
  source_url: string
  status: string
}

export interface ReviewRequest {
  action: 'approve' | 'reject'
  notes?: string
  confidence_override?: number
}

export interface ReviewResponse {
  requirement_set_id: string
  action: string
  reviewer_id?: string
  timestamp: string
  notes?: string
}

export interface RequirementSetDetail {
  basic_info: {
    id: string
    source_url: string
    confidence: number
    status: string
    last_verified_at: string
    parse_version: string
    extraction_method: string
    created_at: string
    program_name: string
    degree: string
    department_name: string
    institution_name: string
    term_name: string
    term_year: number
  }
  validation_issues: Array<{
    field_name: string
    severity: string
    message: string
    current_value: string
    expected_value: string
  }>
  citations: Array<{
    field_name: string
    kind: string
    snippet: string
    selector: string
    page_num?: number
    line_start?: number
    line_end?: number
  }>
  requirements_data: {
    tests?: any
    components?: any
    intl?: any
    deadlines?: any[]
    contacts?: any[]
  }
}