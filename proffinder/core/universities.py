"""
Curated list of top US universities for psychology/sociology research.
Selected based on:
1. Top university ranking
2. Strong psychology/sociology departments  
3. International student friendly
4. Top field reputation for psych/sociology
5. Located in major US cities
"""

from typing import List, Dict

# US Regional University Groups
NORTHEAST_UNIVERSITIES = [
    "Harvard University",
    "Yale University", 
    "Columbia University",
    "University of Pennsylvania",
    "Princeton University",
    "New York University",
    "Boston University",
    "Brown University",
    "Cornell University",
    "Dartmouth College",
    "Massachusetts Institute of Technology",
    "Tufts University",
    "Boston College",
    "Northeastern University",
    "University of Connecticut",
]

SOUTHEAST_UNIVERSITIES = [
    "Emory University",
    "Vanderbilt University",
    "Georgetown University", 
    "University of North Carolina at Chapel Hill",
    "Duke University",
    "University of Virginia",
    "Florida State University",
    "University of Florida",
    "Georgia Institute of Technology",
    "University of Georgia",
    "Wake Forest University",
    "University of Miami",
    "Tulane University",
    "Rice University",
]

MIDWEST_UNIVERSITIES = [
    "University of Chicago",
    "Northwestern University",
    "University of Michigan, Ann Arbor",
    "University of Wisconsin-Madison",
    "University of Minnesota, Twin Cities",
    "Ohio State University",
    "University of Illinois at Urbana-Champaign",
    "Penn State University",
    "Washington University in St. Louis",
    "University of Iowa",
    "Indiana University",
    "Purdue University",
    "University of Notre Dame",
    "Case Western Reserve University",
]

SOUTHWEST_UNIVERSITIES = [
    "University of Texas at Austin",
    "Arizona State University",
    "University of Arizona",
    "Texas A&M University",
    "University of Oklahoma",
    "University of New Mexico",
    "Texas Tech University",
    "University of Houston",
    "Southern Methodist University",
    "Baylor University",
]

WEST_UNIVERSITIES = [
    "Stanford University",
    "University of California, Los Angeles", 
    "University of California, Berkeley",
    "University of Washington",
    "University of California, San Diego",
    "University of California, San Francisco",
    "University of California, Irvine",
    "University of California, Davis",
    "Carnegie Mellon University",
    "University of Southern California",
    "University of California, Santa Barbara",
    "University of Oregon",
    "Colorado University Boulder",
    "University of Utah",
    "California Institute of Technology",
]

# Curated list of 50+ universities meeting the criteria
CURATED_UNIVERSITIES = [
    # Tier 1: Top Ivy League + Elite Private (Major Cities)
    "Harvard University",
    "Stanford University", 
    "Yale University",
    "Columbia University",
    "University of Pennsylvania",
    "Princeton University",
    "University of Chicago",
    "Northwestern University",
    "New York University",
    "Boston University",
    
    # Tier 2: Top Public Universities (Major Cities)
    "University of California, Los Angeles",
    "University of California, Berkeley", 
    "University of Michigan, Ann Arbor",
    "University of Washington",
    "University of California, San Diego",
    "University of Texas at Austin",
    "University of California, San Francisco",
    "University of Wisconsin-Madison",
    "University of Minnesota, Twin Cities",
    "Ohio State University",
    "University of Illinois at Urbana-Champaign",
    "Penn State University",
    "University of North Carolina at Chapel Hill",
    "University of California, Irvine",
    "University of California, Davis",
    
    # Tier 3: Psychology/Sociology Powerhouses
    "Carnegie Mellon University",
    "Emory University",
    "Vanderbilt University", 
    "Washington University in St. Louis",
    "University of Southern California",
    "Georgetown University",
    "Tufts University",
    "Northeastern University",
    "George Washington University",
    "American University",
    "University of Pittsburgh",
    "University of Rochester",
    "Case Western Reserve University",
    "Rutgers University",
    "University of Maryland, College Park",
    
    # Tier 4: Strong Regional Universities (Major Cities)
    "Arizona State University",
    "University of Arizona",
    "University of Colorado Boulder",
    "University of Denver",
    "Florida International University", 
    "University of Florida",
    "Florida State University",
    "Georgia Institute of Technology",
    "University of Georgia",
    "University of Hawaii at Manoa",
    "University of Illinois at Chicago",
    "Indiana University Bloomington",
    "University of Iowa",
    "University of Kansas",
    "Louisiana State University",
    "Tulane University",
    "University of Massachusetts Amherst",
    "Michigan State University",
    "University of Missouri",
    "University of Nebraska-Lincoln",
    "University of Nevada, Las Vegas",
    "University of New Mexico",
    "Oregon State University",
    "University of Oregon",
    "Temple University",
    "University of Tennessee, Knoxville",
    "Rice University",
    "University of Utah",
    "Virginia Tech",
    "University of Virginia",
    "Seattle University"
]

def get_northeast_universities() -> List[str]:
    """Get Northeast region universities."""
    return NORTHEAST_UNIVERSITIES

def get_southeast_universities() -> List[str]:
    """Get Southeast region universities."""
    return SOUTHEAST_UNIVERSITIES

def get_midwest_universities() -> List[str]:
    """Get Midwest region universities.""" 
    return MIDWEST_UNIVERSITIES

def get_southwest_universities() -> List[str]:
    """Get Southwest region universities."""
    return SOUTHWEST_UNIVERSITIES

def get_west_universities() -> List[str]:
    """Get West Coast universities."""
    return WEST_UNIVERSITIES

def get_universities_by_region() -> Dict[str, List[str]]:
    """Group universities by major US regions for easier selection."""
    return {
        "Northeast": [
            "Harvard University",
            "Yale University", 
            "Columbia University",
            "University of Pennsylvania",
            "Princeton University",
            "New York University",
            "Boston University",
            "Tufts University",
            "Northeastern University",
            "Georgetown University",
            "George Washington University",
            "American University",
            "University of Rochester",
            "Rutgers University",
            "Temple University"
        ],
        "West Coast": [
            "Stanford University",
            "University of California, Los Angeles",
            "University of California, Berkeley",
            "University of Washington", 
            "University of California, San Diego",
            "University of California, San Francisco",
            "University of California, Irvine",
            "University of California, Davis",
            "University of Southern California",
            "Arizona State University",
            "University of Arizona",
            "University of Hawaii at Manoa",
            "Oregon State University",
            "University of Oregon",
            "Seattle University"
        ],
        "Midwest": [
            "University of Chicago",
            "Northwestern University",
            "University of Michigan, Ann Arbor",
            "University of Wisconsin-Madison",
            "University of Minnesota, Twin Cities",
            "Ohio State University",
            "University of Illinois at Urbana-Champaign",
            "Penn State University",
            "Carnegie Mellon University",
            "Washington University in St. Louis",
            "University of Pittsburgh",
            "Case Western Reserve University",
            "University of Illinois at Chicago",
            "Indiana University Bloomington",
            "University of Iowa",
            "University of Kansas",
            "Michigan State University",
            "University of Missouri",
            "University of Nebraska-Lincoln"
        ],
        "South": [
            "University of Texas at Austin",
            "Emory University",
            "Vanderbilt University",
            "University of North Carolina at Chapel Hill",
            "University of Maryland, College Park",
            "Florida International University",
            "University of Florida",
            "Florida State University", 
            "Georgia Institute of Technology",
            "University of Georgia",
            "Louisiana State University",
            "Tulane University",
            "University of Tennessee, Knoxville",
            "Rice University",
            "Virginia Tech",
            "University of Virginia"
        ],
        "Mountain/Southwest": [
            "University of Colorado Boulder",
            "University of Denver",
            "University of Nevada, Las Vegas",
            "University of New Mexico",
            "University of Utah"
        ]
    }

def get_psychology_sociology_top_programs() -> List[str]:
    """Universities with top-ranked psychology/sociology programs."""
    return [
        # Psychology Rankings Leaders
        "Harvard University",
        "Stanford University",
        "University of California, Los Angeles",
        "Yale University", 
        "University of Michigan, Ann Arbor",
        "University of California, Berkeley",
        "Princeton University",
        "University of Pennsylvania",
        "Columbia University",
        "University of Wisconsin-Madison",
        "University of Minnesota, Twin Cities",
        "Northwestern University",
        "University of Washington",
        "University of Chicago",
        "Carnegie Mellon University",
        "New York University",
        "University of California, San Diego",
        "Ohio State University",
        "University of Illinois at Urbana-Champaign",
        "University of Texas at Austin",
        
        # Sociology Rankings Leaders  
        "University of California, Berkeley",
        "Harvard University",
        "Princeton University",
        "Stanford University",
        "University of Michigan, Ann Arbor",
        "University of Wisconsin-Madison",
        "Columbia University",
        "University of Chicago",
        "Northwestern University",
        "University of California, Los Angeles",
        "University of North Carolina at Chapel Hill",
        "Yale University",
        "University of Pennsylvania",
        "New York University",
        "University of Washington"
    ]

def get_international_friendly_universities() -> List[str]:
    """Universities known for strong international student support."""
    return [
        "New York University",  # Largest international student body
        "University of Southern California",
        "Columbia University", 
        "Boston University",
        "Northeastern University",
        "University of California, Los Angeles",
        "Stanford University",
        "Harvard University",
        "University of Washington",
        "Arizona State University",  # Very international friendly
        "University of Illinois at Urbana-Champaign",
        "University of Michigan, Ann Arbor", 
        "Carnegie Mellon University",
        "University of Pennsylvania",
        "Northwestern University",
        "University of California, San Diego",
        "University of Texas at Austin",
        "George Washington University",
        "Georgetown University",
        "University of Minnesota, Twin Cities"
    ]