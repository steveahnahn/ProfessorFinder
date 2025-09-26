from typing import Optional
from uuid import UUID
from datetime import datetime

from database import db
from models.responses import ReviewRequest, ReviewResponse


class ReviewService:
    """Service for requirement set review operations."""

    async def approve_requirement_set(
        self,
        requirement_set_id: UUID,
        reviewer_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        confidence_override: Optional[float] = None
    ) -> ReviewResponse:
        """Approve a requirement set."""

        # Update the requirement set status
        update_query = """
            UPDATE requirement_set
            SET
                status = 'approved',
                reviewer_id = $2,
                updated_at = NOW()
            WHERE id = $1 AND status IN ('draft', 'needs_review')
            RETURNING id, status, updated_at
        """

        result = await db.execute_one(update_query, requirement_set_id, reviewer_id)
        if not result:
            raise ValueError("Requirement set not found or already processed")

        # Apply confidence override if provided
        if confidence_override is not None:
            confidence_query = """
                UPDATE requirement_set
                SET confidence = $2
                WHERE id = $1
            """
            await db.execute_one(confidence_query, requirement_set_id, confidence_override)

        # Log the review action
        if notes:
            await self._log_review_action(requirement_set_id, "approve", reviewer_id, notes)

        return ReviewResponse(
            requirement_set_id=requirement_set_id,
            action="approve",
            reviewer_id=reviewer_id,
            timestamp=result['updated_at'],
            notes=notes
        )

    async def reject_requirement_set(
        self,
        requirement_set_id: UUID,
        reviewer_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> ReviewResponse:
        """Reject a requirement set, moving it back to draft status."""

        # Update the requirement set status
        update_query = """
            UPDATE requirement_set
            SET
                status = 'draft',
                reviewer_id = $2,
                updated_at = NOW()
            WHERE id = $1 AND status = 'needs_review'
            RETURNING id, status, updated_at
        """

        result = await db.execute_one(update_query, requirement_set_id, reviewer_id)
        if not result:
            raise ValueError("Requirement set not found or not in review status")

        # Log the review action
        if notes:
            await self._log_review_action(requirement_set_id, "reject", reviewer_id, notes)

        return ReviewResponse(
            requirement_set_id=requirement_set_id,
            action="reject",
            reviewer_id=reviewer_id,
            timestamp=result['updated_at'],
            notes=notes
        )

    async def get_pending_reviews(
        self,
        page: int = 1,
        per_page: int = 20,
        min_confidence: float = 0.0
    ) -> tuple[list, int]:
        """Get requirement sets pending review."""

        # Build query with confidence filter
        where_clause = "rs.status = 'needs_review' AND rs.confidence >= $1"
        params = [min_confidence, per_page, (page - 1) * per_page]

        # Count query
        count_query = f"""
            SELECT COUNT(*)
            FROM requirement_set rs
            WHERE {where_clause}
        """

        # Main query with program information
        main_query = f"""
            SELECT
                rs.id,
                rs.source_url,
                rs.confidence,
                rs.last_verified_at,
                rs.created_at,
                p.name as program_name,
                p.degree,
                d.name as department_name,
                i.name as institution_name,
                t.name as term_name,
                t.year as term_year,
                COUNT(vi.id) as validation_issue_count
            FROM requirement_set rs
            JOIN track tr ON rs.track_id = tr.id
            JOIN program p ON tr.program_id = p.id
            JOIN department d ON p.department_id = d.id
            JOIN institution i ON d.institution_id = i.id
            JOIN term t ON rs.term_id = t.id
            LEFT JOIN validation_issue vi ON rs.id = vi.requirement_set_id AND vi.resolved_at IS NULL
            WHERE {where_clause}
            GROUP BY rs.id, p.name, p.degree, d.name, i.name, t.name, t.year
            ORDER BY rs.confidence DESC, rs.created_at ASC
            LIMIT $2 OFFSET $3
        """

        # Execute queries
        total_result = await db.execute_one(count_query, min_confidence)
        results = await db.execute_query(main_query, *params)

        return list(results), total_result['count']

    async def get_requirement_set_details(self, requirement_set_id: UUID) -> Optional[dict]:
        """Get detailed information about a requirement set for review."""

        # Get basic requirement set info
        basic_query = """
            SELECT
                rs.id,
                rs.source_url,
                rs.confidence,
                rs.status,
                rs.last_verified_at,
                rs.parse_version,
                rs.extraction_method,
                rs.created_at,
                p.name as program_name,
                p.degree,
                d.name as department_name,
                i.name as institution_name,
                t.name as term_name,
                t.year as term_year
            FROM requirement_set rs
            JOIN track tr ON rs.track_id = tr.id
            JOIN program p ON tr.program_id = p.id
            JOIN department d ON p.department_id = d.id
            JOIN institution i ON d.institution_id = i.id
            JOIN term t ON rs.term_id = t.id
            WHERE rs.id = $1
        """

        basic_info = await db.execute_one(basic_query, requirement_set_id)
        if not basic_info:
            return None

        # Get validation issues
        validation_query = """
            SELECT field_name, severity, message, current_value, expected_value
            FROM validation_issue
            WHERE requirement_set_id = $1 AND resolved_at IS NULL
            ORDER BY
                CASE severity
                    WHEN 'error' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info' THEN 3
                END,
                field_name
        """

        validation_issues = await db.execute_query(validation_query, requirement_set_id)

        # Get citations for traceability
        citations_query = """
            SELECT field_name, kind, snippet, selector, page_num, line_start, line_end
            FROM citation
            WHERE requirement_set_id = $1
            ORDER BY field_name, created_at
        """

        citations = await db.execute_query(citations_query, requirement_set_id)

        # Get extracted requirements data
        requirements_data = await self._get_requirements_data(requirement_set_id)

        return {
            'basic_info': dict(basic_info),
            'validation_issues': [dict(issue) for issue in validation_issues],
            'citations': [dict(citation) for citation in citations],
            'requirements_data': requirements_data
        }

    async def _get_requirements_data(self, requirement_set_id: UUID) -> dict:
        """Get all requirement data for a requirement set."""
        data = {}

        # Get test requirements
        tests_query = """
            SELECT * FROM tests WHERE requirement_set_id = $1
        """
        tests_data = await db.execute_one(tests_query, requirement_set_id)
        if tests_data:
            data['tests'] = dict(tests_data)

        # Get components
        components_query = """
            SELECT * FROM components WHERE requirement_set_id = $1
        """
        components_data = await db.execute_one(components_query, requirement_set_id)
        if components_data:
            data['components'] = dict(components_data)

        # Get international requirements
        intl_query = """
            SELECT * FROM intl WHERE requirement_set_id = $1
        """
        intl_data = await db.execute_one(intl_query, requirement_set_id)
        if intl_data:
            data['intl'] = dict(intl_data)

        # Get deadlines
        deadlines_query = """
            SELECT deadline_type, deadline_ts, rolling_flag, audience
            FROM deadlines
            WHERE requirement_set_id = $1
            ORDER BY deadline_ts
        """
        deadlines_data = await db.execute_query(deadlines_query, requirement_set_id)
        data['deadlines'] = [dict(deadline) for deadline in deadlines_data]

        # Get contacts
        contacts_query = """
            SELECT contact_type, email, phone, address
            FROM contacts
            WHERE requirement_set_id = $1
        """
        contacts_data = await db.execute_query(contacts_query, requirement_set_id)
        data['contacts'] = [dict(contact) for contact in contacts_data]

        return data

    async def _log_review_action(
        self,
        requirement_set_id: UUID,
        action: str,
        reviewer_id: Optional[UUID],
        notes: str
    ):
        """Log review action for audit trail."""
        # This could be implemented as a separate audit table
        # For now, we'll add it as a validation issue with severity 'info'
        log_query = """
            INSERT INTO validation_issue (
                requirement_set_id,
                field_name,
                severity,
                message,
                current_value
            ) VALUES ($1, 'review_action', 'info', $2, $3)
        """

        message = f"Review action: {action}"
        if notes:
            message += f" - {notes}"

        await db.execute_one(
            log_query,
            requirement_set_id,
            message,
            str(reviewer_id) if reviewer_id else "anonymous"
        )

    async def batch_approve_high_confidence(
        self,
        confidence_threshold: float = 0.95,
        reviewer_id: Optional[UUID] = None,
        max_batch_size: int = 100
    ) -> list[ReviewResponse]:
        """Batch approve high-confidence requirement sets."""

        # Find high-confidence requirement sets
        find_query = """
            SELECT id
            FROM requirement_set
            WHERE status = 'needs_review'
              AND confidence >= $1
            ORDER BY confidence DESC, created_at ASC
            LIMIT $2
        """

        candidates = await db.execute_query(find_query, confidence_threshold, max_batch_size)

        results = []
        for candidate in candidates:
            try:
                result = await self.approve_requirement_set(
                    candidate['id'],
                    reviewer_id,
                    f"Auto-approved (confidence >= {confidence_threshold})"
                )
                results.append(result)
            except ValueError:
                # Skip if already processed
                continue

        return results