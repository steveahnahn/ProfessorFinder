"""
Requirements Validation System
Validates extracted requirements using business rules and cross-checks
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from pathlib import Path
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import (
    ExtractedRequirements, ValidationIssue, ValidationReport, ValidationSeverity,
    TestStatus, Degree
)

import structlog
logger = structlog.get_logger()


@dataclass
class ValidationConfig:
    """Configuration for validation rules"""
    strict_mode: bool = False  # Strict validation fails on warnings
    check_peer_consistency: bool = True
    require_citations: bool = True
    validate_date_logic: bool = True
    current_year: int = datetime.now().year


class RequirementsValidator:
    """Validates extracted requirements using comprehensive rule set"""

    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()

        # Known valid TOEFL institution codes (partial list for validation)
        self.known_toefl_codes = {
            '0010', '0017', '0027', '0034', '0058', '0065', '0090', '0103',
            '1234', '1262', '1324', '1335', '1343', '1395', '1426', '1461',
            '1506', '1533', '1592', '1652', '1759', '1839', '1852',
            '2028', '2098', '2161', '2206', '2298', '2358', '2439', '2496',
            '2533', '2590', '2671', '2723', '2785', '2823', '2859', '2883',
            '3005', '3026', '3058', '3087', '3151', '3225', '3294', '3336',
            '3425', '3434', '3444', '3469', '3514', '3542', '3592', '3654',
            '3711', '3766', '3795', '3837', '3873', '3892', '3912', '3965',
            '4004', '4026', '4058', '4087', '4123', '4186', '4256', '4313',
            '4362', '4419', '4463', '4512', '4565', '4633', '4677', '4704',
            '4756', '4833', '4876', '4912', '4965', '5002', '5045', '5098',
            '5126', '5185', '5256', '5323', '5372', '5435', '5489', '5534',
            '5567', '5623', '5675', '5712', '5786', '5823', '5865', '5912'
        }

        # Reasonable ranges for test scores
        self.score_ranges = {
            'toefl_total': (0, 120),
            'toefl_section': (0, 30),
            'ielts': (0.0, 9.0),
            'duolingo': (0, 160),
            'gre_section': (130, 170),
            'gre_writing': (0.0, 6.0),
            'gmat_total': (200, 800),
            'gpa': (0.0, 4.0)
        }

        # Typical test requirements by degree type
        self.typical_requirements = {
            Degree.MBA: {
                'typical_tests': ['gmat', 'gre'],
                'typical_gmat': TestStatus.REQUIRED,
                'typical_gre': TestStatus.OPTIONAL
            },
            Degree.MS: {
                'typical_tests': ['gre'],
                'typical_gre': TestStatus.OPTIONAL
            },
            Degree.PHD: {
                'typical_tests': ['gre'],
                'typical_gre': TestStatus.REQUIRED
            },
            Degree.JD: {
                'typical_tests': ['lsat'],
                'typical_lsat': TestStatus.REQUIRED
            },
            Degree.MD: {
                'typical_tests': ['mcat'],
                'typical_mcat': TestStatus.REQUIRED
            }
        }

    def validate_requirements(self, requirements: ExtractedRequirements) -> ValidationReport:
        """
        Main validation method

        Args:
            requirements: Extracted requirements to validate

        Returns:
            ValidationReport with all issues found
        """
        logger.info("Starting requirements validation",
                   program=requirements.program.program_name)

        issues = []

        # Run all validation rules
        issues.extend(self._validate_format_rules(requirements))
        issues.extend(self._validate_logical_consistency(requirements))
        issues.extend(self._validate_business_rules(requirements))
        issues.extend(self._validate_temporal_logic(requirements))

        if self.config.require_citations:
            issues.extend(self._validate_citation_completeness(requirements))

        if self.config.check_peer_consistency:
            issues.extend(self._validate_peer_consistency(requirements))

        # Calculate overall confidence
        confidence = self._calculate_validation_confidence(requirements, issues)

        # Determine status recommendation
        status = self._determine_status_recommendation(issues, confidence)

        report = ValidationReport(
            requirement_set_id="temp_id",  # Would be filled by calling code
            issues=issues,
            overall_confidence=confidence,
            status_recommendation=status,
            timestamp=datetime.now()
        )

        logger.info("Validation completed",
                   total_issues=len(issues),
                   errors=report.error_count,
                   warnings=report.warning_count,
                   confidence=confidence)

        return report

    def _validate_format_rules(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate field formats and ranges"""
        issues = []

        # Test score ranges
        if req.tests.toefl_min:
            min_score, max_score = self.score_ranges['toefl_total']
            if not (min_score <= req.tests.toefl_min <= max_score):
                issues.append(ValidationIssue(
                    field_name='toefl_min',
                    severity=ValidationSeverity.ERROR,
                    message=f'TOEFL score out of valid range ({min_score}-{max_score})',
                    current_value=str(req.tests.toefl_min),
                    expected_value=f'{min_score}-{max_score}'
                ))

        # TOEFL section scores
        if req.tests.toefl_section_min:
            for section, score in req.tests.toefl_section_min.model_dump().items():
                if score is not None:
                    min_score, max_score = self.score_ranges['toefl_section']
                    if not (min_score <= score <= max_score):
                        issues.append(ValidationIssue(
                            field_name=f'toefl_section_min.{section}',
                            severity=ValidationSeverity.ERROR,
                            message=f'TOEFL {section} score out of range ({min_score}-{max_score})',
                            current_value=str(score),
                            expected_value=f'{min_score}-{max_score}'
                        ))

        # IELTS score
        if req.tests.ielts_min:
            min_score, max_score = self.score_ranges['ielts']
            if not (min_score <= req.tests.ielts_min <= max_score):
                issues.append(ValidationIssue(
                    field_name='ielts_min',
                    severity=ValidationSeverity.ERROR,
                    message=f'IELTS score out of valid range ({min_score}-{max_score})',
                    current_value=str(req.tests.ielts_min),
                    expected_value=f'{min_score}-{max_score}'
                ))

        # Institution codes format
        if req.tests.code_toefl:
            if not re.match(r'^\d{4}$', req.tests.code_toefl):
                issues.append(ValidationIssue(
                    field_name='code_toefl',
                    severity=ValidationSeverity.ERROR,
                    message='TOEFL code must be exactly 4 digits',
                    current_value=req.tests.code_toefl,
                    expected_value='4-digit number (e.g., "1234")'
                ))
            elif req.tests.code_toefl not in self.known_toefl_codes:
                issues.append(ValidationIssue(
                    field_name='code_toefl',
                    severity=ValidationSeverity.WARNING,
                    message='TOEFL code not in known valid codes list',
                    current_value=req.tests.code_toefl,
                    expected_value='Known ETS institution code'
                ))

        # GPA range
        if req.components.gpa_min:
            min_gpa, max_gpa = self.score_ranges['gpa']
            if not (min_gpa <= req.components.gpa_min <= max_gpa):
                issues.append(ValidationIssue(
                    field_name='gpa_min',
                    severity=ValidationSeverity.WARNING,
                    message=f'GPA out of typical range ({min_gpa}-{max_gpa})',
                    current_value=str(req.components.gpa_min),
                    expected_value=f'{min_gpa}-{max_gpa}'
                ))

        # Application fee reasonableness
        if req.components.fee_amount:
            if req.components.fee_amount < 0:
                issues.append(ValidationIssue(
                    field_name='fee_amount',
                    severity=ValidationSeverity.ERROR,
                    message='Application fee cannot be negative',
                    current_value=str(req.components.fee_amount)
                ))
            elif req.components.fee_amount > 500:
                issues.append(ValidationIssue(
                    field_name='fee_amount',
                    severity=ValidationSeverity.WARNING,
                    message='Application fee unusually high (>$500)',
                    current_value=str(req.components.fee_amount),
                    expected_value='$50-$200 typical range'
                ))

        return issues

    def _validate_logical_consistency(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate logical consistency between fields"""
        issues = []

        # TOEFL requirements consistency
        if req.tests.toefl_min and not req.tests.code_toefl:
            if not req.intl.english_exemptions:
                issues.append(ValidationIssue(
                    field_name='code_toefl',
                    severity=ValidationSeverity.WARNING,
                    message='TOEFL minimum specified but no institution code provided',
                    current_value='null',
                    expected_value='4-digit TOEFL code'
                ))

        # Recommendation letter consistency
        if req.components.rec_min and req.components.rec_max:
            if req.components.rec_min > req.components.rec_max:
                issues.append(ValidationIssue(
                    field_name='rec_min',
                    severity=ValidationSeverity.ERROR,
                    message='Minimum recommendation count exceeds maximum',
                    current_value=f'min={req.components.rec_min}, max={req.components.rec_max}',
                    expected_value='min <= max'
                ))

        # TOEFL section scores vs total
        if req.tests.toefl_min and req.tests.toefl_section_min:
            sections = req.tests.toefl_section_min.model_dump()
            section_scores = [score for score in sections.values() if score is not None]

            if section_scores:
                theoretical_min_total = sum(section_scores)
                if theoretical_min_total > req.tests.toefl_min:
                    issues.append(ValidationIssue(
                        field_name='toefl_section_min',
                        severity=ValidationSeverity.WARNING,
                        message='Sum of section minima exceeds total TOEFL minimum',
                        current_value=f'sections sum to {theoretical_min_total}',
                        expected_value=f'should not exceed {req.tests.toefl_min}'
                    ))

        return issues

    def _validate_business_rules(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate against business logic and typical patterns"""
        issues = []

        degree = req.program.degree

        # Degree-specific test expectations
        if degree in self.typical_requirements:
            expectations = self.typical_requirements[degree]

            # MBA programs typically require GMAT
            if degree == Degree.MBA:
                if req.tests.gmat_status == TestStatus.NOT_ACCEPTED:
                    issues.append(ValidationIssue(
                        field_name='gmat_status',
                        severity=ValidationSeverity.WARNING,
                        message='MBA program not accepting GMAT is unusual',
                        current_value=req.tests.gmat_status.value
                    ))
                elif req.tests.gmat_status == TestStatus.UNKNOWN:
                    issues.append(ValidationIssue(
                        field_name='gmat_status',
                        severity=ValidationSeverity.INFO,
                        message='GMAT status not specified for MBA program',
                        current_value='unknown',
                        expected_value='typically required or optional'
                    ))

            # PhD programs typically require GRE
            elif degree == Degree.PHD:
                if req.tests.gre_status == TestStatus.NOT_ACCEPTED:
                    issues.append(ValidationIssue(
                        field_name='gre_status',
                        severity=ValidationSeverity.INFO,
                        message='PhD program not requiring GRE (increasingly common)',
                        current_value=req.tests.gre_status.value
                    ))

            # Professional programs
            elif degree == Degree.JD and req.tests.lsat_status != TestStatus.REQUIRED:
                issues.append(ValidationIssue(
                    field_name='lsat_status',
                    severity=ValidationSeverity.WARNING,
                    message='Law degree program not requiring LSAT is unusual',
                    current_value=req.tests.lsat_status.value,
                    expected_value='required'
                ))

        # International requirements logic
        if req.tests.toefl_min or req.tests.ielts_min:
            if not req.intl.english_exemptions:
                issues.append(ValidationIssue(
                    field_name='english_exemptions',
                    severity=ValidationSeverity.INFO,
                    message='English proficiency required but no exemption rules specified',
                    current_value='null',
                    expected_value='Exemption criteria for native speakers'
                ))

        return issues

    def _validate_temporal_logic(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate date and time-related logic"""
        issues = []

        if not self.config.validate_date_logic:
            return issues

        current_date = datetime.now()

        for deadline in req.deadlines:
            # Check if deadlines are in the reasonable future
            if deadline.deadline_ts < current_date:
                # Only warn if significantly in the past
                days_past = (current_date - deadline.deadline_ts).days
                if days_past > 30:  # More than 30 days ago
                    issues.append(ValidationIssue(
                        field_name='deadline_ts',
                        severity=ValidationSeverity.WARNING,
                        message=f'{deadline.deadline_type.value} deadline is {days_past} days in the past',
                        current_value=deadline.deadline_ts.strftime('%Y-%m-%d'),
                        expected_value='Future date for current application cycle'
                    ))

            # Check if deadline is too far in future (probably wrong year)
            elif deadline.deadline_ts > current_date + timedelta(days=730):  # 2 years
                issues.append(ValidationIssue(
                    field_name='deadline_ts',
                    severity=ValidationSeverity.WARNING,
                    message='Deadline more than 2 years in future - check year',
                    current_value=deadline.deadline_ts.strftime('%Y-%m-%d'),
                    expected_value='Deadline within next academic year'
                ))

        # Check term year consistency
        if req.term_year < self.config.current_year:
            issues.append(ValidationIssue(
                field_name='term_year',
                severity=ValidationSeverity.INFO,
                message='Term year is in the past',
                current_value=str(req.term_year),
                expected_value=f'{self.config.current_year} or later'
            ))

        return issues

    def _validate_citation_completeness(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate citation completeness for important fields"""
        issues = []

        # Fields that should have citations
        important_fields = {
            'toefl_min': req.tests.toefl_min,
            'ielts_min': req.tests.ielts_min,
            'code_toefl': req.tests.code_toefl,
            'gre_status': req.tests.gre_status.value if req.tests.gre_status != TestStatus.UNKNOWN else None,
            'fee_amount': req.components.fee_amount,
            'rec_min': req.components.rec_min,
            'gpa_min': req.components.gpa_min
        }

        cited_fields = {citation.field_name for citation in req.provenance.citations}

        for field_name, field_value in important_fields.items():
            if field_value is not None and field_name not in cited_fields:
                issues.append(ValidationIssue(
                    field_name=field_name,
                    severity=ValidationSeverity.WARNING,
                    message='Important field missing citation to source text',
                    current_value=str(field_value),
                    expected_value='Citation with source text reference'
                ))

        return issues

    def _validate_peer_consistency(self, req: ExtractedRequirements) -> List[ValidationIssue]:
        """Validate against peer institution patterns (placeholder)"""
        issues = []

        # This would typically query database for similar programs
        # For now, just basic sanity checks

        # Very high TOEFL requirements might be unusual
        if req.tests.toefl_min and req.tests.toefl_min > 110:
            issues.append(ValidationIssue(
                field_name='toefl_min',
                severity=ValidationSeverity.INFO,
                message='TOEFL requirement higher than typical (>110)',
                current_value=str(req.tests.toefl_min),
                expected_value='80-105 typical range for graduate programs'
            ))

        # Very low requirements might also be unusual
        if req.tests.toefl_min and req.tests.toefl_min < 70:
            issues.append(ValidationIssue(
                field_name='toefl_min',
                severity=ValidationSeverity.INFO,
                message='TOEFL requirement lower than typical (<70)',
                current_value=str(req.tests.toefl_min),
                expected_value='80-105 typical range for graduate programs'
            ))

        return issues

    def _calculate_validation_confidence(
        self,
        req: ExtractedRequirements,
        issues: List[ValidationIssue]
    ) -> float:
        """Calculate overall confidence based on validation results"""
        base_confidence = 0.7  # Start with moderate confidence

        # Penalize for errors
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)

        confidence = base_confidence - (error_count * 0.2) - (warning_count * 0.05)

        # Bonus for good citation coverage
        important_field_count = sum(1 for value in [
            req.tests.toefl_min, req.tests.code_toefl, req.components.fee_amount,
            req.components.rec_min, req.tests.gre_status != TestStatus.UNKNOWN
        ] if value)

        citation_coverage = len(req.provenance.citations) / max(important_field_count, 1)
        confidence += min(0.2, citation_coverage * 0.2)

        # Bonus for deadline information
        if req.deadlines:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _determine_status_recommendation(
        self,
        issues: List[ValidationIssue],
        confidence: float
    ) -> str:
        """Determine recommended status based on validation results"""
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)

        # Hard errors require review
        if error_count > 0:
            return 'needs_review'

        # High confidence can be auto-approved
        if confidence >= 0.9:
            return 'approved'

        # Medium confidence needs review
        elif confidence >= 0.7:
            return 'needs_review'

        # Low confidence is draft
        else:
            return 'draft'


async def main():
    """Test the validation system"""
    from schemas.requirements import create_example_requirements

    validator = RequirementsValidator(ValidationConfig(
        strict_mode=False,
        check_peer_consistency=True,
        require_citations=True
    ))

    # Test with example requirements
    example_req = create_example_requirements()

    # Introduce some validation issues for testing
    example_req.tests.toefl_min = 150  # Invalid score
    example_req.components.rec_min = 5  # Too many recommendations
    example_req.components.rec_max = 3  # Inconsistent with min

    report = validator.validate_requirements(example_req)

    print(f"\n=== Validation Report ===")
    print(f"Overall Confidence: {report.overall_confidence:.2f}")
    print(f"Status Recommendation: {report.status_recommendation}")
    print(f"Issues Found: {len(report.issues)} ({report.error_count} errors, {report.warning_count} warnings)")

    print(f"\n=== Issues Details ===")
    for issue in report.issues:
        print(f"[{issue.severity.value.upper()}] {issue.field_name}: {issue.message}")
        if issue.current_value:
            print(f"  Current: {issue.current_value}")
        if issue.expected_value:
            print(f"  Expected: {issue.expected_value}")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())