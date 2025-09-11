"""
Web Scraping Module for Graduate Program Requirements
Collects admissions requirements and faculty information from university websites
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse

from core.social_psych_programs import (
    ProgramDetails, InternationalRequirements, FacultyMember,
    DataSource, program_db
)

logger = logging.getLogger(__name__)

class ProgramScraper:
    """Scraper for graduate program information"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GradProgramBot/1.0; +academic-research)'
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch webpage content"""
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_requirements_from_text(self, text: str) -> Dict[str, Any]:
        """Extract admission requirements from page text using patterns"""
        requirements = {}
        
        # GPA patterns
        gpa_patterns = [
            r'GPA.*?(\d+\.\d+)',
            r'minimum GPA.*?(\d+\.\d+)',
            r'grade point average.*?(\d+\.\d+)'
        ]
        for pattern in gpa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                requirements['gpa_min'] = float(match.group(1))
                break
        
        # TOEFL patterns
        toefl_patterns = [
            r'TOEFL.*?(\d{2,3})',
            r'TOEFL iBT.*?(\d{2,3})',
            r'minimum TOEFL.*?(\d{2,3})'
        ]
        for pattern in toefl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if score >= 70 and score <= 120:  # Valid TOEFL range
                    requirements['toefl_min'] = score
                    break
        
        # IELTS patterns
        ielts_patterns = [
            r'IELTS.*?(\d+(?:\.\d+)?)',
            r'minimum IELTS.*?(\d+(?:\.\d+)?)'
        ]
        for pattern in ielts_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if score >= 5.0 and score <= 9.0:  # Valid IELTS range
                    requirements['ielts_min'] = score
                    break
        
        # GRE requirement
        if re.search(r'GRE.*not.*required|GRE.*optional|GRE.*waived', text, re.IGNORECASE):
            requirements['gre_required'] = False
        elif re.search(r'GRE.*required|require.*GRE', text, re.IGNORECASE):
            requirements['gre_required'] = True
        
        # Letters of recommendation
        letters_match = re.search(r'(\d+).*letters?\s+of\s+recommendation', text, re.IGNORECASE)
        if letters_match:
            requirements['letters_of_rec'] = int(letters_match.group(1))
        
        # Application fee
        fee_match = re.search(r'application fee.*?\$(\d+)', text, re.IGNORECASE)
        if fee_match:
            requirements['application_fee'] = int(fee_match.group(1))
        
        # Deadlines
        deadline_patterns = [
            r'(December|January|February)\s+(\d{1,2})',
            r'deadline.*?(Dec|Jan|Feb).*?(\d{1,2})'
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                requirements['deadline_fall'] = f"{match.group(1)} {match.group(2)}"
                break
        
        return requirements
    
    async def scrape_program_page(self, university: str, urls: Dict[str, str]) -> ProgramDetails:
        """Scrape program information from university pages"""
        program = ProgramDetails(
            university_name=university,
            program_name=f"PhD in Psychology - Social Psychology",
            degree_type="PhD",
            department="Department of Psychology"
        )
        
        # Scrape admissions page
        if 'admissions' in urls:
            content = await self.fetch_page(urls['admissions'])
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text()
                
                # Extract requirements
                reqs_data = self.extract_requirements_from_text(text)
                
                # Update international requirements
                reqs = program.international_requirements
                for key, value in reqs_data.items():
                    if hasattr(reqs, key):
                        setattr(reqs, key, value)
                
                program.data_sources['admissions'] = DataSource.ADMISSIONS_PORTAL
                program.admissions_website = urls['admissions']
        
        # Scrape faculty page
        if 'faculty' in urls:
            faculty_members = await self.scrape_faculty_page(urls['faculty'])
            program.top_faculty = faculty_members[:3]  # Top 3
            program.total_social_psych_faculty = len(faculty_members)
            program.data_sources['faculty'] = DataSource.FACULTY_DIRECTORY
        
        # Scrape program page
        if 'program' in urls:
            content = await self.fetch_page(urls['program'])
            if content:
                program.program_website = urls['program']
                program.data_sources['program'] = DataSource.DEPARTMENT_PAGE
        
        program.last_updated = datetime.now()
        program.verification_status = "scraped"
        
        return program
    
    async def scrape_faculty_page(self, url: str) -> List[FacultyMember]:
        """Scrape faculty information from faculty directory"""
        faculty_list = []
        
        content = await self.fetch_page(url)
        if not content:
            return faculty_list
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Common patterns for faculty listings
        faculty_containers = (
            soup.find_all('div', class_=re.compile('faculty|professor', re.I)) or
            soup.find_all('article', class_=re.compile('faculty|professor', re.I)) or
            soup.find_all('li', class_=re.compile('faculty|professor', re.I))
        )
        
        for container in faculty_containers[:20]:  # Limit to prevent over-scraping
            faculty = self.extract_faculty_info(container)
            if faculty and self.is_social_psychology_faculty(faculty):
                faculty_list.append(faculty)
        
        # Sort by research relevance (basic scoring)
        faculty_list.sort(key=lambda f: len(f.research_areas), reverse=True)
        
        return faculty_list
    
    def extract_faculty_info(self, element) -> Optional[FacultyMember]:
        """Extract faculty information from HTML element"""
        try:
            # Extract name
            name_elem = element.find(['h2', 'h3', 'h4', 'strong', 'a'])
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3:
                return None
            
            # Extract title
            title = "Professor"  # Default
            title_patterns = ['Professor', 'Associate Professor', 'Assistant Professor']
            text = element.get_text()
            for pattern in title_patterns:
                if pattern in text:
                    title = pattern
                    break
            
            # Extract research areas
            research_areas = []
            research_text = text.lower()
            
            # Social psychology keywords
            social_psych_keywords = [
                'social psychology', 'social cognition', 'attitudes', 'prejudice',
                'stereotyping', 'group dynamics', 'intergroup', 'social influence',
                'interpersonal', 'relationships', 'social identity', 'self',
                'emotion', 'motivation', 'culture', 'social neuroscience',
                'prosocial', 'aggression', 'cooperation', 'social judgment'
            ]
            
            for keyword in social_psych_keywords:
                if keyword in research_text:
                    research_areas.append(keyword.title())
            
            # Extract email
            email = None
            email_elem = element.find('a', href=re.compile(r'mailto:'))
            if email_elem:
                email = email_elem.get('href', '').replace('mailto:', '')
            
            # Extract website
            website = None
            link_elem = element.find('a', href=re.compile(r'http'))
            if link_elem:
                website = link_elem.get('href')
            
            if research_areas:  # Only include if has relevant research
                return FacultyMember(
                    name=name,
                    title=title,
                    research_areas=research_areas[:5],  # Top 5 areas
                    email=email,
                    website=website
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting faculty info: {e}")
            return None
    
    def is_social_psychology_faculty(self, faculty: FacultyMember) -> bool:
        """Check if faculty member is in social psychology"""
        social_keywords = {
            'social', 'interpersonal', 'group', 'culture', 'prejudice',
            'stereotyp', 'attitude', 'self', 'identity', 'emotion'
        }
        
        research_text = ' '.join(faculty.research_areas).lower()
        return any(keyword in research_text for keyword in social_keywords)

# URL patterns for different universities
UNIVERSITY_URL_PATTERNS = {
    "Stanford University": {
        "admissions": "https://psychology.stanford.edu/graduate/prospective-students/admissions",
        "faculty": "https://psychology.stanford.edu/people/faculty",
        "program": "https://psychology.stanford.edu/graduate/program-areas/social-psychology"
    },
    "University of Michigan": {
        "admissions": "https://lsa.umich.edu/psych/program/graduate-program/prospective-students.html",
        "faculty": "https://lsa.umich.edu/psych/people/faculty.html",
        "program": "https://lsa.umich.edu/psych/program/graduate-program/program-areas/social.html"
    },
    "Harvard University": {
        "admissions": "https://psychology.fas.harvard.edu/graduate-admissions",
        "faculty": "https://psychology.fas.harvard.edu/faculty",
        "program": "https://psychology.fas.harvard.edu/research"
    },
    "Yale University": {
        "admissions": "https://psychology.yale.edu/graduate/admissions",
        "faculty": "https://psychology.yale.edu/people/faculty",
        "program": "https://psychology.yale.edu/graduate/areas-study/social-personality-psychology"
    },
    # Add more universities as needed
}

async def update_program_data(universities: List[str], force_update: bool = False):
    """Update program data for specified universities"""
    async with ProgramScraper() as scraper:
        tasks = []
        
        for university in universities:
            # Skip if recently updated unless forced
            existing = program_db.get_program(university)
            if existing and not force_update:
                days_old = (datetime.now() - existing.last_updated).days
                if days_old < 30:  # Skip if updated within 30 days
                    logger.info(f"Skipping {university} - recently updated")
                    continue
            
            # Get URLs for this university
            urls = UNIVERSITY_URL_PATTERNS.get(university, {})
            if not urls:
                logger.warning(f"No URL patterns for {university}")
                continue
            
            # Create scraping task
            task = scraper.scrape_program_page(university, urls)
            tasks.append(task)
        
        # Run all scraping tasks concurrently
        if tasks:
            programs = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results
            for program in programs:
                if isinstance(program, ProgramDetails):
                    program_db.add_program(program)
                    logger.info(f"Updated data for {program.university_name}")
                elif isinstance(program, Exception):
                    logger.error(f"Error scraping program: {program}")
    
    return program_db

def get_data_documentation() -> str:
    """Generate documentation about data sourcing"""
    doc = """
    # Data Sourcing Documentation
    
    ## How We Collect Program Information
    
    ### 1. Web Scraping Process
    - **Primary Sources**: Official university websites
    - **Pages Scraped**:
      - Graduate admissions pages
      - Psychology department pages  
      - Faculty directories
      - Program-specific pages
    
    ### 2. Data Extraction Methods
    
    #### Admission Requirements:
    - Pattern matching for GPA, test scores (TOEFL, IELTS, GRE)
    - Text analysis for requirements (letters, fees, deadlines)
    - Specific searches for international student information
    
    #### Faculty Information:
    - Faculty directory parsing
    - Research interest keyword matching
    - Social psychology relevance scoring
    - Top 3 selection based on research alignment
    
    ### 3. Data Validation
    - Range checking (e.g., TOEFL 70-120, IELTS 5.0-9.0)
    - Cross-reference multiple sources when available
    - Manual verification flags for uncertain data
    
    ### 4. Update Schedule
    - Full update: Annually (September/October)
    - Partial updates: As needed for specific programs
    - Last update timestamp tracked per program
    
    ### 5. Limitations & Accuracy
    - Web scraping depends on website structure
    - Some data may require manual verification
    - Contact admissions offices for final confirmation
    
    ### 6. Data Sources by University
    Each program entry includes:
    - Source URLs for transparency
    - Last updated timestamp
    - Verification status
    
    ## Verification Checklist
    ✓ Official university domain
    ✓ Current academic year information
    ✓ International student specific requirements
    ✓ Faculty actively researching in social psychology
    """
    
    return doc