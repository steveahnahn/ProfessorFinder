from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from database import db
from models.responses import (
    ProgramSearchResult, ProgramDetailResponse, FitCheckRequest,
    FitCheckResponse, FitScore, TestRequirementDetail,
    DeadlineDetail, ContactDetail
)


class ProgramService:
    """Service for program-related operations."""

    async def search_programs(
        self,
        query: Optional[str] = None,
        degree: Optional[str] = None,
        country: Optional[str] = None,
        modality: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        min_confidence: float = 0.7
    ) -> tuple[List[ProgramSearchResult], int]:
        """Search for programs with filters."""

        # Build the WHERE clause
        where_conditions = ["psv.avg_confidence >= $1"]
        params = [min_confidence]
        param_count = 1

        if query:
            param_count += 1
            where_conditions.append(f"""
                (psv.program_name ILIKE ${param_count} OR
                 psv.institution_name ILIKE ${param_count} OR
                 psv.department_name ILIKE ${param_count})
            """)
            params.append(f"%{query}%")

        if degree:
            param_count += 1
            where_conditions.append(f"psv.degree = ${param_count}")
            params.append(degree)

        if country:
            param_count += 1
            where_conditions.append(f"psv.country = ${param_count}")
            params.append(country)

        if modality:
            param_count += 1
            where_conditions.append(f"${param_count} = ANY(psv.modalities)")
            params.append(modality)

        where_clause = " AND ".join(where_conditions)

        # Count query
        count_query = f"""
            SELECT COUNT(*)
            FROM program_search_view psv
            WHERE {where_clause}
        """

        # Main query
        search_query = f"""
            SELECT
                psv.program_id::uuid,
                psv.program_name,
                psv.degree,
                psv.department_name,
                psv.school_name,
                psv.institution_name,
                psv.country,
                psv.institution_website,
                psv.program_website,
                psv.priority_tier,
                psv.modalities,
                psv.schedules,
                psv.last_updated,
                psv.avg_confidence,
                psv.requirement_count
            FROM program_search_view psv
            WHERE {where_clause}
            ORDER BY psv.priority_tier ASC, psv.avg_confidence DESC, psv.last_updated DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        # Add pagination params
        params.extend([per_page, (page - 1) * per_page])

        # Execute queries
        total_count = await db.execute_one(count_query, *params[:-2])
        results = await db.execute_query(search_query, *params)

        programs = []
        for row in results:
            programs.append(ProgramSearchResult(
                program_id=row['program_id'],
                program_name=row['program_name'],
                degree=row['degree'],
                department_name=row['department_name'],
                school_name=row['school_name'],
                institution_name=row['institution_name'],
                country=row['country'],
                institution_website=row['institution_website'],
                program_website=row['program_website'],
                priority_tier=row['priority_tier'],
                modalities=row['modalities'],
                schedules=row['schedules'],
                last_updated=row['last_updated'],
                avg_confidence=float(row['avg_confidence']),
                requirement_count=row['requirement_count']
            ))

        return programs, total_count['count']

    async def get_program_detail(self, program_id: UUID) -> Optional[ProgramDetailResponse]:
        """Get detailed program information."""

        # Get basic program info
        program_query = """
            SELECT
                psv.program_id::uuid,
                psv.program_name,
                psv.degree,
                psv.department_name,
                psv.school_name,
                psv.institution_name,
                psv.country,
                psv.institution_website,
                psv.program_website,
                psv.priority_tier,
                psv.modalities,
                psv.schedules,
                psv.last_updated,
                psv.avg_confidence,
                p.cip_code
            FROM program_search_view psv
            LEFT JOIN program p ON p.id::text = psv.program_id
            WHERE psv.program_id = $1::text
        """

        program_row = await db.execute_one(program_query, str(program_id))
        if not program_row:
            return None

        # Get requirement set for this program
        req_query = """
            SELECT rs.id, rs.source_url, rs.last_verified_at, rs.confidence, rs.status
            FROM current_requirements_view rs
            JOIN track t ON rs.track_id = t.id
            JOIN program p ON t.program_id = p.id
            WHERE p.id = $1
            LIMIT 1
        """

        req_row = await db.execute_one(req_query, program_id)
        if not req_row:
            # Return basic info without requirements
            return ProgramDetailResponse(
                program_id=program_row['program_id'],
                program_name=program_row['program_name'],
                degree=program_row['degree'],
                department_name=program_row['department_name'],
                school_name=program_row['school_name'],
                institution_name=program_row['institution_name'],
                country=program_row['country'],
                institution_website=program_row['institution_website'],
                program_website=program_row['program_website'],
                priority_tier=program_row['priority_tier'],
                modalities=program_row['modalities'],
                schedules=program_row['schedules'],
                cip_code=program_row['cip_code'],
                test_requirements=[],
                deadlines=[],
                contacts=[],
                prerequisites=[],
                last_verified=program_row['last_updated'],
                confidence_score=float(program_row['avg_confidence']),
                source_url="",
                status="incomplete"
            )

        requirement_set_id = req_row['id']

        # Get test requirements
        test_requirements = await self._get_test_requirements(requirement_set_id)

        # Get deadlines
        deadlines = await self._get_deadlines(requirement_set_id)

        # Get contacts
        contacts = await self._get_contacts(requirement_set_id)

        # Get application components
        components = await self._get_components(requirement_set_id)

        # Get international requirements
        intl_reqs = await self._get_intl_requirements(requirement_set_id)

        return ProgramDetailResponse(
            program_id=program_row['program_id'],
            program_name=program_row['program_name'],
            degree=program_row['degree'],
            department_name=program_row['department_name'],
            school_name=program_row['school_name'],
            institution_name=program_row['institution_name'],
            country=program_row['country'],
            institution_website=program_row['institution_website'],
            program_website=program_row['program_website'],
            priority_tier=program_row['priority_tier'],
            modalities=program_row['modalities'],
            schedules=program_row['schedules'],
            cip_code=program_row['cip_code'],
            test_requirements=test_requirements,
            deadlines=deadlines,
            contacts=contacts,

            # Components
            sop_required=components.get('sop_required'),
            recommendation_letters_min=components.get('rec_min'),
            recommendation_letters_max=components.get('rec_max'),
            resume_required=components.get('resume_required'),
            portfolio_required=components.get('portfolio_required'),
            writing_sample_required=components.get('writing_sample_required'),
            prerequisites=components.get('prereq_list', []),
            min_gpa=float(components['gpa_min']) if components.get('gpa_min') else None,
            min_experience_years=components.get('experience_years_min'),
            application_fee=float(components['fee_amount']) if components.get('fee_amount') else None,

            # International
            transcript_evaluation_required=bool(intl_reqs.get('wes_required') or intl_reqs.get('ece_required')),
            funding_documentation_required=bool(intl_reqs.get('funding_docs_required', True)),
            english_exemptions=intl_reqs.get('english_exemptions'),

            # Metadata
            last_verified=req_row['last_verified_at'],
            confidence_score=float(req_row['confidence']),
            source_url=req_row['source_url'],
            status=req_row['status']
        )

    async def _get_test_requirements(self, requirement_set_id: UUID) -> List[TestRequirementDetail]:
        """Get test requirements for a requirement set."""
        query = """
            SELECT
                gre_status, gmat_status, lsat_status, mcat_status,
                toefl_min, toefl_section_min, ielts_min, det_min,
                code_toefl, code_gre, code_gmat, score_validity_months
            FROM tests
            WHERE requirement_set_id = $1
        """

        row = await db.execute_one(query, requirement_set_id)
        if not row:
            return []

        requirements = []

        # Add each test if it has a status
        test_configs = [
            ('GRE', row['gre_status'], None, None, row['code_gre']),
            ('GMAT', row['gmat_status'], None, None, row['code_gmat']),
            ('LSAT', row['lsat_status'], None, None, None),
            ('MCAT', row['mcat_status'], None, None, None),
            ('TOEFL', 'required' if row['toefl_min'] else 'unknown',
             row['toefl_min'], row['toefl_section_min'], row['code_toefl']),
            ('IELTS', 'required' if row['ielts_min'] else 'unknown',
             int(row['ielts_min']) if row['ielts_min'] else None, None, None),
            ('DET', 'required' if row['det_min'] else 'unknown',
             row['det_min'], None, None),
        ]

        for test_name, status, min_score, section_min, code in test_configs:
            if status and status != 'unknown':
                requirements.append(TestRequirementDetail(
                    test_name=test_name,
                    status=status,
                    min_score=min_score,
                    section_minima=section_min if isinstance(section_min, dict) else None,
                    institution_code=code,
                    validity_months=row['score_validity_months']
                ))

        return requirements

    async def _get_deadlines(self, requirement_set_id: UUID) -> List[DeadlineDetail]:
        """Get deadlines for a requirement set."""
        query = """
            SELECT deadline_type, deadline_ts, rolling_flag, audience
            FROM deadlines
            WHERE requirement_set_id = $1
            ORDER BY deadline_ts ASC
        """

        rows = await db.execute_query(query, requirement_set_id)
        return [
            DeadlineDetail(
                deadline_type=row['deadline_type'],
                deadline_date=row['deadline_ts'],
                is_rolling=row['rolling_flag'],
                audience=row['audience']
            )
            for row in rows
        ]

    async def _get_contacts(self, requirement_set_id: UUID) -> List[ContactDetail]:
        """Get contacts for a requirement set."""
        query = """
            SELECT contact_type, email, phone, address
            FROM contacts
            WHERE requirement_set_id = $1
        """

        rows = await db.execute_query(query, requirement_set_id)
        return [
            ContactDetail(
                contact_type=row['contact_type'],
                email=row['email'],
                phone=row['phone'],
                address=row['address']
            )
            for row in rows
        ]

    async def _get_components(self, requirement_set_id: UUID) -> Dict[str, Any]:
        """Get application components for a requirement set."""
        query = """
            SELECT
                sop_required, rec_min, rec_max, resume_required,
                portfolio_required, writing_sample_required, prereq_list,
                gpa_min, experience_years_min, fee_amount
            FROM components
            WHERE requirement_set_id = $1
        """

        row = await db.execute_one(query, requirement_set_id)
        return dict(row) if row else {}

    async def _get_intl_requirements(self, requirement_set_id: UUID) -> Dict[str, Any]:
        """Get international requirements for a requirement set."""
        query = """
            SELECT
                wes_required, ece_required, transcript_policy,
                english_exemptions, funding_docs_required
            FROM intl
            WHERE requirement_set_id = $1
        """

        row = await db.execute_one(query, requirement_set_id)
        return dict(row) if row else {}

    async def calculate_fit(
        self,
        request: FitCheckRequest,
        programs: List[ProgramSearchResult]
    ) -> List[FitCheckResponse]:
        """Calculate fit scores for programs based on student profile."""
        fit_results = []

        for program in programs:
            # Get detailed requirements for fit calculation
            detail = await self.get_program_detail(program.program_id)
            if not detail:
                continue

            fit_score = self._calculate_program_fit(request, detail)
            admission_prob = self._estimate_admission_probability(fit_score.overall_score)

            fit_results.append(FitCheckResponse(
                program_id=program.program_id,
                program_name=program.program_name,
                institution_name=program.institution_name,
                degree=program.degree,
                fit_score=fit_score,
                estimated_admission_probability=admission_prob
            ))

        return sorted(fit_results, key=lambda x: x.fit_score.overall_score, reverse=True)

    def _calculate_program_fit(self, request: FitCheckRequest, program: ProgramDetailResponse) -> FitScore:
        """Calculate detailed fit score for a program."""
        scores = []
        missing_requirements = []
        strengths = []
        recommendations = []

        # Test score matching
        test_score = self._calculate_test_score_match(request, program)
        scores.append(test_score)

        # GPA matching
        gpa_score = self._calculate_gpa_match(request, program)
        scores.append(gpa_score)

        # Experience matching
        exp_score = self._calculate_experience_match(request, program)
        scores.append(exp_score)

        # Preference matching
        pref_score = self._calculate_preference_match(request, program)
        scores.append(pref_score)

        # Check missing requirements
        if program.min_gpa and (not request.gpa or request.gpa < program.min_gpa):
            missing_requirements.append(f"Minimum GPA: {program.min_gpa}")

        if program.min_experience_years and (not request.work_experience_years or
                                           request.work_experience_years < program.min_experience_years):
            missing_requirements.append(f"Minimum experience: {program.min_experience_years} years")

        # Identify strengths
        if request.gpa and program.min_gpa and request.gpa > program.min_gpa + 0.3:
            strengths.append("Strong academic record")

        if request.work_experience_years and request.work_experience_years > 3:
            strengths.append("Significant work experience")

        if request.publications > 0:
            strengths.append("Research publications")

        # Generate recommendations
        if test_score < 60:
            recommendations.append("Consider retaking standardized tests")

        if pref_score < 50:
            recommendations.append("Review program location and format preferences")

        overall_score = sum(scores) / len(scores) if scores else 0

        return FitScore(
            overall_score=overall_score,
            test_score_match=test_score,
            gpa_match=gpa_score,
            experience_match=exp_score,
            preference_match=pref_score,
            missing_requirements=missing_requirements,
            strengths=strengths,
            recommendations=recommendations
        )

    def _calculate_test_score_match(self, request: FitCheckRequest, program: ProgramDetailResponse) -> float:
        """Calculate test score matching percentage."""
        scores = []

        for test_req in program.test_requirements:
            if test_req.status not in ['required', 'recommended']:
                continue

            if test_req.test_name == 'GRE' and request.gre_total:
                # Approximate GRE score matching (assuming competitive score ~320)
                target_score = 320
                actual_score = request.gre_total
                score_match = min(100, (actual_score / target_score) * 100)
                scores.append(score_match)

            elif test_req.test_name == 'TOEFL' and request.toefl_total and test_req.min_score:
                score_match = min(100, (request.toefl_total / test_req.min_score) * 100)
                scores.append(score_match)

            elif test_req.test_name == 'IELTS' and request.ielts_total and test_req.min_score:
                score_match = min(100, (request.ielts_total / test_req.min_score) * 100)
                scores.append(score_match)

            elif test_req.test_name == 'GMAT' and request.gmat_total:
                target_score = 650
                score_match = min(100, (request.gmat_total / target_score) * 100)
                scores.append(score_match)

        return sum(scores) / len(scores) if scores else 85  # Default if no tests required

    def _calculate_gpa_match(self, request: FitCheckRequest, program: ProgramDetailResponse) -> float:
        """Calculate GPA matching percentage."""
        if not program.min_gpa:
            return 90  # No GPA requirement

        if not request.gpa:
            return 50  # Unknown GPA is risky

        if request.gpa >= program.min_gpa:
            excess = request.gpa - program.min_gpa
            return min(100, 80 + (excess * 50))  # 80% for meeting + bonus
        else:
            shortfall = program.min_gpa - request.gpa
            return max(0, 80 - (shortfall * 100))  # Penalty for not meeting

    def _calculate_experience_match(self, request: FitCheckRequest, program: ProgramDetailResponse) -> float:
        """Calculate experience matching percentage."""
        if not program.min_experience_years:
            return 80  # No specific requirement

        if not request.work_experience_years:
            return 30  # No experience when required

        if request.work_experience_years >= program.min_experience_years:
            return 100
        else:
            shortfall = program.min_experience_years - request.work_experience_years
            return max(0, 70 - (shortfall * 20))

    def _calculate_preference_match(self, request: FitCheckRequest, program: ProgramDetailResponse) -> float:
        """Calculate preference matching percentage."""
        score = 70  # Base score

        # Country preference
        if request.preferred_countries and program.country in request.preferred_countries:
            score += 20
        elif request.preferred_countries and program.country not in request.preferred_countries:
            score -= 10

        # Modality preference
        if request.preferred_modalities:
            if any(mod in program.modalities for mod in request.preferred_modalities):
                score += 10
            else:
                score -= 10

        # Application fee
        if request.max_application_fee and program.application_fee:
            if program.application_fee <= request.max_application_fee:
                score += 5
            else:
                score -= 5

        return min(100, max(0, score))

    def _estimate_admission_probability(self, fit_score: float) -> float:
        """Estimate admission probability based on fit score."""
        if fit_score >= 90:
            return 0.8
        elif fit_score >= 80:
            return 0.65
        elif fit_score >= 70:
            return 0.45
        elif fit_score >= 60:
            return 0.25
        else:
            return 0.1