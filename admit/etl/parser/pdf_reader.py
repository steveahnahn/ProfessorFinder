"""
PDF Content Reader
Extracts structured text from PDFs with coordinate tracking for citations
"""

import pdfplumber
import pymupdf  # fitz
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import re
import structlog
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import ParsedSegment, CitationKind

logger = structlog.get_logger()


@dataclass
class PDFExtractionConfig:
    """Configuration for PDF text extraction"""
    extract_tables: bool = True
    extract_images: bool = False  # For future OCR support
    min_text_length: int = 30
    max_segment_length: int = 2000
    preserve_layout: bool = True
    extract_coordinates: bool = True  # For precise citations


@dataclass
class TextBlock:
    """Represents a block of text with position information"""
    text: str
    page_num: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    line_start: int
    line_end: int
    font_size: float = 0.0
    font_name: str = ""
    is_heading: bool = False


class PDFReader:
    """Extracts and segments PDF content with coordinate tracking"""

    def __init__(self, config: PDFExtractionConfig = None):
        self.config = config or PDFExtractionConfig()

        # Keywords for identifying relevant content
        self.admissions_keywords = {
            'toefl', 'ielts', 'duolingo', 'english proficiency',
            'gre', 'gmat', 'lsat', 'mcat',
            'admission', 'application', 'requirements',
            'deadline', 'due date',
            'graduate', 'masters', 'phd', 'doctoral',
            'fee', 'cost', 'tuition',
            'recommendation', 'transcript', 'gpa'
        }

    def extract_segments(self, pdf_path: str, source_url: str) -> List[ParsedSegment]:
        """
        Main extraction method

        Args:
            pdf_path: Path to PDF file
            source_url: Source URL for reference

        Returns:
            List of ParsedSegment objects
        """
        logger.info("Starting PDF extraction", path=pdf_path)

        # Try both extraction methods and combine results
        pdfplumber_segments = self._extract_with_pdfplumber(pdf_path, source_url)
        pymupdf_segments = self._extract_with_pymupdf(pdf_path, source_url)

        # Combine and deduplicate
        all_segments = pdfplumber_segments + pymupdf_segments
        filtered_segments = self._filter_and_merge_segments(all_segments)

        logger.info("PDF extraction completed",
                   path=pdf_path,
                   total_segments=len(filtered_segments))

        return filtered_segments

    def _extract_with_pdfplumber(self, pdf_path: str, source_url: str) -> List[ParsedSegment]:
        """Extract content using pdfplumber (good for tables and layout)"""
        segments = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract tables first
                    if self.config.extract_tables:
                        table_segments = self._extract_tables_pdfplumber(page, page_num, source_url)
                        segments.extend(table_segments)

                    # Extract text blocks
                    text_segments = self._extract_text_blocks_pdfplumber(page, page_num, source_url)
                    segments.extend(text_segments)

        except Exception as e:
            logger.error("PDFPlumber extraction failed", path=pdf_path, error=str(e))

        return segments

    def _extract_with_pymupdf(self, pdf_path: str, source_url: str) -> List[ParsedSegment]:
        """Extract content using PyMuPDF (good for text positioning)"""
        segments = []

        try:
            doc = pymupdf.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Extract text blocks with formatting
                text_segments = self._extract_text_blocks_pymupdf(page, page_num + 1, source_url)
                segments.extend(text_segments)

            doc.close()

        except Exception as e:
            logger.error("PyMuPDF extraction failed", path=pdf_path, error=str(e))

        return segments

    def _extract_tables_pdfplumber(self, page, page_num: int, source_url: str) -> List[ParsedSegment]:
        """Extract tables using pdfplumber"""
        segments = []

        tables = page.extract_tables()
        if not tables:
            return segments

        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:  # Skip empty or single-row tables
                continue

            # Format table as text
            table_text = self._format_table_text(table)

            if len(table_text) >= self.config.min_text_length:
                # Estimate coordinates (pdfplumber doesn't provide exact table coordinates)
                bbox = page.bbox  # Use full page as fallback

                segment = ParsedSegment(
                    source_url=source_url,
                    kind=CitationKind.PDF,
                    page_num=page_num,
                    line_start=1,  # Approximate
                    line_end=len(table),
                    text=table_text,
                    context_tags=['table', f'table_{table_idx}']
                )

                segments.append(segment)

        return segments

    def _extract_text_blocks_pdfplumber(self, page, page_num: int, source_url: str) -> List[ParsedSegment]:
        """Extract text blocks using pdfplumber"""
        segments = []

        try:
            # Extract text with character-level details
            chars = page.chars
            if not chars:
                return segments

            # Group characters into lines and blocks
            text_blocks = self._group_chars_into_blocks(chars, page_num)

            for block in text_blocks:
                if len(block.text.strip()) >= self.config.min_text_length:
                    segment = ParsedSegment(
                        source_url=source_url,
                        kind=CitationKind.PDF,
                        page_num=block.page_num,
                        line_start=block.line_start,
                        line_end=block.line_end,
                        text=block.text,
                        context_tags=['text_block'] + (['heading'] if block.is_heading else [])
                    )

                    segments.append(segment)

        except Exception as e:
            logger.warning("Failed to extract text blocks with pdfplumber", page_num=page_num, error=str(e))

        return segments

    def _extract_text_blocks_pymupdf(self, page, page_num: int, source_url: str) -> List[ParsedSegment]:
        """Extract text blocks using PyMuPDF"""
        segments = []

        try:
            # Get text blocks with positioning
            blocks = page.get_text("dict")["blocks"]

            line_counter = 1

            for block in blocks:
                if "lines" not in block:  # Skip image blocks
                    continue

                block_text_parts = []
                block_line_start = line_counter

                for line in block["lines"]:
                    line_text_parts = []

                    for span in line["spans"]:
                        text = span.get("text", "").strip()
                        if text:
                            line_text_parts.append(text)

                    line_text = " ".join(line_text_parts)
                    if line_text:
                        block_text_parts.append(line_text)
                        line_counter += 1

                if block_text_parts:
                    block_text = "\n".join(block_text_parts)

                    if len(block_text.strip()) >= self.config.min_text_length:
                        # Detect if this looks like a heading
                        is_heading = self._detect_heading(block_text_parts[0] if block_text_parts else "")

                        segment = ParsedSegment(
                            source_url=source_url,
                            kind=CitationKind.PDF,
                            page_num=page_num,
                            line_start=block_line_start,
                            line_end=line_counter - 1,
                            text=block_text,
                            context_tags=['text_block'] + (['heading'] if is_heading else [])
                        )

                        segments.append(segment)

        except Exception as e:
            logger.warning("Failed to extract text blocks with PyMuPDF", page_num=page_num, error=str(e))

        return segments

    def _group_chars_into_blocks(self, chars: List[Dict], page_num: int) -> List[TextBlock]:
        """Group individual characters into meaningful text blocks"""
        if not chars:
            return []

        # Sort characters by position (top to bottom, left to right)
        sorted_chars = sorted(chars, key=lambda c: (round(c.get('top', 0), 1), round(c.get('x0', 0), 1)))

        blocks = []
        current_block_chars = []
        current_line = None

        for char in sorted_chars:
            char_top = round(char.get('top', 0), 1)

            # Check if we're on a new line (different y-position)
            if current_line is None or abs(char_top - current_line) > 2:  # 2 point tolerance
                # Start new block if significant vertical gap
                if current_block_chars and current_line is not None and abs(char_top - current_line) > 10:
                    # Finish current block
                    block = self._create_text_block_from_chars(current_block_chars, page_num)
                    if block:
                        blocks.append(block)
                    current_block_chars = []

                current_line = char_top

            current_block_chars.append(char)

        # Process final block
        if current_block_chars:
            block = self._create_text_block_from_chars(current_block_chars, page_num)
            if block:
                blocks.append(block)

        return blocks

    def _create_text_block_from_chars(self, chars: List[Dict], page_num: int) -> Optional[TextBlock]:
        """Create a TextBlock from a list of characters"""
        if not chars:
            return None

        # Extract text
        text = ''.join(char.get('text', '') for char in chars).strip()

        if not text or len(text) < self.config.min_text_length:
            return None

        # Calculate bounding box
        x0s = [char.get('x0', 0) for char in chars]
        y0s = [char.get('top', 0) for char in chars]  # pdfplumber uses 'top' for y0
        x1s = [char.get('x1', 0) for char in chars]
        y1s = [char.get('bottom', 0) for char in chars]  # pdfplumber uses 'bottom' for y1

        bbox = (min(x0s), min(y0s), max(x1s), max(y1s))

        # Estimate font size (use most common size)
        font_sizes = [char.get('size', 0) for char in chars if char.get('size', 0) > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

        # Detect heading
        is_heading = self._detect_heading(text, avg_font_size)

        # Estimate line numbers (simplified)
        line_start = 1  # Would need more sophisticated line tracking
        line_end = text.count('\n') + 1

        return TextBlock(
            text=text,
            page_num=page_num,
            bbox=bbox,
            line_start=line_start,
            line_end=line_end,
            font_size=avg_font_size,
            is_heading=is_heading
        )

    def _format_table_text(self, table: List[List[str]]) -> str:
        """Format table data as readable text"""
        if not table:
            return ""

        lines = ["TABLE:"]

        # Assume first row is headers
        headers = table[0] if table else []
        data_rows = table[1:] if len(table) > 1 else []

        if headers:
            lines.append("HEADERS: " + " | ".join(str(h) for h in headers if h))
            lines.append("-" * 50)

        for row in data_rows[:10]:  # Limit to 10 rows
            if any(cell for cell in row if cell):  # Skip empty rows
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                lines.append(" | ".join(cleaned_row))

        if len(data_rows) > 10:
            lines.append(f"... and {len(data_rows) - 10} more rows")

        return "\n".join(lines)

    def _detect_heading(self, text: str, font_size: float = 0) -> bool:
        """Detect if text is likely a heading"""
        text = text.strip()

        # Length-based detection
        if len(text) < 5 or len(text) > 100:
            return False

        # Pattern-based detection
        heading_patterns = [
            r'^[A-Z][A-Z\s]+$',  # ALL CAPS
            r'^\d+\.\s+[A-Z]',   # 1. Title format
            r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$',  # Title Case
        ]

        for pattern in heading_patterns:
            if re.match(pattern, text):
                return True

        # Font size based (if available)
        if font_size > 14:  # Larger than typical body text
            return True

        # Keyword-based detection for common headings
        heading_keywords = [
            'requirements', 'admission', 'application', 'deadline',
            'english proficiency', 'test scores', 'documents',
            'eligibility', 'prerequisites', 'contact'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in heading_keywords)

    def _filter_and_merge_segments(self, segments: List[ParsedSegment]) -> List[ParsedSegment]:
        """Filter segments by relevance and merge similar ones"""
        # Score segments by relevance
        scored_segments = []

        for segment in segments:
            relevance_score = self._calculate_relevance_score(segment.text)

            # Only keep segments with minimum relevance
            if relevance_score > 0.5:  # Threshold for PDF content
                scored_segments.append((segment, relevance_score))

        # Sort by page number, then by line start, then by relevance
        scored_segments.sort(key=lambda x: (x[0].page_num, x[0].line_start or 0, -x[1]))

        # Remove duplicates based on text similarity
        unique_segments = []
        seen_texts = set()

        for segment, score in scored_segments:
            # Create a normalized version for duplicate detection
            normalized_text = ' '.join(segment.text.split()).lower()[:100]

            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_segments.append(segment)

        return unique_segments

    def _calculate_relevance_score(self, text: str) -> float:
        """Calculate relevance score for admissions content"""
        text_lower = text.lower()
        score = 0.0

        # Keyword matching
        for keyword in self.admissions_keywords:
            if keyword in text_lower:
                score += 1.0

        # Pattern matching
        patterns = [
            r'\btoefl\s+\d{2,3}\b',  # TOEFL scores
            r'\bielts\s+\d\.\d\b',   # IELTS scores
            r'\bgre\s+\d{3}\b',      # GRE scores
            r'\bcode\s*:?\s*\d{4}\b', # Institution codes
            r'\bdeadline\s*:?\s*\w+\s+\d{1,2}\b',  # Deadlines
            r'\$\d+',                # Fees
            r'\bgpa\s+\d\.\d\b'      # GPA requirements
        ]

        for pattern in patterns:
            if re.search(pattern, text_lower):
                score += 2.0

        # Length bonus (longer, more detailed content is often more relevant)
        if len(text) > 200:
            score += 1.0

        if len(text) > 500:
            score += 1.0

        return score


async def main():
    """Test the PDF reader"""
    # This would need an actual PDF file to test
    print("PDF Reader test - requires actual PDF file")

    # Create a mock test
    config = PDFExtractionConfig()
    reader = PDFReader(config)

    # Test text analysis
    sample_texts = [
        "TOEFL minimum score of 100 required for international students",
        "Application deadlines: Fall - January 15, Spring - October 1",
        "Admission Requirements",
        "Random text about campus life and dining options"
    ]

    print("\n=== Relevance Scoring Test ===")
    for text in sample_texts:
        score = reader._calculate_relevance_score(text)
        print(f"Score {score:4.1f}: {text}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())