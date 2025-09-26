# Graduate Admissions API

FastAPI backend service for the graduate admissions requirements platform.

## Features

- **Program Search**: Search and filter graduate programs with full-text search
- **Program Details**: Get comprehensive admission requirements for specific programs
- **Fit Analysis**: Calculate student-program fit scores based on academic profile
- **Review System**: Human review workflow for requirement validation
- **High Performance**: Async PostgreSQL queries with connection pooling
- **Rate Limiting**: Built-in request throttling
- **Health Monitoring**: Health check and statistics endpoints

## Quick Start

1. **Install dependencies**:
   ```bash
   cd apps/api
   uv pip install -e .
   ```

2. **Setup environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Run the server**:
   ```bash
   uvicorn main:app --reload
   ```

4. **View API docs**: http://localhost:8000/docs

## API Endpoints

### Public Endpoints

- `GET /api/v1/programs/search` - Search programs with filtering
- `GET /api/v1/programs/{program_id}` - Get program details
- `POST /api/v1/programs/fit-check` - Calculate program fit scores
- `GET /api/v1/programs/degrees/options` - Available degree types
- `GET /api/v1/programs/countries/options` - Available countries
- `GET /api/v1/programs/stats/summary` - Database statistics

### Review Endpoints (Internal)

- `GET /api/v1/review/pending` - Pending requirement sets for review
- `GET /api/v1/review/{id}/details` - Detailed requirement set information
- `POST /api/v1/review/{id}/approve` - Approve requirement set
- `POST /api/v1/review/{id}/reject` - Reject requirement set
- `POST /api/v1/review/batch-approve` - Batch approve high-confidence sets
- `GET /api/v1/review/stats` - Review workflow statistics

## Configuration

Key environment variables:

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
DATABASE_URL=postgresql://postgres:password@host:port/db

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# LLM
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

## Architecture

```
apps/api/
├── main.py              # FastAPI app and middleware
├── config.py           # Settings management
├── database.py         # Database connections
├── models/
│   └── responses.py    # API response models
├── services/
│   ├── program_service.py  # Program operations
│   └── review_service.py   # Review operations
└── routers/
    ├── programs.py     # Program endpoints
    └── review.py       # Review endpoints
```

## Development

Run with hot reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:
```bash
pytest
```

## Deployment

The API is designed for deployment on:
- Railway/Render (with Supabase database)
- Docker containers
- Serverless platforms (with connection pooling)

Example Docker deployment:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```