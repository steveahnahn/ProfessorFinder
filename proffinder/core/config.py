import os
from dotenv import load_dotenv

load_dotenv()

OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "proffinder@example.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
CONCURRENCY_PER_HOST = int(os.getenv("CONCURRENCY_PER_HOST", "2"))
DEFAULT_YEARS_WINDOW = int(os.getenv("DEFAULT_YEARS_WINDOW", "5"))

WEIGHT_CONCEPT = float(os.getenv("WEIGHT_CONCEPT", "0.5"))
WEIGHT_WORKS = float(os.getenv("WEIGHT_WORKS", "0.3"))
WEIGHT_GRANT = float(os.getenv("WEIGHT_GRANT", "0.2"))

CACHE_TTL_HOURS = 24

API_ENDPOINTS = {
    "ror": "https://api.ror.org/organizations",
    "openalex": "https://api.openalex.org",
    "orcid": "https://pub.orcid.org/v3.0",
    "ncbi_esearch": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
    "ncbi_efetch": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
    "nih_reporter": "https://api.reporter.nih.gov/v2",
    "nsf_awards": "https://api.nsf.gov/services/v1/awards.json"
}

RECRUITING_PHRASES = [
    "join our lab", "we are recruiting", "prospective students", "open positions",
    "phd applicants", "ra wanted", "graduate students", "postdoc", "research assistant",
    "now hiring", "positions available", "accepting applications", "looking for students"
]

MAX_RECRUITING_SNIPPET = 240

USER_AGENT = "ProfFinder/1.0 (Academic Research Tool)"