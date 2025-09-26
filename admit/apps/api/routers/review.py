from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query

from models.responses import (
    ReviewRequest, ReviewResponse, PaginatedResponse
)
from services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


def get_review_service() -> ReviewService:
    """Dependency to get review service."""
    return ReviewService()


@router.get("/pending")
async def get_pending_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence filter"),
    review_service: ReviewService = Depends(get_review_service)
):
    """Get requirement sets pending human review."""

    try:
        reviews, total = await review_service.get_pending_reviews(
            page=page,
            per_page=per_page,
            min_confidence=min_confidence
        )

        total_pages = (total + per_page - 1) // per_page

        return PaginatedResponse(
            items=reviews,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending reviews: {str(e)}")


@router.get("/{requirement_set_id}/details")
async def get_requirement_set_details(
    requirement_set_id: UUID,
    review_service: ReviewService = Depends(get_review_service)
):
    """Get detailed information about a requirement set for review."""

    try:
        details = await review_service.get_requirement_set_details(requirement_set_id)
        if not details:
            raise HTTPException(status_code=404, detail="Requirement set not found")

        return details

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get requirement set details: {str(e)}")


@router.post("/{requirement_set_id}/approve", response_model=ReviewResponse)
async def approve_requirement_set(
    requirement_set_id: UUID,
    request: ReviewRequest,
    reviewer_id: Optional[UUID] = None,  # In production, this would come from auth
    review_service: ReviewService = Depends(get_review_service)
):
    """Approve a requirement set."""

    if request.action != "approve":
        raise HTTPException(status_code=400, detail="Invalid action for approve endpoint")

    try:
        result = await review_service.approve_requirement_set(
            requirement_set_id=requirement_set_id,
            reviewer_id=reviewer_id,
            notes=request.notes,
            confidence_override=request.confidence_override
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve requirement set: {str(e)}")


@router.post("/{requirement_set_id}/reject", response_model=ReviewResponse)
async def reject_requirement_set(
    requirement_set_id: UUID,
    request: ReviewRequest,
    reviewer_id: Optional[UUID] = None,  # In production, this would come from auth
    review_service: ReviewService = Depends(get_review_service)
):
    """Reject a requirement set, sending it back to draft status."""

    if request.action != "reject":
        raise HTTPException(status_code=400, detail="Invalid action for reject endpoint")

    try:
        result = await review_service.reject_requirement_set(
            requirement_set_id=requirement_set_id,
            reviewer_id=reviewer_id,
            notes=request.notes
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject requirement set: {str(e)}")


@router.post("/batch-approve", response_model=List[ReviewResponse])
async def batch_approve_high_confidence(
    confidence_threshold: float = Query(0.95, ge=0.8, le=1.0, description="Confidence threshold for auto-approval"),
    max_batch_size: int = Query(100, ge=1, le=500, description="Maximum number to approve in one batch"),
    reviewer_id: Optional[UUID] = None,  # In production, this would come from auth
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Batch approve high-confidence requirement sets.

    This is useful for processing large numbers of high-quality extractions
    that don't need individual human review.
    """

    try:
        results = await review_service.batch_approve_high_confidence(
            confidence_threshold=confidence_threshold,
            reviewer_id=reviewer_id,
            max_batch_size=max_batch_size
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch approval failed: {str(e)}")


@router.get("/stats")
async def get_review_stats(
    review_service: ReviewService = Depends(get_review_service)
):
    """Get review workflow statistics."""

    try:
        from database import db

        # Get review status counts
        status_query = """
            SELECT
                status,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence
            FROM requirement_set
            GROUP BY status
        """

        status_results = await db.execute_query(status_query)

        # Get validation issue counts
        validation_query = """
            SELECT
                vi.severity,
                COUNT(*) as count
            FROM validation_issue vi
            JOIN requirement_set rs ON vi.requirement_set_id = rs.id
            WHERE vi.resolved_at IS NULL
            GROUP BY vi.severity
        """

        validation_results = await db.execute_query(validation_query)

        # Get recent review activity
        activity_query = """
            SELECT
                DATE_TRUNC('day', updated_at) as review_date,
                COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
                COUNT(*) FILTER (WHERE status = 'draft') as rejected_count
            FROM requirement_set
            WHERE updated_at >= NOW() - INTERVAL '7 days'
              AND status IN ('approved', 'draft')
            GROUP BY DATE_TRUNC('day', updated_at)
            ORDER BY review_date DESC
        """

        activity_results = await db.execute_query(activity_query)

        # Get high-confidence pending count
        pending_query = """
            SELECT COUNT(*) as count
            FROM requirement_set
            WHERE status = 'needs_review' AND confidence >= 0.95
        """

        pending_result = await db.execute_one(pending_query)

        return {
            "status_counts": [dict(row) for row in status_results],
            "validation_issues": [dict(row) for row in validation_results],
            "recent_activity": [dict(row) for row in activity_results],
            "high_confidence_pending": pending_result['count']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get review stats: {str(e)}")