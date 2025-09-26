const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'APIError'
  }
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw new APIError(response.status, errorData.error || `HTTP ${response.status}`)
    }

    return response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }

    // Handle network errors
    throw new APIError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

export const api = {
  // Program endpoints
  searchPrograms: (params: {
    q?: string
    degree?: string
    country?: string
    modality?: string
    page?: number
    per_page?: number
    min_confidence?: number
  }) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })

    return fetchAPI<import('@/types/api').ProgramSearchResponse>(
      `/api/v1/programs/search?${searchParams}`
    )
  },

  getProgramDetail: (programId: string) =>
    fetchAPI<import('@/types/api').ProgramDetailResponse>(
      `/api/v1/programs/${programId}`
    ),

  getStats: () =>
    fetchAPI<{
      total_programs: number
      total_institutions: number
      total_countries: number
      average_confidence: number
      high_confidence_programs: number
      programs_with_requirements: number
    }>(`/api/v1/programs/stats/summary`),

  // Review endpoints
  getPendingReviews: (params: {
    page?: number
    per_page?: number
    min_confidence?: number
  }) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })

    return fetchAPI<import('@/types/api').PaginatedResponse<any>>(
      `/api/v1/review/pending?${searchParams}`
    )
  },

  getRequirementSetDetails: (requirementSetId: string) =>
    fetchAPI<import('@/types/api').RequirementSetDetail>(
      `/api/v1/review/${requirementSetId}/details`
    ),

  approveRequirementSet: (requirementSetId: string, request: import('@/types/api').ReviewRequest) =>
    fetchAPI<import('@/types/api').ReviewResponse>(
      `/api/v1/review/${requirementSetId}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    ),

  rejectRequirementSet: (requirementSetId: string, request: import('@/types/api').ReviewRequest) =>
    fetchAPI<import('@/types/api').ReviewResponse>(
      `/api/v1/review/${requirementSetId}/reject`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    ),

  batchApprove: (params: {
    confidence_threshold?: number
    max_batch_size?: number
  }) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })

    return fetchAPI<import('@/types/api').ReviewResponse[]>(
      `/api/v1/review/batch-approve?${searchParams}`,
      { method: 'POST' }
    )
  },

  getReviewStats: () =>
    fetchAPI<{
      status_counts: Array<{
        status: string
        count: number
        avg_confidence: number
      }>
      validation_issues: Array<{
        severity: string
        count: number
      }>
      recent_activity: Array<{
        review_date: string
        approved_count: number
        rejected_count: number
      }>
      high_confidence_pending: number
    }>(`/api/v1/review/stats`),

  // Health check
  health: () =>
    fetchAPI<{
      status: string
      timestamp: string
      version: string
      database: boolean
    }>(`/health`),
}

export { APIError }