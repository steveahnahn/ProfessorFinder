# 🔍 ProfFinder

**Faculty Discovery & Research Matching Tool**

ProfFinder is a comprehensive Streamlit application that discovers researchers at specified US universities whose recent work matches user-provided keywords. It ranks authors using transparent scoring and exports results with complete provenance tracking.

## 🌟 Features

### Core Capabilities
- **Institution Resolution**: Automatically resolves university names to ROR IDs
- **Keyword Expansion**: Enhances search terms using OpenAlex Concepts/Topics and PubMed/MeSH
- **Multi-Source Discovery**: Finds researchers through OpenAlex author profiles and publication affiliations
- **Profile Enrichment**: Adds employment details and homepage URLs from ORCID
- **Grant Integration**: Searches NIH RePORTER and NSF Awards for active funding
- **Recruitment Detection**: Scans faculty homepages for recruiting signals
- **Transparent Scoring**: Provides explainable scores based on topic match, recent work, and grants
- **Full Provenance**: Tracks all data sources and evidence URLs for complete transparency

### Technical Features
- **Async Processing**: Concurrent API calls with rate limiting and exponential backoff
- **Smart Caching**: 24-hour disk cache to avoid redundant API requests
- **Resilient**: Handles API failures gracefully with partial results
- **Scalable**: Supports batch processing of multiple institutions and researchers

## 🚀 Quick Start

### Local Development

1. **Clone and setup**:
```bash
git clone <repository-url>
cd proffinder
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (copy and edit):
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run the application**:
```bash
streamlit run app.py
```

5. **Access the web interface**:
Open http://localhost:8501 in your browser

### Docker

1. **Build the image**:
```bash
docker build -t proffinder .
```

2. **Run the container**:
```bash
docker run -p 8080:8080 \
  -e OPENALEX_MAILTO=your-email@example.com \
  -e NCBI_API_KEY=your_ncbi_key \
  proffinder
```

3. **Access the application**:
Open http://localhost:8080

### Google Cloud Run Deployment

1. **Set up Google Cloud**:
```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

2. **Store API keys as secrets** (recommended):
```bash
# Store OpenAlex email
echo "your-email@example.com" | gcloud secrets create openalex-mailto --data-file=-

# Store NCBI API key (optional but recommended)
echo "your_ncbi_api_key" | gcloud secrets create ncbi-api-key --data-file=-
```

3. **Deploy using Cloud Build**:
```bash
gcloud builds submit --config cloudbuild.yaml
```

4. **Or deploy manually**:
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/proffinder

# Deploy to Cloud Run (Seoul region)
gcloud run deploy proffinder \
  --image gcr.io/$PROJECT_ID/proffinder \
  --region=asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars OPENALEX_MAILTO=your-email@example.com,NCBI_API_KEY=your_ncbi_key \
  --cpu=2 \
  --memory=2Gi \
  --timeout=600s \
  --max-instances=10
```

## 📊 Usage

### Basic Workflow

1. **Enter Universities**: Add institution names (e.g., "UCLA", "Stanford University")
2. **Specify Keywords**: Enter research terms (e.g., "psychology", "machine learning")  
3. **Set Time Window**: Choose how many years back to search for publications (default: 5)
4. **Run Search**: Click "Run Search" to begin processing
5. **Review Results**: Browse the ranked table of matching researchers
6. **Export Data**: Download complete results as CSV with full provenance

### Example Search

**Universities**:
```
UCLA
Stanford University  
University of Washington
```

**Keywords**:
```
psychology
suicide prevention
social networks
machine learning
```

This will find psychologists and related researchers at these three universities who work on suicide prevention, social networks, or machine learning, ranked by relevance.

### Understanding Results

#### Scoring Components
- **Concept Score** (50% weight): Overlap between researcher's topics and your keywords
- **Recent Works Score** (30% weight): Relevance and recency of matching publications  
- **Grant Score** (20% weight): Active NIH/NSF funding in relevant areas
- **Final Score**: Weighted combination of the three components

#### CSV Output Columns
The exported CSV includes 27 columns with complete provenance:

**Basic Info**: `institution_name`, `institution_ror`, `author_name`, `openalex_id`, `orcid_id`

**Employment**: `current_title`, `department`, `homepage_url`

**Research Profile**: `primary_topics_or_concepts`, `matched_keywords`, `recent_pubs_count`, `example_pub_titles`

**Funding**: `active_grants_count`, `funders`, `grant_ids`, `grant_urls`

**Recruiting**: `is_recruiting`, `recruiting_snippet`, `recruiting_url`  

**Scores**: `concept_score`, `recent_works_score`, `grant_score`, `final_score`

**Provenance**: `evidence_urls`, `last_seen_utc`, `sources_used`

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENALEX_MAILTO` | Email for OpenAlex polite pool | `proffinder@example.com` |
| `NCBI_API_KEY` | NCBI API key (optional but recommended) | `""` |
| `REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `10` |
| `CONCURRENCY_PER_HOST` | Max concurrent requests per host | `5` |
| `DEFAULT_YEARS_WINDOW` | Default years for recent publications | `5` |
| `WEIGHT_CONCEPT` | Weight for concept matching score | `0.5` |
| `WEIGHT_WORKS` | Weight for recent works score | `0.3` |  
| `WEIGHT_GRANT` | Weight for grants score | `0.2` |

### API Requirements

#### Required APIs
- **OpenAlex**: No key required, but email recommended for polite pool
- **ROR API**: No key required  

#### Optional APIs (enhance results significantly)
- **NCBI/PubMed**: API key recommended for higher rate limits
- **ORCID**: No key required (public API)
- **NIH RePORTER**: No key required
- **NSF Awards**: No key required

#### Rate Limits & Caching
- All APIs are automatically rate-limited and cached for 24 hours
- Exponential backoff with jitter handles temporary failures
- Partial results returned if some APIs fail

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python tests/run_tests.py

# Run specific test file
python -m pytest tests/test_scoring.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage
- **Scoring Logic**: Validates score calculations and component weighting
- **Keyword Expansion**: Tests OpenAlex/MeSH integration (may require API keys)
- **CSV Export**: Verifies column order, data format, and provenance tracking

## 🏗️ Architecture

### Project Structure
```
proffinder/
├── app.py                      # Main Streamlit application
├── core/
│   ├── config.py              # Configuration and constants  
│   ├── models.py              # Pydantic data models
│   ├── keywords.py            # Keyword expansion logic
│   ├── scoring.py             # Transparent scoring system
│   ├── csvio.py               # CSV export with provenance
│   └── cache.py               # Disk caching utilities
├── sources/  
│   ├── ror.py                 # Institution name → ROR ID resolution
│   ├── openalex.py            # Author discovery & publication matching
│   ├── orcid.py               # Profile enrichment & homepage detection  
│   ├── nih.py                 # NIH RePORTER grant search
│   ├── nsf.py                 # NSF Awards grant search
│   └── recruit.py             # Homepage recruitment signal detection
├── util/
│   ├── http.py                # Async HTTP client with rate limiting
│   └── text.py                # Text processing utilities
├── tests/                     # Unit tests
├── Dockerfile                 # Container definition
└── deploy.yaml                # Cloud Run configuration
```

### Data Flow
1. **Input Processing**: Parse institutions and keywords from user
2. **Institution Resolution**: Convert names to ROR IDs via ROR API  
3. **Keyword Expansion**: Enhance terms using OpenAlex + MeSH APIs
4. **Author Discovery**: Find researchers via OpenAlex (authors + works)
5. **Profile Enrichment**: Add ORCID employment/homepage data
6. **Grant Discovery**: Search NIH RePORTER + NSF Awards concurrently
7. **Recruitment Detection**: Scan homepages for recruiting signals
8. **Scoring & Ranking**: Calculate transparent scores and rank results
9. **Export Generation**: Create CSV with complete provenance

## 🔒 Privacy & Ethics

### Responsible Use
- Only accesses public APIs and data sources
- Respects robots.txt for homepage scanning (single page only)
- Includes proper attribution and provenance for all data
- Does not scrape Google Scholar or bulk-harvest emails
- Rate-limited to be respectful of API providers

### Data Sources
- **OpenAlex**: Open scholarly metadata
- **ORCID**: Public researcher profiles only  
- **NIH RePORTER**: Public grant database
- **NSF Awards**: Public funding records
- **ROR**: Open registry of research organizations
- **Faculty Homepages**: Public websites only, single page fetch

## 🚨 Limitations

### Data Quality Issues
- **US-focused**: Optimized for US universities and funding agencies
- **English-only**: Best results with English-language keywords
- **Department information** often unavailable from OpenAlex API - many results show empty departments
- **Publication counts capped at 50** per author to prevent API timeouts (explains why many authors show exactly 50 recent publications)
- **API Dependencies**: Results quality depends on external API availability  
- **Rate Limits**: Large searches may take several minutes

### Grant Data Limitations  
- **Grant information is unreliable and incomplete**:
  - Many grants are private or not publicly reported
  - Industry/private foundation grants are largely unsourceable
  - Grant databases (NIH, NSF) have significant coverage gaps
  - Grant timing often lags actual funding by months/years
- **Grant data excluded from ranking** due to these reliability issues
- Grant information shown for reference only, should not be used as primary selection criteria

### Technical Limitations
- **Homepage Detection**: Only checks single homepage URL if available
- **Author disambiguation**: Challenging - we do our best with name matching

## 🤝 Contributing

### Development Setup
```bash
# Clone and setup development environment
git clone <repository-url>
cd proffinder
pip install -r requirements.txt
cp .env.example .env

# Run tests
python tests/run_tests.py

# Start development server
streamlit run app.py
```

### Adding New Data Sources
1. Create new module in `sources/` directory
2. Implement async functions following existing patterns  
3. Add rate limiting and error handling
4. Update models and scoring as needed
5. Add tests and update documentation

## 📄 License

This project is intended for academic and research purposes. Please ensure compliance with all API terms of service and respect rate limits.

## 🔗 Links

- **OpenAlex**: https://openalex.org/
- **ROR**: https://ror.org/  
- **ORCID**: https://orcid.org/
- **NIH RePORTER**: https://reporter.nih.gov/
- **NSF Awards**: https://nsf.gov/awardsearch/
- **Streamlit**: https://streamlit.io/
- **Google Cloud Run**: https://cloud.google.com/run

---

**Built with ❤️ for the research community**