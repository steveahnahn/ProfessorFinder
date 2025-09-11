"""
Social Psychology Graduate Programs Module
Comprehensive data structure for top universities and social psychology programs
with international student requirements and faculty information
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class DataSource(Enum):
    """Track where data comes from"""
    OFFICIAL_WEBSITE = "official_website"
    DEPARTMENT_PAGE = "department_page"
    ADMISSIONS_PORTAL = "admissions_portal"
    FACULTY_DIRECTORY = "faculty_directory"
    MANUAL_VERIFICATION = "manual_verification"

@dataclass
class InternationalRequirements:
    """Complete requirements for international students"""
    # English Proficiency
    toefl_min: Optional[int] = None
    toefl_ibt_min: Optional[int] = None
    ielts_min: Optional[float] = None
    duolingo_min: Optional[int] = None
    pte_min: Optional[int] = None
    english_waiver_conditions: Optional[str] = None
    
    # Standardized Tests
    gre_required: bool = True
    gre_general_min: Optional[int] = None
    gre_verbal_min: Optional[int] = None
    gre_quant_min: Optional[int] = None
    gre_writing_min: Optional[float] = None
    gre_subject_psych: bool = False
    gre_waived_conditions: Optional[str] = None
    
    # Academic Requirements
    gpa_min: Optional[float] = None
    gpa_scale: str = "4.0"
    transcript_evaluation_required: bool = True
    wes_or_ece_required: bool = False
    
    # Application Documents
    letters_of_rec: int = 3
    statement_of_purpose: bool = True
    personal_statement: bool = False
    research_statement: bool = False
    writing_sample: bool = False
    writing_sample_pages: Optional[int] = None
    cv_required: bool = True
    diversity_statement: bool = False
    
    # Financial Requirements
    financial_statement_required: bool = True
    funding_amount_required: Optional[int] = None
    funding_guaranteed: bool = False
    assistantship_available: bool = True
    
    # Visa & Legal
    f1_eligible: bool = True
    j1_eligible: bool = False
    cpt_available: bool = True
    opt_available: bool = True
    
    # Deadlines & Fees
    application_fee: Optional[int] = None
    application_fee_waiver_available: bool = False
    deadline_fall: Optional[str] = None
    deadline_spring: Optional[str] = None
    deadline_international_different: bool = False
    
    # Additional Notes
    special_requirements: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class FacultyMember:
    """Detailed faculty information for social psychology"""
    name: str
    title: str
    research_areas: List[str]
    current_projects: List[str] = field(default_factory=list)
    accepting_students: Optional[bool] = None
    email: Optional[str] = None
    website: Optional[str] = None
    google_scholar: Optional[str] = None
    recent_publications: List[str] = field(default_factory=list)
    h_index: Optional[int] = None
    total_citations: Optional[int] = None
    grants_active: List[str] = field(default_factory=list)
    lab_name: Optional[str] = None
    lab_website: Optional[str] = None

@dataclass
class ProgramDetails:
    """Complete program information with data sourcing"""
    # Basic Information
    university_name: str
    program_name: str
    degree_type: str  # PhD, MA/PhD, MS/PhD
    department: str
    
    # Rankings
    overall_university_ranking: Optional[int] = None
    psychology_dept_ranking: Optional[int] = None
    social_psych_ranking: Optional[int] = None
    
    # Program Details
    program_duration_years: Optional[int] = None
    cohort_size: Optional[int] = None
    total_applications: Optional[int] = None
    acceptance_rate: Optional[float] = None
    
    # Requirements
    international_requirements: InternationalRequirements = field(default_factory=InternationalRequirements)
    
    # Faculty (Top 3 for social psychology)
    top_faculty: List[FacultyMember] = field(default_factory=list)
    total_social_psych_faculty: Optional[int] = None
    
    # Links & Resources
    program_website: Optional[str] = None
    admissions_website: Optional[str] = None
    application_portal: Optional[str] = None
    international_services: Optional[str] = None
    
    # Data Tracking
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: Dict[str, DataSource] = field(default_factory=dict)
    verification_status: str = "pending"  # pending, verified, needs_update
    update_notes: List[str] = field(default_factory=list)

# Top 30 US Universities (US News 2024 + Research Impact)
TOP_30_UNIVERSITIES = [
    "Princeton University",
    "Massachusetts Institute of Technology", 
    "Harvard University",
    "Stanford University",
    "Yale University",
    "University of Pennsylvania",
    "California Institute of Technology",
    "Duke University",
    "Brown University",
    "Johns Hopkins University",
    "Northwestern University",
    "Columbia University",
    "Cornell University",
    "University of Chicago",
    "University of California, Berkeley",
    "University of California, Los Angeles",
    "Dartmouth College",
    "Vanderbilt University",
    "University of Notre Dame",
    "University of Michigan",
    "Georgetown University",
    "University of North Carolina at Chapel Hill",
    "Carnegie Mellon University",
    "Emory University",
    "University of Virginia",
    "Washington University in St. Louis",
    "University of California, San Diego",
    "University of Southern California",
    "University of California, Davis",
    "University of Texas at Austin"
]

# Top 30 Social Psychology Graduate Programs
# Based on faculty research impact, program reputation, and placement records
TOP_30_SOCIAL_PSYCH_PROGRAMS = [
    "Stanford University",
    "University of Michigan",
    "Harvard University",
    "Yale University",
    "Princeton University",
    "University of California, Berkeley",
    "University of California, Los Angeles",
    "Ohio State University",
    "Cornell University",
    "University of Minnesota",
    "University of Texas at Austin",
    "New York University",
    "University of California, San Diego",
    "University of North Carolina at Chapel Hill",
    "University of Pennsylvania",
    "Columbia University",
    "Northwestern University",
    "University of Illinois at Urbana-Champaign",
    "University of Washington",
    "Indiana University",
    "University of Colorado Boulder",
    "University of Wisconsin-Madison",
    "Duke University",
    "University of Virginia",
    "University of California, Santa Barbara",
    "Arizona State University",
    "University of Oregon",
    "University of Iowa",
    "University of Pittsburgh",
    "Boston University"
]

class ProgramDatabase:
    """Database for managing program information"""
    
    def __init__(self):
        self.programs: Dict[str, ProgramDetails] = {}
        self.last_full_update: Optional[datetime] = None
        
    def add_program(self, program: ProgramDetails):
        """Add or update a program"""
        self.programs[program.university_name] = program
        
    def get_program(self, university_name: str) -> Optional[ProgramDetails]:
        """Get program by university name"""
        return self.programs.get(university_name)
        
    def get_programs_by_group(self, group: str) -> List[ProgramDetails]:
        """Get programs by grouping (top_universities or top_social_psych)"""
        if group == "top_universities":
            universities = TOP_30_UNIVERSITIES
        elif group == "top_social_psych":
            universities = TOP_30_SOCIAL_PSYCH_PROGRAMS
        else:
            return []
            
        return [self.programs[uni] for uni in universities if uni in self.programs]
    
    def get_programs_needing_update(self, days_old: int = 365) -> List[str]:
        """Get list of programs that need updating"""
        needs_update = []
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for uni_name, program in self.programs.items():
            if program.last_updated < cutoff_date:
                needs_update.append(uni_name)
                
        return needs_update
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export database to dictionary for CSV export"""
        export_data = []
        
        for program in self.programs.values():
            reqs = program.international_requirements
            
            # Create faculty summary
            faculty_info = []
            for faculty in program.top_faculty[:3]:
                faculty_info.append({
                    "name": faculty.name,
                    "research": ", ".join(faculty.research_areas[:3]),
                    "accepting": faculty.accepting_students
                })
            
            export_data.append({
                "University": program.university_name,
                "Program": program.program_name,
                "Department": program.department,
                "Overall Ranking": program.overall_university_ranking,
                "Social Psych Ranking": program.social_psych_ranking,
                
                # Requirements
                "GPA Minimum": reqs.gpa_min,
                "GRE Required": reqs.gre_required,
                "GRE Waived": reqs.gre_waived_conditions,
                "TOEFL Minimum": reqs.toefl_min,
                "IELTS Minimum": reqs.ielts_min,
                "Letters of Rec": reqs.letters_of_rec,
                "Application Fee": reqs.application_fee,
                "Fall Deadline": reqs.deadline_fall,
                
                # Faculty
                "Faculty 1": faculty_info[0] if len(faculty_info) > 0 else None,
                "Faculty 2": faculty_info[1] if len(faculty_info) > 1 else None,
                "Faculty 3": faculty_info[2] if len(faculty_info) > 2 else None,
                
                # Additional Info
                "Acceptance Rate": program.acceptance_rate,
                "Funding Guaranteed": reqs.funding_guaranteed,
                "Program Website": program.program_website,
                "Last Updated": program.last_updated.strftime("%Y-%m-%d"),
                "Data Sources": ", ".join(program.data_sources.keys())
            })
            
        return export_data

# Initialize global database
program_db = ProgramDatabase()

def get_program_database() -> ProgramDatabase:
    """Get the global program database instance"""
    return program_db