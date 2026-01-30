# PowerCV Copilot Instructions

**For**: AI agents helping develop PowerCV (CV optimization platform)  
**Updated**: 2026-01-20 | **Version**: 3.2

---

## System Overview

PowerCV is an **AI-powered CV optimizer** that tailors resumes to job descriptions, generates cover letters, and exports PDFs. It combines FastAPI backend (Python 3.12), React 19 frontend (TypeScript), MongoDB, Redis, and AI providers (Cerebras/OpenAI/Deepseek).

**Key Objectives**: Parse CVs → Analyze job fit (ATS scoring) → Optimize content → Generate outputs (PDF/JSON/HTML)  
**Tech Stack**: FastAPI + Motor (async MongoDB) + Redis + React/Vite/Tailwind + Docker + n8n workflows

---

## Essential Architecture

### Backend: Workflow-Centric Design
**File**: `app/services/workflow_orchestrator.py` (619 lines)  
**Core Pattern**:
```python
# Three-stage pipeline (analyze → optimize → generate)
orchestrator = CVWorkflowOrchestrator()
result = orchestrator.optimize_cv_for_job(
    cv_text=request.cv_text,           # Candidate resume
    jd_text=request.jd_text,           # Job description
    generate_cover_letter=True         # Optional cover letter
)
# Returns: {analysis, optimized_cv, ats_score, cover_letter, matching_skills, missing_skills}
```

**Service Layer** (`app/services/`):
- `cv_analyzer.py` - ATS scoring, keyword extraction, gap analysis
- `cv_optimizer.py` - Comprehensive section rewriting (one-shot via Cerebras)
- `cover_letter_gen.py` - Professional letter generation with tone control
- `workflow_orchestrator.py` - Orchestrates the three services + handles retries/rate limits
- `cerebras_client.py` - Wrapper for Cerebras API (primary AI provider)

**API Routes** (`app/api/routers/`):
- `/api/v2/optimize` - Full workflow (POST, return resume_id for PDF generation)
- `/api/v2/analyze` - ATS scoring only
- `/api/v2/cover-letter` - Cover letter generation
- `/api/optimize-resume` - Legacy endpoint (maps to v2)
- Resume CRUD in `resume/router.py` (download PDFs, list versions)

**Database** (`app/database/`):
- MongoDB models in `models/resume.py` - Stores CV history, ATS scores, optimized content
- `connector.py` - Singleton connection manager (Motor async client)
- Repositories pattern: `ResumeRepository`, `CoverLetterRepository`

### Frontend: Component-Driven State
**File**: `frontend/src/` (React 19 + TypeScript strict + Tailwind)

**Key Components**:
- `components/optimization/` - TailorForm, ATS analyzer UI, resume previewer
- `components/dashboard/` - Resume history, version comparison
- `stores/` - Zustand state (CV uploads, optimization results)
- `api/` - Axios client with interceptors (base URL: `/api/v2/`)

**React Query Integration** (TanStack):
```typescript
const mutation = useMutation({
  mutationFn: (data) => api.post('/api/v2/optimize', data),
  onSuccess: (result) => store.setResumes([...store.resumes, result])
});
```

### Orchestration: Docker Compose
**Services** (`docker-compose.yml`):
- `powercv` - FastAPI app (port 8081 → 8080)
- `mongodb` - Data store (port 27018 → 27017)
- `redis` - Caching & rate limiting (port 6379)
- `n8n` - Workflow automation UI (port 5678)

**Health Checks**: All containers include healthchecks; PowerCV depends on MongoDB + Redis  
**Volumes**: `./data` (persistence), `./n8n_workflows` (automation), `./n8n_data` (n8n state)

---

## Critical Patterns

### 1. AI Response Parsing (Common Gotcha)
**Problem**: Cerebras/OpenAI sometimes return truncated JSON or text-wrapped responses.

**Solution** (`app/utils/shared_utils.py`):
```python
# Repair truncated JSON
def safe_json_parse(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt repair
        repaired = JSONParser.repair_json(text)  # Close braces/brackets
        return json.loads(repaired)

# For cover letters: parse text format with markers
def _parse_cover_letter_response(text):
    marker = "=== FINAL COVER LETTER ==="
    if marker in text:
        return text.split(marker)[-1].strip()
    # Fallback to raw text
    return text
```

### 2. Rate Limiting & Caching
**Pattern**: Cache analysis results by CV+JD hash to avoid redundant API calls.
```python
# In workflow_orchestrator.py
cache_key = f"analysis:{hash(cv_text)}:{hash(jd_text)}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)
# Run analysis, then cache for 3600s
result = analyzer.analyze(cv_text, jd_text)
redis.setex(cache_key, 3600, json.dumps(result))
```

### 3. Email Field Validation
**Context**: Optimization saves resumes to MongoDB; empty emails cause validation errors.

**Fix** (`app/database/models/resume.py`):
```python
email: Optional[str] = None  # Make optional
```

**In optimizer** (`app/api/routers/comprehensive_optimizer.py`):
```python
# Clean email before saving
if not user_info.email or user_info.email.strip() == "":
    user_info.email = None
```

### 4. PDF Generation Filenames
**New Format** (2026-01-19): `{type}_{initial}{surname}_{company}_{role}_{date}.pdf`

**Implementation** (`app/services/export.py`):
```python
def generate_pdf_filename(resume_data, template_type="resume"):
    name = resume_data.get("name", "candidate")
    company = resume_data.get("target_company", "target")
    role = resume_data.get("target_role", "role")
    # Sanitize for filesystem
    return f"{template_type}_{name_to_initials(name)}_{company}_{role}_{date.today()}.pdf"
```

### 5. Async-First Backend
**Rule**: All endpoints async, use Motor (async MongoDB driver), no blocking I/O.

```python
# Correct:
async def optimize_cv_v2(request: OptimizationRequest):
    result = await orchestrator.optimize_cv_for_job(...)  # Await
    resume_id = await repo.create_resume(resume_data)    # Await
    return result

# Wrong: Never block
def sync_optimize():  # ❌ Blocks event loop
    result = orchestrator.optimize_cv_for_job(...)
```

---

## Developer Workflows

### Quick Start (Local Dev)
```bash
# 1. Backend
cd /home/illnar/Projects/PowerCV
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:.
python -m uvicorn app.main:app --reload --port 8080

# 2. Frontend (new terminal)
cd frontend
npm install && npm run dev  # Runs on http://localhost:5173

# 3. MongoDB (if local)
docker run -d --name mongodb -p 27017:27017 mongo:latest

# 4. Redis (if local)
docker run -d --name redis -p 6379:6379 redis:latest
```

### Testing
```bash
# Backend: pytest (goal: 90%+ coverage)
pytest tests/ -v --cov=app --cov-fail-under=90

# Frontend: Vitest
cd frontend && npm run test:coverage

# Integration: Start containers
docker-compose up -d
curl http://localhost:8080/health  # Should return {status: "healthy"}
```

### Common Commands
```bash
# View service logs
docker-compose logs -f powercv

# Reset database
docker-compose exec mongodb mongosh --eval "db.resumes.deleteMany({})"

# Check AI provider connectivity
python -c "from app.services.cerebras_client import CerebrasClient; print(CerebrasClient().test_connection())"

# Format code
ruff format . && ruff check . --fix

# Type checking
mypy . --strict
```

---

## Project-Specific Conventions

### File Naming
- **Services**: Verb + noun (e.g., `cv_analyzer.py`, `cover_letter_gen.py`)
- **Routers**: Plural nouns (e.g., `resume/`, `cover_letter.py`)
- **Models**: Entity names (e.g., `resume.py` → `Resume` class)

### Error Handling
**Use `ErrorHandler` class** (`app/utils/error_handler.py`):
```python
from app.utils.error_handler import ErrorHandler, ErrorContext

# For AI provider errors:
try:
    result = ai_client.call()
except Exception as e:
    raise ErrorHandler.handle_ai_api_error(
        e,
        provider="cerebras",
        operation="optimization",
        context={"cv_length": len(cv_text)}
    )

# For context tracking:
with ErrorContext("operation_name", {"key": "value"}):
    # Code here; errors logged with context
    pass
```

### Logging
**Use**: `app.config.logging_config.logger` (structured JSON logging)
```python
from app.config.logging_config import logger

logger.info("Starting optimization", extra={"cv_length": 1500, "jd_length": 800})
logger.warning("Rate limit approaching", extra={"remaining": 5})
logger.error("AI API failed", exc_info=True)  # Logs traceback
```

### Pydantic Models
**Location**: `app/database/models/` for database, inline for request/response

**Pattern** (Python 3.12):
```python
from pydantic import BaseModel, Field, field_validator

class CVTailorRequest(BaseModel):
    cv_text: str = Field(..., min_length=100, max_length=25000)
    jd_text: str = Field(..., min_length=50, max_length=15000)
    
    @field_validator("cv_text")
    @classmethod
    def validate_cv_not_just_spaces(cls, v):
        if not v.strip():
            raise ValueError("CV cannot be empty")
        return v
```

### Frontend TypeScript
**Rules**: Strict mode ON, no `any` type
```typescript
// frontend/tsconfig.json: strict: true

// Correct:
interface UserData { name: string; email?: string; }
const user: UserData = { name: "John" };

// Wrong:
const user: any = getData();  // ❌ Breaks type safety
```

---

## Critical Files & Their Purposes

| File | Purpose | When to Edit |
|------|---------|--------------|
| `app/main.py` | FastAPI app setup, routes, lifespan | Adding new API endpoints |
| `app/services/workflow_orchestrator.py` | Three-stage CV pipeline | Changing optimization logic |
| `app/api/routers/resume/router.py` | Resume CRUD + PDF download | Modifying resume endpoints |
| `app/database/connector.py` | MongoDB connection pool | Database config changes |
| `docker-compose.yml` | Container orchestration | Service scaling, env vars |
| `frontend/src/App.tsx` | React root, routing | UI structure changes |
| `mkdocs.yml` | Documentation nav | Adding new docs |
| `.github/workflows/` | CI/CD pipeline | Test/deploy automation |
| `data/templates/*.typ` | Typst PDF templates | Resume layout changes |

---

## Pre-Implementation Checklist

**Before you code**, verify:
```bash
# 1. Environment & dependencies
ls .env && echo "✓ .env exists" || echo "✗ Copy env-template.txt → .env"
python -c "import fastapi; import motor; print('✓ Dependencies OK')"

# 2. Services running (for integration)
docker-compose ps | grep -E "powercv|mongodb|redis"

# 3. Existing tests pass
pytest tests/ --co -q | head -5 && echo "✓ Tests found"

# 4. Code style baseline
ruff check app/ | head -3 || echo "✓ No ruff errors"
```

---

## Key Metrics & Targets

- **API Response Time**: CV optimization p95 < 10 seconds (cached < 2s)
- **ATS Score Range**: 60–95 (realistic, not all 99s)
- **Keyword Match**: >70% of job requirements appear in optimized CV
- **PDF Generation**: <3 seconds for Typst compilation
- **Test Coverage**: ≥90% on `app/` (exclude migrations)
- **Docker Image**: <500MB
- **Frontend Bundle**: <200KB gzipped

---

## Common Pitfalls & Solutions

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `JSONDecodeError` in optimization | Truncated AI response | Use `safe_json_parse()` with repair logic |
| 500 error on resume save | Invalid email field | Make `email: Optional[str] = None` |
| Slow API response | No Redis caching | Add `cache_key = hash(cv+jd); redis.get()` |
| Frontend auth fails | CORS not configured | Check `CORSMiddleware` in `app/main.py` |
| PDF filenames are placeholders | Missing export.py function | Use `generate_pdf_filename()` helper |
| n8n workflows unreachable | Webhook URL mismatch | Set `N8N_WEBHOOK_URL=http://n8n:5678` in `.env` |

---

## Deployment Notes

- **Local**: `python -m uvicorn app.main:app --reload` + `npm run dev`
- **Docker**: `docker-compose up -d` (mounts volumes for persistence)
- **CI/CD**: GitHub Actions (`.github/workflows/`) runs pytest + docker build
- **Scaling**: Redis for distributed caching, MongoDB connection pooling via Motor

---

## Useful References

- **Cerebras API**: https://docs.cerebras.ai/ (models: gpt-oss-120b recommended)
- **FastAPI Docs**: http://localhost:8080/docs (auto-generated from route docstrings)
- **MongoDB Motor**: Motor async driver for PyMongo
- **React Query**: TanStack documentation for data fetching patterns
- **Tailwind**: https://tailwindcss.com/ (use only utility classes, no custom CSS in components)

---

## What SUCCESS Looks Like

✅ New feature passes pytest (90%+ coverage)  
✅ Docker builds <500MB  
✅ API response <10s for full optimization  
✅ No hardcoded secrets in code (use `.env`)  
✅ CHANGELOG.md updated with impact metrics  
✅ Frontend TypeScript strict mode passes  
✅ All existing tests still pass
