"""
HTML Content Segmentation
Intelligently chunks HTML content into semantically meaningful segments
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag, NavigableString
from selectolax.parser import HTMLParser
import structlog
from pathlib import Path
import sys

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from schemas.requirements import ParsedSegment, CitationKind

logger = structlog.get_logger()


@dataclass
class SegmentationConfig:
    """Configuration for HTML segmentation"""
    max_segment_length: int = 2000  # Max characters per segment
    min_segment_length: int = 50    # Min characters to keep segment
    preserve_structure: bool = True  # Keep heading hierarchy
    extract_tables: bool = True     # Extract tables separately
    extract_lists: bool = True      # Extract lists separately
    noise_removal: bool = True      # Remove navigation, footer, etc.


class HTMLSegmenter:
    """Segments HTML content into meaningful chunks for LLM processing"""

    def __init__(self, config: SegmentationConfig = None):
        self.config = config or SegmentationConfig()

        # Keywords that indicate admissions-related content
        self.admissions_keywords = {
            'high_priority': {
                'toefl', 'ielts', 'duolingo', 'english proficiency',
                'gre', 'gmat', 'lsat', 'mcat',
                'application deadline', 'deadline', 'due date',
                'admission requirements', 'requirements',
                'application fee', 'fee',
                'letters of recommendation', 'recommendation',
                'statement of purpose', 'personal statement',
                'transcript', 'gpa'
            },
            'medium_priority': {
                'graduate', 'masters', 'phd', 'doctoral',
                'apply', 'application', 'admissions',
                'program', 'degree',
                'international students', 'visa',
                'fall', 'spring', 'summer', 'semester'
            },
            'context_keywords': {
                'eligibility', 'prerequisite', 'background',
                'contact', 'email', 'phone', 'office',
                'academic', 'research', 'thesis'
            }
        }

        # CSS selectors for noise removal
        self.noise_selectors = [
            'nav', 'header', 'footer', 'aside',
            '.navigation', '.nav', '.menu',
            '.sidebar', '.breadcrumb', '.breadcrumbs',
            '.social', '.share', '.sharing',
            '.advertisement', '.ad', '.ads',
            '#header', '#footer', '#nav', '#navigation',
            '#sidebar', '#menu',
            '.cookie-banner', '.cookie-notice'
        ]

    def segment_html(self, html_content: str, source_url: str) -> List[ParsedSegment]:
        """
        Main segmentation method

        Args:
            html_content: Raw HTML content
            source_url: Source URL for reference

        Returns:
            List of ParsedSegment objects
        """
        logger.info("Starting HTML segmentation", url=source_url)

        # Parse HTML
        soup = BeautifulSoup(html_content, 'lxml')

        # Remove noise
        if self.config.noise_removal:
            self._remove_noise(soup)

        segments = []

        # Extract different content types
        if self.config.preserve_structure:
            segments.extend(self._extract_heading_sections(soup, source_url))

        if self.config.extract_tables:
            segments.extend(self._extract_tables(soup, source_url))

        if self.config.extract_lists:
            segments.extend(self._extract_lists(soup, source_url))

        # Extract remaining paragraph content
        segments.extend(self._extract_paragraphs(soup, source_url))

        # Filter and prioritize segments
        filtered_segments = self._filter_and_prioritize(segments)

        logger.info("HTML segmentation completed",
                   url=source_url,
                   total_segments=len(segments),
                   filtered_segments=len(filtered_segments))

        return filtered_segments

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Remove navigation, footer, and other noise elements"""
        for selector in self.noise_selectors:
            try:
                if selector.startswith('.') or selector.startswith('#'):
                    # CSS class or ID selector
                    elements = soup.select(selector)
                else:
                    # Tag selector
                    elements = soup.find_all(selector)

                for element in elements:
                    element.decompose()
            except Exception as e:
                logger.debug("Error removing noise element", selector=selector, error=str(e))

        # Remove script and style tags
        for element in soup(['script', 'style', 'meta', 'link']):
            element.decompose()

    def _extract_heading_sections(self, soup: BeautifulSoup, source_url: str) -> List[ParsedSegment]:
        """Extract content organized by headings"""
        segments = []

        # Find all headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        for heading in headings:
            # Get heading text
            heading_text = self._clean_text(heading.get_text())

            if not heading_text or len(heading_text) < 10:
                continue

            # Collect content until next heading of same or higher level
            content_elements = []
            heading_level = int(heading.name[1])  # h1 -> 1, h2 -> 2, etc.

            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag):
                    # Stop at next heading of same or higher level
                    if sibling.name and sibling.name.startswith('h'):
                        sibling_level = int(sibling.name[1])
                        if sibling_level <= heading_level:
                            break

                    content_elements.append(sibling)
                elif isinstance(sibling, NavigableString):
                    text = str(sibling).strip()
                    if text:
                        content_elements.append(sibling)

            # Combine content
            content_text = self._extract_text_from_elements(content_elements)

            if content_text and len(content_text.strip()) >= self.config.min_segment_length:
                # Generate XPath selector for the heading
                xpath_selector = self._generate_xpath(heading)

                # Combine heading and content
                full_text = f"{heading_text}\n\n{content_text}"

                segment = ParsedSegment(
                    source_url=source_url,
                    kind=CitationKind.HTML,
                    selector=xpath_selector,
                    text=full_text,
                    context_tags=[heading.name, 'section']
                )

                segments.append(segment)

        return segments

    def _extract_tables(self, soup: BeautifulSoup, source_url: str) -> List[ParsedSegment]:
        """Extract table content with structure preserved"""
        segments = []

        tables = soup.find_all('table')

        for i, table in enumerate(tables):
            # Extract table structure
            table_data = self._parse_table_structure(table)

            if not table_data['rows'] or len(str(table_data)) < self.config.min_segment_length:
                continue

            # Find table context (preceding heading or caption)
            context = self._find_table_context(table)

            # Format table as text
            table_text = self._format_table_as_text(table_data, context)

            xpath_selector = self._generate_xpath(table)

            segment = ParsedSegment(
                source_url=source_url,
                kind=CitationKind.HTML,
                selector=xpath_selector,
                text=table_text,
                context_tags=['table', 'structured_data']
            )

            segments.append(segment)

        return segments

    def _extract_lists(self, soup: BeautifulSoup, source_url: str) -> List[ParsedSegment]:
        """Extract list content (ul, ol)"""
        segments = []

        lists = soup.find_all(['ul', 'ol'])

        for list_elem in lists:
            # Skip if nested inside a table (already captured)
            if list_elem.find_parent('table'):
                continue

            # Extract list items
            list_items = list_elem.find_all('li', recursive=False)

            if not list_items:
                continue

            # Combine list items
            list_text_parts = []
            for li in list_items:
                item_text = self._clean_text(li.get_text())
                if item_text:
                    list_text_parts.append(f"• {item_text}")

            list_text = '\n'.join(list_text_parts)

            if len(list_text) >= self.config.min_segment_length:
                # Find context (preceding heading)
                context = self._find_list_context(list_elem)

                if context:
                    full_text = f"{context}\n\n{list_text}"
                else:
                    full_text = list_text

                xpath_selector = self._generate_xpath(list_elem)

                segment = ParsedSegment(
                    source_url=source_url,
                    kind=CitationKind.HTML,
                    selector=xpath_selector,
                    text=full_text,
                    context_tags=[list_elem.name, 'list']
                )

                segments.append(segment)

        return segments

    def _extract_paragraphs(self, soup: BeautifulSoup, source_url: str) -> List[ParsedSegment]:
        """Extract standalone paragraph content"""
        segments = []

        paragraphs = soup.find_all('p')

        for paragraph in paragraphs:
            # Skip if already captured in heading sections or tables
            if paragraph.find_parent(['table', 'nav', 'header', 'footer']):
                continue

            para_text = self._clean_text(paragraph.get_text())

            if len(para_text) >= self.config.min_segment_length:
                xpath_selector = self._generate_xpath(paragraph)

                segment = ParsedSegment(
                    source_url=source_url,
                    kind=CitationKind.HTML,
                    selector=xpath_selector,
                    text=para_text,
                    context_tags=['paragraph']
                )

                segments.append(segment)

        return segments

    def _parse_table_structure(self, table: Tag) -> Dict[str, Any]:
        """Parse table into structured format"""
        headers = []
        rows = []

        # Find header row
        header_row = table.find('tr')
        if header_row:
            for th in header_row.find_all(['th', 'td']):
                headers.append(self._clean_text(th.get_text()))

        # Find data rows
        all_rows = table.find_all('tr')
        data_rows = all_rows[1:] if headers else all_rows

        for row in data_rows:
            cells = []
            for td in row.find_all(['td', 'th']):
                cells.append(self._clean_text(td.get_text()))

            if cells:  # Only add non-empty rows
                rows.append(cells)

        return {
            'headers': headers,
            'rows': rows,
            'row_count': len(rows),
            'col_count': len(headers) if headers else (len(rows[0]) if rows else 0)
        }

    def _format_table_as_text(self, table_data: Dict[str, Any], context: str = "") -> str:
        """Format table data as readable text"""
        lines = []

        if context:
            lines.append(f"TABLE: {context}")
            lines.append("")

        # Add headers
        if table_data['headers']:
            lines.append("HEADERS: " + " | ".join(table_data['headers']))
            lines.append("-" * 50)

        # Add rows
        for i, row in enumerate(table_data['rows'][:10]):  # Limit to 10 rows
            if table_data['headers'] and len(row) == len(table_data['headers']):
                # Format as key-value pairs
                row_parts = []
                for header, cell in zip(table_data['headers'], row):
                    if cell.strip():
                        row_parts.append(f"{header}: {cell}")
                lines.append(" | ".join(row_parts))
            else:
                # Format as simple row
                lines.append(" | ".join(row))

        if len(table_data['rows']) > 10:
            lines.append(f"... and {len(table_data['rows']) - 10} more rows")

        return '\n'.join(lines)

    def _find_table_context(self, table: Tag) -> str:
        """Find contextual information for a table"""
        # Check for caption
        caption = table.find('caption')
        if caption:
            return self._clean_text(caption.get_text())

        # Check for preceding heading
        for sibling in table.previous_siblings:
            if isinstance(sibling, Tag):
                if sibling.name and sibling.name.startswith('h'):
                    return self._clean_text(sibling.get_text())
                elif sibling.name == 'p':
                    text = self._clean_text(sibling.get_text())
                    if len(text) < 200:  # Short descriptive paragraph
                        return text

        return ""

    def _find_list_context(self, list_elem: Tag) -> str:
        """Find contextual information for a list"""
        # Check for preceding heading or paragraph
        for sibling in list_elem.previous_siblings:
            if isinstance(sibling, Tag):
                if sibling.name and sibling.name.startswith('h'):
                    return self._clean_text(sibling.get_text())
                elif sibling.name == 'p':
                    text = self._clean_text(sibling.get_text())
                    if len(text) < 300:  # Short descriptive paragraph
                        return text

        return ""

    def _extract_text_from_elements(self, elements: List) -> str:
        """Extract clean text from a list of elements"""
        text_parts = []

        for element in elements:
            if isinstance(element, Tag):
                text = self._clean_text(element.get_text())
                if text:
                    text_parts.append(text)
            elif isinstance(element, NavigableString):
                text = self._clean_text(str(element))
                if text:
                    text_parts.append(text)

        return '\n\n'.join(text_parts)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove common artifacts
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\r\n]+', '\n', text)

        return text.strip()

    def _generate_xpath(self, element: Tag) -> str:
        """Generate XPath selector for an element"""
        try:
            # Simple XPath generation - can be enhanced
            parts = []

            current = element
            while current and hasattr(current, 'name') and current.name != '[document]':
                tag = current.name

                # Add index if there are multiple similar siblings
                siblings = current.parent.find_all(tag) if current.parent else [current]
                if len(siblings) > 1:
                    index = siblings.index(current) + 1
                    parts.append(f"{tag}[{index}]")
                else:
                    parts.append(tag)

                current = current.parent

            parts.reverse()
            xpath = "//" + "/".join(parts)

            return xpath

        except Exception:
            # Fallback to simple selector
            return f"//{element.name}"

    def _filter_and_prioritize(self, segments: List[ParsedSegment]) -> List[ParsedSegment]:
        """Filter segments by relevance and prioritize"""
        scored_segments = []

        for segment in segments:
            score = self._calculate_relevance_score(segment.text)

            # Only keep segments with minimum relevance or length
            if score > 0 or len(segment.text) > 500:
                scored_segments.append((segment, score))

        # Sort by relevance score (descending)
        scored_segments.sort(key=lambda x: x[1], reverse=True)

        # Return segments without scores
        return [segment for segment, score in scored_segments]

    def _calculate_relevance_score(self, text: str) -> float:
        """Calculate relevance score for admissions content"""
        text_lower = text.lower()
        score = 0.0

        # High priority keywords
        for keyword in self.admissions_keywords['high_priority']:
            if keyword in text_lower:
                score += 2.0

        # Medium priority keywords
        for keyword in self.admissions_keywords['medium_priority']:
            if keyword in text_lower:
                score += 1.0

        # Context keywords
        for keyword in self.admissions_keywords['context_keywords']:
            if keyword in text_lower:
                score += 0.5

        # Bonus for numeric patterns (scores, dates, codes)
        if re.search(r'\b\d{3,4}\b', text):  # 3-4 digit numbers (test scores, codes)
            score += 1.0

        if re.search(r'\b\d+\s*(?:months?|years?|days?)\b', text):  # Time periods
            score += 0.5

        # Length penalty for very short segments
        if len(text) < 100:
            score *= 0.5

        return score


async def main():
    """Test the HTML segmenter"""
    sample_html = """
    <html>
    <body>
        <nav>Skip this navigation</nav>

        <h1>Graduate Admissions</h1>
        <p>Welcome to our graduate programs.</p>

        <h2>English Proficiency Requirements</h2>
        <p>All international students must demonstrate English proficiency through one of the following:</p>
        <ul>
            <li>TOEFL minimum score of 100 (Reading: 22, Listening: 22, Speaking: 22, Writing: 22)</li>
            <li>IELTS minimum score of 7.0</li>
            <li>Duolingo English Test minimum score of 120</li>
        </ul>
        <p>Institution code for TOEFL: 4704</p>

        <h2>Application Deadlines</h2>
        <table>
            <tr><th>Program</th><th>Priority Deadline</th><th>Final Deadline</th></tr>
            <tr><td>MS Computer Science</td><td>December 1</td><td>January 15</td></tr>
            <tr><td>PhD Computer Science</td><td>December 1</td><td>January 15</td></tr>
        </table>

        <footer>Copyright University</footer>
    </body>
    </html>
    """

    segmenter = HTMLSegmenter()
    segments = segmenter.segment_html(sample_html, "https://example.edu/admissions")

    print(f"\n=== Found {len(segments)} segments ===")
    for i, segment in enumerate(segments, 1):
        print(f"\n{i}. SEGMENT ({', '.join(segment.context_tags)})")
        print(f"   Selector: {segment.selector}")
        print(f"   Text: {segment.text[:200]}...")
        if len(segment.text) > 200:
            print(f"   [{len(segment.text)} total characters]")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())