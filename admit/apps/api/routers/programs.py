from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse

from models.responses import (
    ProgramSearchResponse, ProgramDetailResponse, FitCheckRequest,
    FitCheckResponse, PaginatedResponse
)
from services.program_service import ProgramService

router = APIRouter(prefix="/programs", tags=["programs"])


def get_program_service() -> ProgramService:
    """Dependency to get program service."""
    return ProgramService()


@router.get("/search", response_model=ProgramSearchResponse)
async def search_programs(
    q: Optional[str] = Query(None, description="Search query"),
    degree: Optional[str] = Query(None, description="Degree type (MS, PhD, etc.)"),
    country: Optional[str] = Query(None, description="Country code"),
    modality: Optional[str] = Query(None, description="Modality (in_person, online, hybrid)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence score"),
    program_service: ProgramService = Depends(get_program_service)
):
    """Search for graduate programs with filtering and pagination."""

    try:
        programs, total = await program_service.search_programs(
            query=q,
            degree=degree,
            country=country,
            modality=modality,
            page=page,
            per_page=per_page,
            min_confidence=min_confidence
        )

        total_pages = (total + per_page - 1) // per_page

        filters_applied = {}
        if q:
            filters_applied['query'] = q
        if degree:
            filters_applied['degree'] = degree
        if country:
            filters_applied['country'] = country
        if modality:
            filters_applied['modality'] = modality
        if min_confidence != 0.7:
            filters_applied['min_confidence'] = min_confidence

        return ProgramSearchResponse(
            items=programs,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            filters_applied=filters_applied,
            search_query=q
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{program_id}", response_model=ProgramDetailResponse)
async def get_program_detail(
    program_id: UUID,
    program_service: ProgramService = Depends(get_program_service)
):
    """Get detailed information for a specific program."""

    try:
        program = await program_service.get_program_detail(program_id)
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")

        return program

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get program details: {str(e)}")


@router.post("/fit-check", response_model=List[FitCheckResponse])
async def calculate_program_fit(
    fit_request: FitCheckRequest,
    q: Optional[str] = Query(None, description="Search query to filter programs"),
    degree: Optional[str] = Query(None, description="Degree type filter"),
    country: Optional[str] = Query(None, description="Country filter"),
    modality: Optional[str] = Query(None, description="Modality filter"),
    max_results: int = Query(50, ge=1, le=200, description="Maximum results to analyze"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="Minimum confidence for programs"),
    program_service: ProgramService = Depends(get_program_service)
):
    """
    Calculate fit scores for programs based on student profile.

    This endpoint:
    1. Searches for programs matching the optional filters
    2. Calculates fit scores based on the provided student profile
    3. Returns programs ranked by fit score
    """

    try:
        # Search for programs to evaluate
        programs, _ = await program_service.search_programs(
            query=q,
            degree=degree or fit_request.degree_level,  # Use degree from fit request if not provided
            country=country,
            modality=modality,
            page=1,
            per_page=max_results,
            min_confidence=min_confidence
        )

        if not programs:
            return []

        # Calculate fit scores
        fit_results = await program_service.calculate_fit(fit_request, programs)

        # Limit results and add additional filtering
        fit_results = fit_results[:max_results]

        # Filter out programs with very poor fit (< 20%)
        fit_results = [
            result for result in fit_results
            if result.fit_score.overall_score >= 20
        ]

        return fit_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fit calculation failed: {str(e)}")


@router.get("/degrees/options")
async def get_degree_options():
    """Get available degree options."""
    degrees = [
        {"code": "MS", "name": "Master of Science"},
        {"code": "MA", "name": "Master of Arts"},
        {"code": "MEng", "name": "Master of Engineering"},
        {"code": "MBA", "name": "Master of Business Administration"},
        {"code": "PhD", "name": "Doctor of Philosophy"},
        {"code": "EdD", "name": "Doctor of Education"},
        {"code": "JD", "name": "Juris Doctor"},
        {"code": "MD", "name": "Doctor of Medicine"},
        {"code": "DDS", "name": "Doctor of Dental Surgery"},
        {"code": "PharmD", "name": "Doctor of Pharmacy"},
        {"code": "DVM", "name": "Doctor of Veterinary Medicine"},
        {"code": "Other", "name": "Other"}
    ]
    return {"degrees": degrees}


@router.get("/countries/options")
async def get_country_options(
    program_service: ProgramService = Depends(get_program_service)
):
    """Get available country options with program counts."""
    try:
        query = """
            SELECT
                country,
                COUNT(*) as program_count
            FROM program_search_view
            WHERE avg_confidence >= 0.5
            GROUP BY country
            ORDER BY program_count DESC
        """

        from database import db
        results = await db.execute_query(query)

        countries = [
            {"code": row['country'], "count": row['program_count']}
            for row in results
        ]

        return {"countries": countries}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get countries: {str(e)}")


@router.get("/modalities/options")
async def get_modality_options():
    """Get available modality options."""
    modalities = [
        {"code": "in_person", "name": "In Person"},
        {"code": "online", "name": "Online"},
        {"code": "hybrid", "name": "Hybrid"}
    ]
    return {"modalities": modalities}


@router.get("/stats/summary")
async def get_program_stats(
    program_service: ProgramService = Depends(get_program_service)
):
    """Get summary statistics about programs in the database."""
    try:
        query = """
            SELECT
                COUNT(*) as total_programs,
                COUNT(DISTINCT institution_name) as total_institutions,
                COUNT(DISTINCT country) as total_countries,
                AVG(avg_confidence) as average_confidence,
                COUNT(*) FILTER (WHERE avg_confidence >= 0.9) as high_confidence_count,
                COUNT(*) FILTER (WHERE requirement_count > 0) as programs_with_requirements
            FROM program_search_view
            WHERE avg_confidence >= 0.5
        """

        from database import db
        result = await db.execute_one(query)

        return {
            "total_programs": result['total_programs'],
            "total_institutions": result['total_institutions'],
            "total_countries": result['total_countries'],
            "average_confidence": float(result['average_confidence']) if result['average_confidence'] else 0,
            "high_confidence_programs": result['high_confidence_count'],
            "programs_with_requirements": result['programs_with_requirements']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")