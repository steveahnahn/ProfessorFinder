"""
LLM-based Requirements Extraction
Uses OpenAI/Anthropic to extract structured requirements from parsed content
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import openai
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import (
    ExtractedRequirements, ParsedSegment, ExtractionResult,
    ProgramInfo, Audit, Provenance, Citation, CitationKind
)

logger = structlog.get_logger()


class LLMExtractor:
    """Extracts structured requirements using LLM with strict JSON schema validation"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # API clients
        self.openai_client = None
        self.anthropic_client = None

        # Model settings
        self.openai_model = self.config.get('openai_model', 'gpt-4-turbo-preview')
        self.anthropic_model = self.config.get('anthropic_model', 'claude-3-sonnet-20240229')
        self.temperature = self.config.get('temperature', 0.1)
        self.max_tokens = self.config.get('max_tokens', 4000)

        # Load JSON schema
        self.json_schema = self._load_json_schema()

        # Load prompt templates
        self.system_prompt = self._load_system_prompt()
        self.few_shot_examples = self._load_few_shot_examples()

    def _load_json_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for validation"""
        try:
            schema_path = Path(__file__).parent.parent.parent / 'schemas' / 'requirements.schema.json'
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load JSON schema", error=str(e))
            # Fallback to generating schema
            from schemas.requirements import generate_json_schema
            return generate_json_schema()

    def _load_system_prompt(self) -> str:
        """Load the system prompt for LLM extraction"""
        return """You are a precise information extraction engine for graduate admissions requirements.

Your task:
1. Extract structured admissions requirements from the provided content
2. Return ONLY valid JSON matching the provided schema
3. Include citations mapping each extracted field to the source text
4. Use null for missing/unclear information - never guess

Key guidelines:
- Focus ONLY on GRADUATE programs (MS, MA, PhD, MBA, etc.)
- Extract exact numbers, codes, and requirements as stated
- For test requirements, distinguish: required/optional/recommended/not_accepted/waived
- TOEFL/GRE/GMAT codes are always 4-digit numbers (e.g., "4704")
- Include section minima for TOEFL when specified (reading, listening, speaking, writing)
- Pay attention to international vs domestic student differences
- Extract exact deadline dates and convert to ISO format with timezone
- Map each extracted field to specific source text in citations array

Common patterns to recognize:
- "TOEFL minimum 100" or "TOEFL: 100+" → toefl_min: 100
- "TOEFL sections: R:22, L:22, S:22, W:22" → toefl_section_min object
- "GRE required/optional/waived" → gre_status
- "Institution code: 1234" or "DI code: 1234" → code_toefl: "1234"
- "Application deadline: December 1, 2025" → deadline object
- "Two letters of recommendation required" → rec_min: 2, rec_max: 2
- "$125 application fee" → fee_amount: 125.0
- "International students must..." → specific intl requirements

Output ONLY valid JSON matching the ExtractedRequirements schema."""

    def _load_few_shot_examples(self) -> List[Dict[str, str]]:
        """Load few-shot examples for better extraction accuracy"""
        return [
            {
                "input": """
GRADUATE ADMISSIONS REQUIREMENTS

English Proficiency:
• TOEFL minimum score of 100 with section scores of at least 22 in each area
• IELTS minimum overall score of 7.0
• Institution code for TOEFL: 4704

Test Requirements:
• GRE General Test recommended but not required
• GMAT not accepted for this program

Application Components:
• Statement of Purpose (required)
• Three letters of recommendation
• Official transcripts
• Resume or CV

Application Deadlines:
• Priority deadline: December 1, 2025
• Final deadline: January 15, 2026
• Application fee: $125

Contact: gradschool@university.edu
                """,
                "output": """
{
  "program": {
    "institution": "Example University",
    "school": "Graduate School",
    "department": "Computer Science",
    "program_name": "Master of Science in Computer Science",
    "degree": "MS",
    "track": "Full-Time",
    "website": "https://example.edu/cs/ms"
  },
  "term_name": "Fall",
  "term_year": 2026,
  "tests": {
    "gre_status": "recommended",
    "gmat_status": "not_accepted",
    "toefl_min": 100,
    "toefl_section_min": {
      "reading": 22,
      "listening": 22,
      "speaking": 22,
      "writing": 22
    },
    "ielts_min": 7.0,
    "code_toefl": "4704"
  },
  "components": {
    "sop_required": true,
    "rec_min": 3,
    "rec_max": 3,
    "resume_required": true,
    "fee_amount": 125.0
  },
  "deadlines": [
    {
      "deadline_type": "priority",
      "deadline_ts": "2025-12-01T23:59:00-08:00",
      "audience": "both"
    },
    {
      "deadline_type": "final",
      "deadline_ts": "2026-01-15T23:59:00-08:00",
      "audience": "both"
    }
  ],
  "contacts": [
    {
      "email": "gradschool@university.edu"
    }
  ],
  "provenance": {
    "source_url": "https://example.edu/cs/ms/admissions",
    "citations": [
      {
        "field_name": "toefl_min",
        "kind": "html",
        "selector": "//div[@class='english-requirements']/ul/li[1]",
        "snippet": "TOEFL minimum score of 100 with section scores of at least 22 in each area"
      },
      {
        "field_name": "code_toefl",
        "kind": "html",
        "selector": "//div[@class='english-requirements']/p",
        "snippet": "Institution code for TOEFL: 4704"
      }
    ]
  }
}
                """
            }
        ]

    async def extract_requirements(
        self,
        segments: List[ParsedSegment],
        program_info: ProgramInfo,
        provider: str = "openai"
    ) -> ExtractionResult:
        """
        Main extraction method

        Args:
            segments: List of parsed content segments
            program_info: Basic program information
            provider: LLM provider ("openai" or "anthropic")

        Returns:
            ExtractionResult with extracted requirements
        """
        start_time = time.time()
        logger.info("Starting LLM extraction",
                   provider=provider,
                   program=program_info.program_name,
                   segments=len(segments))

        try:
            # Prepare context from segments
            context = self._prepare_context(segments)

            # Create user prompt
            user_prompt = self._create_user_prompt(context, program_info)

            # Extract using specified provider
            if provider == "openai":
                raw_response, token_usage = await self._extract_openai(user_prompt)
            elif provider == "anthropic":
                raw_response, token_usage = await self._extract_anthropic(user_prompt)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            # Parse and validate response
            extracted_requirements = self._parse_and_validate_response(
                raw_response, program_info, segments
            )

            # Calculate confidence based on citation completeness
            confidence = self._calculate_extraction_confidence(extracted_requirements, segments)

            processing_time = time.time() - start_time

            result = ExtractionResult(
                extracted_requirements=extracted_requirements,
                raw_response=raw_response,
                model_used=self.openai_model if provider == "openai" else self.anthropic_model,
                extraction_confidence=confidence,
                processing_time_seconds=processing_time,
                token_usage=token_usage
            )

            logger.info("LLM extraction completed",
                       provider=provider,
                       confidence=confidence,
                       processing_time=processing_time)

            return result

        except Exception as e:
            logger.error("LLM extraction failed", provider=provider, error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _extract_openai(self, user_prompt: str) -> tuple[str, Dict[str, int]]:
        """Extract using OpenAI GPT model"""
        if not self.openai_client:
            self.openai_client = openai.AsyncOpenAI()

        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"}  # Enforce JSON output
        )

        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return response.choices[0].message.content, token_usage

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _extract_anthropic(self, user_prompt: str) -> tuple[str, Dict[str, int]]:
        """Extract using Anthropic Claude model"""
        if not self.anthropic_client:
            self.anthropic_client = anthropic.AsyncAnthropic()

        # Anthropic doesn't have built-in JSON mode, so we need to be explicit
        json_instruction = "\n\nIMPORTANT: Respond ONLY with valid JSON. No explanatory text before or after."

        message = await self.anthropic_client.messages.create(
            model=self.anthropic_model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_prompt + json_instruction}
            ]
        )

        token_usage = {
            "prompt_tokens": message.usage.input_tokens,
            "completion_tokens": message.usage.output_tokens,
            "total_tokens": message.usage.input_tokens + message.usage.output_tokens
        }

        return message.content[0].text, token_usage

    def _prepare_context(self, segments: List[ParsedSegment]) -> str:
        """Prepare context string from parsed segments"""
        context_parts = []

        # Sort segments by relevance (those with more admissions keywords first)
        scored_segments = []
        for segment in segments:
            score = self._score_segment_relevance(segment.text)
            scored_segments.append((segment, score))

        scored_segments.sort(key=lambda x: x[1], reverse=True)

        # Limit context to fit in model context window
        total_chars = 0
        max_context_chars = 8000  # Leave room for prompt and response

        for segment, score in scored_segments:
            if total_chars + len(segment.text) > max_context_chars:
                break

            # Format segment with metadata
            if segment.kind == CitationKind.HTML:
                header = f"HTML SECTION (selector: {segment.selector}):"
            elif segment.kind == CitationKind.PDF:
                header = f"PDF SECTION (page {segment.page_num}, lines {segment.line_start}-{segment.line_end}):"
            else:
                header = "CONTENT SECTION:"

            context_parts.append(f"{header}\n{segment.text}\n")
            total_chars += len(segment.text) + len(header) + 2

        if not context_parts:
            context_parts.append("No relevant content found.")

        return "\n".join(context_parts)

    def _create_user_prompt(self, context: str, program_info: ProgramInfo) -> str:
        """Create the user prompt with context and program info"""
        program_context = f"""
PROGRAM INFORMATION:
Institution: {program_info.institution}
School: {program_info.school}
Department: {program_info.department}
Program: {program_info.program_name}
Degree: {program_info.degree}
Track: {program_info.track}
Website: {program_info.website}

CONTENT TO ANALYZE:
{context}

Extract graduate admissions requirements and output valid JSON matching the ExtractedRequirements schema.
Include citations mapping each field to the source text that supports it.
Use null for missing or unclear information.
"""
        return program_context

    def _parse_and_validate_response(
        self,
        raw_response: str,
        program_info: ProgramInfo,
        segments: List[ParsedSegment]
    ) -> ExtractedRequirements:
        """Parse LLM response and validate against schema"""
        try:
            # Parse JSON
            response_data = json.loads(raw_response)

            # Ensure required program info is present
            if "program" not in response_data:
                response_data["program"] = program_info.model_dump()

            # Ensure required metadata
            if "audit" not in response_data:
                response_data["audit"] = {
                    "last_verified_at": "2024-01-01T00:00:00Z",
                    "confidence": 0.5,
                    "extraction_method": "llm"
                }

            if "provenance" not in response_data:
                response_data["provenance"] = {
                    "source_url": program_info.website,
                    "citations": []
                }

            # Create and validate the model
            extracted_requirements = ExtractedRequirements.model_validate(response_data)

            return extracted_requirements

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response", error=str(e), response=raw_response[:200])
            # Create fallback minimal requirements
            return self._create_fallback_requirements(program_info, segments)

        except Exception as e:
            logger.error("Failed to validate extracted requirements", error=str(e))
            return self._create_fallback_requirements(program_info, segments)

    def _create_fallback_requirements(
        self,
        program_info: ProgramInfo,
        segments: List[ParsedSegment]
    ) -> ExtractedRequirements:
        """Create minimal fallback requirements when extraction fails"""
        from datetime import datetime

        return ExtractedRequirements(
            program=program_info,
            term_name="Fall",
            term_year=2026,
            provenance=Provenance(
                source_url=program_info.website,
                citations=[]
            ),
            audit=Audit(
                last_verified_at=datetime.now(),
                confidence=0.1,  # Low confidence for fallback
                extraction_method="fallback",
                notes="LLM extraction failed, using minimal fallback"
            )
        )

    def _score_segment_relevance(self, text: str) -> float:
        """Score segment relevance for prioritization"""
        text_lower = text.lower()
        score = 0.0

        # High-value keywords
        high_value_keywords = [
            'toefl', 'ielts', 'duolingo', 'english proficiency',
            'gre', 'gmat', 'lsat', 'mcat',
            'application deadline', 'deadline',
            'admission requirements', 'requirements',
            'application fee', 'fee'
        ]

        for keyword in high_value_keywords:
            if keyword in text_lower:
                score += 2.0

        # Medium-value keywords
        medium_value_keywords = [
            'graduate', 'masters', 'phd', 'doctoral',
            'recommendation', 'transcript', 'gpa',
            'international', 'visa'
        ]

        for keyword in medium_value_keywords:
            if keyword in text_lower:
                score += 1.0

        # Numeric patterns (often important for requirements)
        import re
        if re.search(r'\b\d{3,4}\b', text):  # Test scores, codes
            score += 1.0

        if re.search(r'\$\d+', text):  # Fees
            score += 1.0

        return score

    def _calculate_extraction_confidence(
        self,
        requirements: ExtractedRequirements,
        segments: List[ParsedSegment]
    ) -> float:
        """Calculate confidence score based on extraction completeness"""
        confidence = 0.5  # Base confidence

        # Check for key fields
        if requirements.tests.toefl_min:
            confidence += 0.1
        if requirements.tests.code_toefl:
            confidence += 0.1
        if requirements.components.fee_amount:
            confidence += 0.1
        if requirements.deadlines:
            confidence += 0.1
        if requirements.contacts:
            confidence += 0.1

        # Citation quality
        citation_count = len(requirements.provenance.citations)
        if citation_count > 0:
            confidence += min(0.2, citation_count * 0.05)

        # Ensure confidence stays within bounds
        return min(1.0, max(0.0, confidence))


async def main():
    """Test the LLM extractor"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Mock program info
    program_info = ProgramInfo(
        institution="Test University",
        school="School of Engineering",
        department="Computer Science",
        program_name="Master of Science in Computer Science",
        degree="MS",
        track="Full-Time",
        website="https://test.edu/cs/ms"
    )

    # Mock segments
    segments = [
        ParsedSegment(
            source_url="https://test.edu/cs/ms/admissions",
            kind=CitationKind.HTML,
            selector="//div[@class='requirements']",
            text="""Graduate Admission Requirements:
            - TOEFL minimum score of 100 (Reading: 22, Listening: 22, Speaking: 22, Writing: 22)
            - IELTS minimum score of 7.0
            - Institution code for TOEFL: 4704
            - GRE recommended but not required
            - Three letters of recommendation required
            - Statement of Purpose required
            - Application deadline: December 1, 2025
            - Application fee: $125""",
            context_tags=['requirements']
        )
    ]

    # Test extraction
    extractor = LLMExtractor()

    if os.getenv('OPENAI_API_KEY'):
        print("Testing OpenAI extraction...")
        result = await extractor.extract_requirements(segments, program_info, "openai")
        print(f"Extracted requirements with confidence: {result.extraction_confidence}")
        print(f"Test requirements: {result.extracted_requirements.tests}")


if __name__ == "__main__":
    asyncio.run(main())