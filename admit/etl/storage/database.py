"""
Database Storage Module
Handles storing extracted requirements data in Supabase
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import asyncpg
from datetime import datetime

from schemas.requirements import ExtractedRequirements, ValidationReport
import logging

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """Handles storing ETL results in the database"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        self.pool = None

    async def _get_pool(self):
        """Get database connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        return self.pool

    async def store_requirements(self, requirements: ExtractedRequirements, validation_report: ValidationReport):
        """Store extracted requirements in the database"""

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Step 1: Find or create institution
                    institution_id = await self._ensure_institution(conn, requirements.program)

                    # Step 2: Find or create department
                    department_id = await self._ensure_department(conn, institution_id, requirements.program)

                    # Step 3: Find or create program
                    program_id = await self._ensure_program(conn, department_id, requirements.program)

                    # Step 4: Find or create track
                    track_id = await self._ensure_track(conn, program_id, requirements.program)

                    # Step 5: Find or create term (Fall 2024 default)
                    term_id = await self._ensure_term(conn, "Fall", 2024)

                    # Step 6: Create requirement set
                    requirement_set_id = await self._create_requirement_set(
                        conn, track_id, term_id, requirements
                    )

                    # Step 7: Store detailed requirements
                    await self._store_test_requirements(conn, requirement_set_id, requirements.tests)
                    await self._store_components(conn, requirement_set_id, requirements)
                    await self._store_deadlines(conn, requirement_set_id, requirements)
                    await self._store_contacts(conn, requirement_set_id, requirements)

                    # Step 8: Store citations and validation issues
                    await self._store_citations(conn, requirement_set_id, requirements.provenance)
                    await self._store_validation_issues(conn, requirement_set_id, validation_report)

                    logger.info(f"Successfully stored requirements for {requirements.program.program_name}")
                    return requirement_set_id

                except Exception as e:
                    logger.error(f"Error storing requirements: {str(e)}")
                    raise

    async def _ensure_institution(self, conn, program_info) -> UUID:
        """Find or create institution"""
        result = await conn.fetchrow(
            "SELECT id FROM institutions WHERE name = $1",
            program_info.institution
        )

        if result:
            return result['id']

        # Create new institution
        institution_id = uuid4()
        await conn.execute("""
            INSERT INTO institutions (id, name, website, country, priority_tier, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, institution_id, program_info.institution, program_info.website,
            "United States", 1)  # Default values

        logger.info(f"Created institution: {program_info.institution}")
        return institution_id

    async def _ensure_department(self, conn, institution_id: UUID, program_info) -> UUID:
        """Find or create department"""
        result = await conn.fetchrow(
            "SELECT id FROM departments WHERE institution_id = $1 AND name = $2",
            institution_id, program_info.department
        )

        if result:
            return result['id']

        # Create new department
        department_id = uuid4()
        await conn.execute("""
            INSERT INTO departments (id, institution_id, name, created_at)
            VALUES ($1, $2, $3, NOW())
        """, department_id, institution_id, program_info.department)

        logger.info(f"Created department: {program_info.department}")
        return department_id

    async def _ensure_program(self, conn, department_id: UUID, program_info) -> UUID:
        """Find or create program"""
        result = await conn.fetchrow(
            "SELECT id FROM program WHERE department_id = $1 AND name = $2 AND degree = $3",
            department_id, program_info.program_name, program_info.degree.value
        )

        if result:
            return result['id']

        # Create new program
        program_id = uuid4()
        await conn.execute("""
            INSERT INTO program (id, department_id, name, degree, website, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, program_id, department_id, program_info.program_name,
            program_info.degree.value, program_info.website)

        logger.info(f"Created program: {program_info.program_name}")
        return program_id

    async def _ensure_track(self, conn, program_id: UUID, program_info) -> UUID:
        """Find or create track"""
        # For now, create a default track since we don't have track-specific data
        result = await conn.fetchrow(
            "SELECT id FROM track WHERE program_id = $1 LIMIT 1",
            program_id
        )

        if result:
            return result['id']

        # Create new track
        track_id = uuid4()

        await conn.execute("""
            INSERT INTO track (id, program_id, modality, schedule, honors_flag, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
        """, track_id, program_id, "in_person", "full_time", False)

        logger.info(f"Created track for program")
        return track_id

    async def _ensure_term(self, conn, season: str, year: int) -> UUID:
        """Find or create term"""
        result = await conn.fetchrow(
            "SELECT id FROM term WHERE name = $1 AND year = $2",
            season, year
        )

        if result:
            return result['id']

        # Create new term
        term_id = uuid4()
        await conn.execute("""
            INSERT INTO term (id, name, year, created_at)
            VALUES ($1, $2, $3, NOW())
        """, term_id, season, year)

        logger.info(f"Created term: {season} {year}")
        return term_id

    async def _create_requirement_set(self, conn, track_id: UUID, term_id: UUID, requirements: ExtractedRequirements) -> UUID:
        """Create requirement set"""
        requirement_set_id = uuid4()

        await conn.execute("""
            INSERT INTO requirement_set (
                id, track_id, term_id, source_url, confidence, status,
                extraction_method, last_verified_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW(), NOW())
        """, requirement_set_id, track_id, term_id,
            requirements.provenance.source_url,
            requirements.audit.confidence,
            'draft',  # Will be reviewed
            requirements.audit.extraction_method)

        return requirement_set_id

    async def _store_test_requirements(self, conn, requirement_set_id: UUID, tests):
        """Store test requirements"""
        await conn.execute("""
            INSERT INTO tests (
                requirement_set_id, gre_status, gmat_status, toefl_min, ielts_min,
                det_min, code_toefl, code_gre, score_validity_months
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, requirement_set_id,
            tests.gre_status.value if tests.gre_status else 'unknown',
            tests.gmat_status.value if tests.gmat_status else 'unknown',
            tests.toefl_min,
            tests.ielts_min,
            tests.det_min,
            tests.code_toefl,
            tests.code_gre,
            24  # Default validity
        )

    async def _store_components(self, conn, requirement_set_id: UUID, requirements: ExtractedRequirements):
        """Store application components"""
        await conn.execute("""
            INSERT INTO components (
                requirement_set_id, sop_required, rec_min, rec_max,
                resume_required, portfolio_required, gpa_min
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, requirement_set_id,
            requirements.components.sop_required or True,
            requirements.components.rec_min or 2,
            requirements.components.rec_max or 3,
            requirements.components.resume_required or True,
            requirements.components.portfolio_required or False,
            requirements.components.gpa_min or 3.0
        )

    async def _store_deadlines(self, conn, requirement_set_id: UUID, requirements: ExtractedRequirements):
        """Store deadlines - placeholder implementation"""
        # This would store actual deadline data from requirements
        pass

    async def _store_contacts(self, conn, requirement_set_id: UUID, requirements: ExtractedRequirements):
        """Store contact information - placeholder implementation"""
        # This would store actual contact data from requirements
        pass

    async def _store_citations(self, conn, requirement_set_id: UUID, provenance):
        """Store citation information"""
        for citation in provenance.citations:
            await conn.execute("""
                INSERT INTO citation (
                    requirement_set_id, field_name, kind, snippet,
                    selector, page_num, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, requirement_set_id, citation.field_name, citation.kind,
                citation.snippet, citation.selector, citation.page_num)

    async def _store_validation_issues(self, conn, requirement_set_id: UUID, validation_report: ValidationReport):
        """Store validation issues"""
        for issue in validation_report.issues:
            await conn.execute("""
                INSERT INTO validation_issue (
                    requirement_set_id, field_name, severity, message,
                    current_value, expected_value, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, requirement_set_id, issue.field_name, issue.severity.value,
                issue.message, str(issue.current_value), str(issue.expected_value))

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()