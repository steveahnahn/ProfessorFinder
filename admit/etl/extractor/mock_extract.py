"""
Mock Extractor for Testing
Generates realistic requirement data for testing the pipeline without LLM APIs
"""

from typing import List
import random
from datetime import datetime
from schemas.requirements import (
    ExtractedRequirements, TestRequirements, ApplicationComponents,
    InternationalRequirements, Provenance, Audit, Citation, TestStatus,
    ProgramInfo, ExtractionResult, Deadline, DeadlineType, Audience
)
from etl.parser.html_segmenter import ParsedSegment
import logging

logger = logging.getLogger(__name__)


class MockRequirementsExtractor:
    """Mock extractor that generates realistic requirements for testing"""

    def __init__(self):
        self.confidence_scores = [0.85, 0.90, 0.92, 0.88, 0.95, 0.78, 0.83]

    async def extract_requirements(self, segments: List[ParsedSegment], program_info: ProgramInfo) -> ExtractionResult:
        """Generate mock requirements based on program info"""

        try:
            # Generate realistic test requirements
            tests = self._generate_test_requirements(program_info)

            # Generate application components
            components = self._generate_application_components()

            # Generate international requirements
            intl_reqs = self._generate_international_requirements()

            # Generate deadlines from real content
            deadlines = self._generate_deadlines(segments)

            # Generate provenance
            provenance = self._generate_provenance(segments, program_info)

            # Generate audit trail
            confidence = random.choice(self.confidence_scores)
            audit = Audit(
                last_verified_at=datetime.now(),
                confidence=confidence,
                extraction_method="llm"
            )

            # Combine into ExtractedRequirements
            requirements = ExtractedRequirements(
                program=program_info,
                term_year=2025,
                tests=tests,
                components=components,
                intl=intl_reqs,
                deadlines=deadlines,
                provenance=provenance,
                audit=audit
            )

            logger.info(f"Generated mock requirements with {confidence:.2f} confidence")

            return ExtractionResult(
                extracted_requirements=requirements,
                raw_response=f"Mock generated requirements for {program_info.program_name}",
                model_used="mock-extractor-v1.0",
                extraction_confidence=confidence,
                processing_time_seconds=0.5,
                token_usage={"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
            )

        except Exception as e:
            logger.error(f"Mock extraction failed: {str(e)}")
            # Create fallback requirements
            fallback_requirements = ExtractedRequirements(
                program=program_info,
                term_year=2025,
                provenance=Provenance(
                    source_url=program_info.website,
                    citations=[]
                ),
                audit=Audit(
                    last_verified_at=datetime.now(),
                    confidence=0.1,
                    extraction_method="heuristic"
                )
            )

            return ExtractionResult(
                extracted_requirements=fallback_requirements,
                raw_response=f"Error occurred: {str(e)}",
                model_used="mock-extractor-v1.0",
                extraction_confidence=0.1,
                processing_time_seconds=0.1,
                token_usage={}
            )

    def _generate_test_requirements(self, program_info: ProgramInfo) -> TestRequirements:
        """Generate realistic test requirements based on program type"""

        # Different requirements based on degree type
        if program_info.degree.value == "MBA":
            return TestRequirements(
                gre_status=TestStatus.OPTIONAL,
                gmat_status=TestStatus.REQUIRED,
                toefl_min=100,
                ielts_min=7.0,
                det_min=120,
                code_toefl="1234",
                code_gre="1234",
                code_gmat="1234"
            )
        else:
            # Graduate programs (MS, PhD)
            return TestRequirements(
                gre_status=TestStatus.REQUIRED,
                gmat_status=TestStatus.NOT_ACCEPTED,
                toefl_min=90,
                ielts_min=6.5,
                det_min=105,
                code_toefl="1234",
                code_gre="1234"
            )

    def _generate_application_components(self) -> ApplicationComponents:
        """Generate typical application components"""
        return ApplicationComponents(
            sop_required=True,
            resume_required=True,
            portfolio_required=random.choice([True, False]),
            writing_sample_required=random.choice([True, False]),
            prereq_list=["Bachelor's degree in relevant field", "Mathematics coursework"],
            gpa_min=3.0,
            experience_years_min=0,
            rec_min=2,
            rec_max=3,
            fee_amount=75.0
        )

    def _generate_international_requirements(self) -> InternationalRequirements:
        """Generate international student requirements"""
        return InternationalRequirements(
            wes_required=random.choice([True, False]),
            ece_required=random.choice([True, False]),
            transcript_policy="Official transcripts required with degree posted",
            english_exemptions="Students from English-speaking countries may be exempt",
            funding_docs_required=True
        )

    def _generate_deadlines(self, segments: List[ParsedSegment]) -> List[Deadline]:
        """Extract REAL deadlines from content - NO FAKE DATA"""
        deadlines = []

        import re
        from datetime import datetime

        # Common deadline patterns
        deadline_patterns = [
            # "December 1, 2025" format
            r'(?:deadline|due|apply by|application due)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            # "December 1st, 2025" format
            r'(?:deadline|due|apply by|application due)[:\s]*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th),?\s+\d{4})',
            # "Dec 1, 2025" format
            r'(?:deadline|due|apply by|application due)[:\s]*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})',
            # "1 December 2025" format
            r'(?:deadline|due|apply by|application due)[:\s]*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        ]

        # Priority deadline patterns
        priority_patterns = [
            r'(?:priority|early|preferred)\s+(?:deadline|due)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?:priority|early|preferred)\s+(?:deadline|due)[:\s]*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})',
        ]

        for segment in segments:
            text = segment.text
            text_lower = text.lower()

            # Skip if no deadline-related keywords
            if not any(keyword in text_lower for keyword in ['deadline', 'due', 'apply by', 'application']):
                continue

            # Look for priority deadlines first
            for pattern in priority_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Try to parse the date
                        parsed_date = self._parse_date_string(match)
                        if parsed_date:
                            deadlines.append(Deadline(
                                date=parsed_date,
                                type=DeadlineType.PRIORITY,
                                audience=Audience.ALL,
                                description=f"Priority application deadline"
                            ))
                    except:
                        continue

            # Look for regular deadlines
            for pattern in deadline_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Try to parse the date
                        parsed_date = self._parse_date_string(match)
                        if parsed_date:
                            # Determine deadline type from context
                            deadline_type = DeadlineType.APPLICATION
                            if any(word in text_lower for word in ['priority', 'early']):
                                deadline_type = DeadlineType.PRIORITY
                            elif any(word in text_lower for word in ['final', 'last', 'regular']):
                                deadline_type = DeadlineType.FINAL

                            # Determine audience from context
                            audience = Audience.ALL
                            if 'international' in text_lower:
                                audience = Audience.INTERNATIONAL
                            elif 'domestic' in text_lower:
                                audience = Audience.DOMESTIC

                            deadlines.append(Deadline(
                                date=parsed_date,
                                type=deadline_type,
                                audience=audience,
                                description=f"Application deadline extracted from: {text[:100]}..."
                            ))
                    except:
                        continue

        # Remove duplicates based on date and type
        unique_deadlines = []
        seen = set()
        for deadline in deadlines:
            key = (deadline.date, deadline.type, deadline.audience)
            if key not in seen:
                seen.add(key)
                unique_deadlines.append(deadline)

        return unique_deadlines

    def _parse_date_string(self, date_str: str):
        """Parse various date string formats"""
        from dateutil.parser import parse

        try:
            # Clean up the date string
            cleaned = date_str.strip().replace(',', '').replace('.', '')

            # Try to parse with dateutil
            parsed = parse(cleaned, fuzzy=True)

            # Only return dates that seem reasonable (not too far in past/future)
            current_year = datetime.now().year
            if current_year <= parsed.year <= current_year + 2:
                return parsed.date()

        except:
            pass

        return None

    def _generate_provenance(self, segments: List[ParsedSegment], program_info: ProgramInfo) -> Provenance:
        """Generate REAL citations only where we can identify relevant content - NO FAKE DATA"""
        citations = []

        # Only create citations for content we can actually identify in segments
        for segment in segments:
            text_lower = segment.text.lower()

            # Look for TOEFL mentions
            if 'toefl' in text_lower and any(word in text_lower for word in ['score', 'minimum', 'required']):
                citations.append(Citation(
                    field_name="toefl_min",
                    kind="html",
                    snippet=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                    selector=segment.selector,
                    page_num=None,
                    line_start=None,
                    line_end=None
                ))

            # Look for GRE mentions
            if 'gre' in text_lower and any(word in text_lower for word in ['required', 'optional', 'recommended']):
                citations.append(Citation(
                    field_name="gre_status",
                    kind="html",
                    snippet=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                    selector=segment.selector,
                    page_num=None,
                    line_start=None,
                    line_end=None
                ))

            # Look for recommendation letters
            if any(word in text_lower for word in ['recommendation', 'letter', 'referee']):
                citations.append(Citation(
                    field_name="rec_min",
                    kind="html",
                    snippet=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                    selector=segment.selector,
                    page_num=None,
                    line_start=None,
                    line_end=None
                ))

        return Provenance(
            source_url=program_info.website,
            citations=citations
        )


# Create global instance
mock_extractor = MockRequirementsExtractor()