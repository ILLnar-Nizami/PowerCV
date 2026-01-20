---
trigger: always_on
---

# PowerCV Engineering Agent v3.2

**Updated**: 2026-01-20  
**For**: Elite AI agents handoff - CV optimization platform  
**Repo**: https://github.com/ILLnar-Nizami/PowerCV (dev@cf5d9a46)

## System Overview
**Purpose**: AI-powered resume optimizer that tailors CVs to job descriptions, generates cover letters, and exports PDFs with ATS compatibility scoring.

**Core Engine**: 
- Parse CV text → Analyze against job description → Generate optimized sections → Export PDF
- Primary AI: Cerebras API (gpt-oss-120b) with fallbacks to OpenAI/Deepseek
- Realistic ATS scores: 60-95 range (not inflated)

## Architecture (Actual Repo - v3.2)
- **Backend**: FastAPI async in app/api/routers/ (v2 endpoints), app/services/ (workflow orchestrator), Motor (MongoDB async driver), Redis caching
- **Frontend**: React 19 + TypeScript strict in frontend/src/, Vite bundler, Tailwind CSS, Zustand state, TanStack Query
- **Database**: MongoDB (port 27017) with models in app/database/models/, repositories pattern for data access
- **Cache/Queue**: Redis (port 6379) for rate limiting and response caching
- **Orchestration**: Docker Compose with 4 services (powercv, mongodb, redis, n8n), GitHub Actions CI/CD
- **PDF Generation**: Typst templating engine (data/templates/*.typ), dynamic filename generation
- **AI/ML**: Prompts in app/prompts/ (or loaded from services), cerebras_client wrapper, structured JSON responses
- **Testing**: pytest 90%+ coverage gate, Vitest for frontend, integration tests
- **Scripts**: run.sh (dev server), docker-compose.yml (production), scripts/ (utilities)
- **Docs**: mkdocs.yml with mkdocs-material, CHANGELOG.md (semantic versioning)

## Mission
Ship production features FAST. Every change MUST pass:
- ✅ pytest 90%+ coverage (or Δ% improvement)
- ✅ Docker build <500MB
- ✅ API response <10s for full optimization (cached <2s)
- ✅ CHANGELOG.md updated with impact metrics
- ✅ Frontend TypeScript strict mode passes
- ✅ All existing tests still pass (no regressions)

**PRESERVE ALWAYS**:
- `docker-compose.yml` volumes (./data, ./n8n_workflows)
- `/api/v2/` endpoints (v1 deprecated)
- MongoDB collections structure
- n8n workflow files
- Zustand store contracts

---

## Data Flow Architecture

### User Journey (High Level)
```
User Input (CV + JD)
    ↓
POST /api/v2/optimize
    ↓
CVWorkflowOrchestrator.optimize_cv_for_job()
    ├─ Step 1: Analyzer.analyze() → ATS score + keyword gaps
    ├─ Step 2: Optimizer.optimize_comprehensive() → Rewritten sections
    └─ Step 3: CoverLetterGen.generate() → Professional letter
    ↓
Save to MongoDB → resume_id
    ↓
GET /api/resume/{resume_id}/download
    ↓
TypstGenerator renders PDF
    ↓
User downloads with filename: cv_j.doe_google_engineer_20.01.26.pdf
```

### Critical Service Dependencies
```python
# app/services/workflow_orchestrator.py (619 lines - THE CORE)
class CVWorkflowOrchestrator:
    def __init__(self):
        self.analyzer = CVAnalyzer()        # Uses Cerebras API
        self.optimizer = CVOptimizer()      # Uses Cerebras API
        self.cover_letter_gen = CoverLetterGenerator()  # Uses AI provider
    
    def optimize_cv_for_job(self, cv_text, jd_text, generate_cover_letter=True):
        # Returns: {analysis, optimized_cv, ats_score, cover_letter, resume_id}
```

---

## Pre-Implementation Checklist (ALWAYS DO THIS FIRST)
```bash
./scripts/migration_status.sh              # DB state
grep "TODO" implementation_checklist.md    # Pending tasks
docker-compose ps                          # Service health
```

## Pre-Implementation Checklist (ALWAYS DO THIS FIRST)

```bash
# 1. Verify environment
ls .env || echo "ERROR: Copy env-template.txt → .env"
python -c "import fastapi; import motor; import redis" || echo "ERROR: Missing deps"

# 2. Check services
docker-compose ps | grep -E "powercv|mongodb|redis" || echo "WARN: Containers not running"

# 3. Verify test suite
pytest tests/ --collect-only -q | head -5

# 4. Check code style baseline
ruff check app/ | head -3 || echo "Ruff OK"

# 5. Read these files (agent context)
- app/main.py (FastAPI setup, routes, lifespan)
- app/services/workflow_orchestrator.py (core pipeline)
- app/database/models/resume.py (data schema)
- docker-compose.yml (service config)
- CHANGELOG.md (recent fixes + patterns)
```

**Decision Tree for New Work**:

| If you're... | Do this first |
|---|---|
| **Adding API endpoint** | Read app/main.py → check @app.post patterns → add to app/api/routers/ |
| **Modifying optimization** | Read workflow_orchestrator.py → understand 3-stage pipeline → edit analyzer/optimizer/generator |
| **Fixing data model** | Read app/database/models/resume.py → update Pydantic model → test with existing data |
| **Changing frontend UI** | Read frontend/src/App.tsx → check component structure → match Tailwind+TypeScript patterns |
| **Integrating AI provider** | Read app/services/cerebras_client.py → error handling → retry logic → rate limits |
| **Debugging 500 error** | Check app/utils/error_handler.py → logs in ErrorContext → test with pytest |

---

## Implementation Patterns
---

## Implementation Patterns

### 1. Backend API Endpoints (Python 3.12 + FastAPI)

**Rule**: All endpoints MUST be async, use Pydantic models, include docstrings for OpenAPI.

```python
# File: app/api/routers/example.py (GOOD PATTERN)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.utils.error_handler import ErrorHandler, ErrorContext
from app.config.logging_config import logger

router = APIRouter(prefix="/api/v2", tags=["Example"])

class ExampleRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)

@router.post("/example")
async def example_endpoint(request: ExampleRequest):
    """Process example data.
    
    Returns dict with status and result
    """
    try:
        with ErrorContext("example_operation", {"input_length": len(request.text)}):
            logger.info("Processing...")
            result = {"status": "success"}
            return result
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise ErrorHandler.handle_ai_api_error(e, provider="example", operation="process")
```

**Key Rules**:
- ✅ `async def` always | Pydantic v2 validation | Use ErrorContext for logging
- ✅ Return response_model for OpenAPI | 3+ line docstrings
- ❌ Never use blocking I/O | Never hardcode secrets

### 2. Database Operations (Motor + MongoDB)

```python
# File: app/database/repositories/resume_repository.py
class ResumeRepository:
    async def create_resume(self, resume: Resume) -> str:
        result = await self.db.resumes.insert_one(resume.model_dump())
        return str(result.inserted_id)
    
    async def get_resume(self, resume_id: str) -> Optional[Resume]:
        from bson.objectid import ObjectId
        doc = await self.db.resumes.find_one({"_id": ObjectId(resume_id)})
        return Resume(**doc) if doc else None
```

**Key Rules**:
- ✅ All DB calls async with `await` | Use ObjectId for IDs | Return Pydantic models
- ❌ Never use synchronous pymongo | Never expose DB errors to client

### 3. AI Provider Integration (Cerebras Primary)

```python
# File: app/services/cerebras_client.py
class CerebrasClient:
    async def chat_completion(self, system: str, user_message: str, temperature: float = 0.7):
        for attempt in range(3):
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": [...], "temperature": temperature}
                )
                return response.json()["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2**attempt)
                    continue
                raise
```

**Key Rules**:
- ✅ Exponential backoff for retries | Handle 429 specially | Log all failures
- ❌ Never expose API keys in logs | Never hardcode endpoints

### 4. JSON Response Parsing (CRITICAL BUG FIX FROM 2026-01-16)

```python
# File: app/utils/shared_utils.py
def safe_json_parse(text: str, default: dict = None) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Repair truncated JSON
        text = re.sub(r'```json\s*|\s*```', '', text)
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end+1]
        open_braces = text.count('{') - text.count('}')
        if open_braces > 0:
            text += '}' * open_braces
        return json.loads(text)
```

**Key Rules**:
- ✅ Always wrap AI responses in safe_json_parse | Provide sensible defaults
- ❌ Never let JSON errors crash endpoint | Never expose raw AI output

### 5. Frontend State & Queries (React 19 + TypeScript)

```typescript
// frontend/src/components/TailorForm.tsx
import { useMutation } from '@tanstack/react-query';
import { tailorCV } from '@/services/api';

export function TailorForm() {
  const mutation = useMutation({ 
    mutationFn: (data) => tailorCV(data),
    onSuccess: (result) => console.log('Success:', result),
    onError: (error) => console.error('Error:', error)
  });
  
  return (
    <form onSubmit={(e) => { 
      e.preventDefault(); 
      mutation.mutate({cv_text, jd_text}); 
    }}>
      <textarea 
        value={cv_text}
        onChange={(e) => setCVText(e.target.value)}
        className="w-full border rounded-lg p-3" 
        aria-describedby="cv-help"
      />
      <button 
        disabled={mutation.isPending} 
        className="btn-primary"
        type="submit"
      >
        {mutation.isPending ? 'Optimizing...' : 'Optimize'}
      </button>
    </form>
  );
}
```

**Key Rules**:
- ✅ React Query for server state | TypeScript strict mode | Tailwind utilities only
- ✅ ARIA labels for accessibility | Handle loading/error states
- ❌ No `any` type | No uncontrolled form inputs | Never expose API URLs

---

## Validation Pipeline (Required Before Commit)
## Validation Pipeline (Required Before Commit)

```bash
# 1. Run full test suite
pytest tests/ -v --cov=app --cov-fail-under=90

# 2. Type checking (strict mode)
mypy . --strict

# 3. Code formatting
ruff format . && ruff check . --fix

# 4. Integration test
docker-compose up -d
curl http://localhost:8080/health  # {status: "healthy"}

# 5. Documentation
mkdocs build --strict

# 6. Update changelog
# Edit CHANGELOG.md with: version, date, breaking changes, impact metrics
```

**Hard Gates** (NO EXCEPTIONS):
- ✅ pytest coverage ≥90% (or improvement Δ%)
- ✅ Docker image <500MB
- ✅ API response <10s (cached <2s)
- ✅ mypy passes strict mode
- ✅ CHANGELOG.md updated with impact metrics
- ✅ All existing tests still pass (no regressions)

---

## Testing Strategies

### Unit Tests
```python
# tests/test_cv_analyzer.py
import pytest
from app.services.cv_analyzer import CVAnalyzer

@pytest.fixture
def analyzer():
    return CVAnalyzer()

@pytest.mark.asyncio
async def test_analyze_valid_cv(analyzer):
    result = await analyzer.analyze(
        cv_text="John Doe\nSoftware Engineer",
        jd_text="We seek Python developer"
    )
    assert result["ats_score"] >= 60
    assert result["ats_score"] <= 95  # Realistic range
    assert "keyword_analysis" in result

def test_invalid_input_raises_error(analyzer):
    with pytest.raises(ValueError):
        analyzer.analyze("", "")  # Empty inputs
```

### Integration Tests
```python
# tests/test_api_optimize.py
@pytest.mark.asyncio
async def test_api_v2_optimize_full_flow(client):
    response = await client.post("/api/v2/optimize", json={
        "cv_text": "CV content here",
        "jd_text": "Job description here",
        "generate_cover_letter": True
    })
    assert response.status_code == 200
    data = response.json()
    assert "resume_id" in data
    assert "ats_score" in data
    assert "cover_letter" in data or data.get("cover_letter") is None
```

### Frontend Tests (Vitest + React Testing Library)
```typescript
// frontend/src/components/__tests__/TailorForm.test.tsx
import { render, screen, userEvent } from '@testing-library/react';
import { TailorForm } from '../TailorForm';

test('submits form with CV and JD text', async () => {
  const user = userEvent.setup();
  render(<TailorForm />);
  
  const cvInput = screen.getByPlaceholderText(/cv/i);
  const jdInput = screen.getByPlaceholderText(/job/i);
  const submitBtn = screen.getByRole('button', { name: /optimize/i });
  
  await user.type(cvInput, 'My CV');
  await user.type(jdInput, 'Job description');
  await user.click(submitBtn);
  
  expect(submitBtn).toHaveAttribute('disabled');
});
```

---

## Environment Setup

### Local Development
```bash
# 1. Clone and install
git clone https://github.com/ILLnar-Nizami/PowerCV.git
cd PowerCV
cp env-template.txt .env

# 2. Configure .env
CEREBRAS_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017/powercv
REDIS_URL=redis://localhost:6379
SECRET_KEY=dev-secret-key

# 3. Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:.
python -m uvicorn app.main:app --reload --port 8080

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev  # http://localhost:5173

# 5. Services (if not Docker)
docker run -d -p 27017:27017 mongo:latest
docker run -d -p 6379:6379 redis:latest
```

### Docker Deployment
```bash
# Build and run
docker-compose up -d

# Verify
curl http://localhost:8080/health

# View logs
docker-compose logs -f powercv

# Reset data
docker-compose exec mongodb mongosh --eval "db.resumes.deleteMany({})"
```

---

## Common Issues & Debugging
## Common Issues & Debugging

| Error | Cause | Fix |
|-------|-------|-----|
| `JSONDecodeError` in `/api/v2/optimize` | Truncated AI response | Wrap response in `safe_json_parse()` with repair logic |
| `500 error on POST /api/resume` | Invalid email field in model | Make `email: Optional[str] = None` in Pydantic model |
| API response >10s | No Redis caching | Add `cache_key = hash(cv+jd)` before expensive operations |
| Frontend won't load | CORS not configured | Check `CORSMiddleware` in app/main.py includes frontend port |
| PDF filenames are placeholders | `export.py` missing | Implement `generate_pdf_filename(resume_data)` function |
| `n8n workflows unreachable` | Webhook URL mismatch | Set `N8N_WEBHOOK_URL=http://n8n:5678` in `.env` |
| Tests fail with rate limit | AI provider overload | Implement retry logic with exponential backoff (see Cerebras client example) |
| Docker build >500MB | Large dependencies installed | Check requirements.txt for bloated packages (remove unused deps) |

### Debugging Commands
```bash
# Check logs with context
docker-compose logs -f powercv | grep ERROR

# Test AI provider connectivity
python -c "from app.services.cerebras_client import CerebrasClient; print(CerebrasClient().chat_completion('test', 'hi'))"

# Check MongoDB state
docker-compose exec mongodb mongosh --eval "db.resumes.countDocuments()"

# Validate environment
python -c "from app.config.settings import get_settings; s = get_settings(); print(f'AI={s.CEREBRAS_API_KEY[:10]}...', f'DB={s.MONGODB_URI}')"

# Run specific test with output
pytest tests/test_api_optimize.py::test_full_workflow -v -s
```

---

## Documentation Standards

### Inline Code Comments
```python
# ✅ GOOD: Explains WHY, not WHAT
# Rate limit retries with exponential backoff to handle provider spikes
for attempt in range(3):
    try:
        response = await client.post(...)
    except HTTPStatusError as e:
        if e.response.status_code == 429:
            await asyncio.sleep(2**attempt)
```

### Docstrings (Google Style)
```python
async def optimize_cv_for_job(self, cv_text: str, jd_text: str) -> Dict[str, Any]:
    """Optimize CV against job description.
    
    Three-stage pipeline: analyze → optimize → generate cover letter.
    
    Args:
        cv_text: Full resume text (100-25000 chars)
        jd_text: Job description text (50-15000 chars)
    
    Returns:
        dict: {analysis, optimized_cv, ats_score, cover_letter, resume_id}
    
    Raises:
        ValueError: If inputs too short
        HTTPError: If AI provider fails
    """
```

### CHANGELOG Format
```markdown
## [3.2.0] - 2026-01-20

### Added
- AI Response Parsing Robustness: Fixed JSONDecodeError on truncated responses
  Impact: 100% success rate (was 87%)

### Fixed
- Email Validation: Made optional in Resume model
  Fixes: 500 error on resume save
  Files: app/database/models/resume.py
  
- PDF Filenames: Professional naming scheme
  Format: cv_j.doe_google_engineer_20.01.26.pdf
```

---

## Constraints & Rules

❌ **NEVER** (Deal-breakers):
- Direct MongoDB writes without repository pattern
- Synchronous code in async context (blocking I/O)
- Hardcoded secrets | AI URLs in source code
- >500MB Docker image | <90% test coverage

✅ **ALWAYS** (Non-negotiable):
- Async/await for all I/O | Pydantic models for validation
- ErrorContext for logging | Redis caching for expensive ops
- 3+ line docstrings | TypeScript strict mode
- ARIA labels | Realistic ATS scores (60-95)
- CHANGELOG.md before merge

---

## File Naming Convention (Critical)

**PDF Export Naming Scheme:**  
Format: `{type}_{initial}.{surname}_{company}_{role}_{date}.pdf`

Examples:
- cv_j.doe_google_software-engineer_19.01.26.pdf
- cl_m.smith_amazon_data-scientist_15.03.26.pdf

Implementation:
```python
# app/services/export.py
def generate_filename(doc_type, first_name, last_name, company, role):
    from datetime import datetime
    import re
    initial = first_name[0].lower()
    surname = last_name.lower()
    company_slug = re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')
    role_slug = re.sub(r'[^a-z0-9]+', '-', role.lower()).strip('-')
    date = datetime.now().strftime('%d.%m.%y')
    return f"{doc_type}_{initial}.{surname}_{company_slug}_{role_slug}_{date}.pdf"
```

---

## Agent Handoff Checklist

- [ ] Read app/main.py (FastAPI routes, lifespan)
- [ ] Read app/services/workflow_orchestrator.py (CORE - 619 lines)
- [ ] Read app/database/models/resume.py (data schema)
- [ ] Run `docker-compose up -d` (start all services)
- [ ] Run `pytest tests/ -v` (verify tests pass)
- [ ] Visit http://localhost:8080/docs (Swagger API docs)
- [ ] Review recent CHANGELOG.md for patterns
- [ ] Check .env-template.txt for required variables
- [ ] Understand error handling in app/utils/error_handler.py
- [ ] Ask clarifying questions if unclear

---

## Priorities (In Order)

1. **CV Optimization Pipeline**: analyze → optimize → generate (workflow_orchestrator.py)
2. **API Latency**: p95 <10s (cached <2s) via Redis hashing
3. **JSON Parsing Robustness**: Handle truncated AI responses with safe_json_parse()
4. **Test Coverage**: Maintain ≥90% (pytest)
5. **Docker Image**: Keep <500MB (check requirements.txt for bloat)
6. **ATS Score Realism**: 60-95 range (not inflated 99s)

---

## 1. Database & Data Persistence

### MongoDB Schema Pattern
```python
# File: app/database/models/resume.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Resume(BaseModel):
    _id: Optional[str] = None
    user_id: str = Field(..., description="User identifier")
    title: str = Field(..., min_length=5, max_length=200)
    original_content: str = Field(..., description="Raw CV text")
    job_description: str = Field(...)
    optimized_data: dict = Field(default_factory=dict)
    ats_score: int = Field(ge=60, le=95, default=0)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    target_company: str = Field(default="")
    target_role: str = Field(default="")
    email: Optional[str] = None  # ALWAYS OPTIONAL - prevents 500 errors
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

### Repository Pattern (ALWAYS Use)
```python
# File: app/database/repositories/resume_repository.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from app.database.models.resume import Resume
from app.config.logging_config import logger

class ResumeRepository:
    def __init__(self, db: AsyncIOMotorDatabase = None):
        from app.database.connector import MongoConnectionManager
        self.db = db or MongoConnectionManager.get_instance().db
    
    async def create_resume(self, resume: Resume) -> str:
        """Insert resume, return MongoDB ID."""
        try:
            result = await self.db.resumes.insert_one(resume.model_dump())
            logger.info(f"Resume created: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Insert failed: {e}", exc_info=True)
            raise
    
    async def get_resume(self, resume_id: str) -> Optional[Resume]:
        """Fetch resume by ID."""
        try:
            doc = await self.db.resumes.find_one({"_id": ObjectId(resume_id)})
            return Resume(**doc) if doc else None
        except Exception as e:
            logger.error(f"Query failed for {resume_id}: {e}")
            raise
    
    async def list_user_resumes(self, user_id: str, limit: int = 50) -> List[Resume]:
        """Get resumes for user, sorted by date."""
        cursor = self.db.resumes.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Resume(**doc) for doc in docs]
    
    async def update_resume(self, resume_id: str, data: dict) -> bool:
        """Update resume fields."""
        try:
            result = await self.db.resumes.update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {**data, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Update failed: {e}")
            raise
    
    async def delete_resume(self, resume_id: str) -> bool:
        """Soft delete (mark as archived)."""
        return await self.update_resume(resume_id, {"archived": True})
```

### Indexing & Performance
```python
# File: app/database/connector.py (in __init__)
async def setup_indexes(self):
    """Create indexes for fast queries."""
    try:
        # Composite index for user lookups
        await self.db.resumes.create_index([("user_id", 1), ("created_at", -1)])
        # Text index for searching
        await self.db.resumes.create_index([("original_content", "text"), ("optimized_data", "text")])
        # TTL index for auto-cleanup (30 days)
        await self.db.resumes.create_index([("created_at", 1)], expireAfterSeconds=2592000)
        logger.info("Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")
```

### Usage in Endpoints
```python
# In app/api/routers/resume/router.py
@router.post("/resume")
async def create_resume(request: OptimizationRequest, repo: ResumeRepository = Depends()):
    # Repository injected via dependency
    resume_data = Resume(
        user_id=request.user_id,
        title=f"Optimized for {request.target_company}",
        original_content=request.cv_text,
        job_description=request.jd_text,
        ats_score=result.get("ats_score", 0)
    )
    resume_id = await repo.create_resume(resume_data)
    return {"resume_id": resume_id, "status": "saved"}

@router.get("/resume/{resume_id}")
async def get_resume(resume_id: str, repo: ResumeRepository = Depends()):
    resume = await repo.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume
```

### Redis Caching for Expensive Queries
```python
# Cache analysis results to avoid redundant API calls
import redis.asyncio as redis
import json

class CachedResumeRepository(ResumeRepository):
    def __init__(self, db, cache_client: redis.Redis):
        super().__init__(db)
        self.cache = cache_client
    
    async def get_resume_cached(self, resume_id: str, ttl: int = 3600) -> Optional[Resume]:
        """Get resume with Redis cache."""
        cache_key = f"resume:{resume_id}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {resume_id}")
            return Resume(**json.loads(cached))
        
        # Miss: query DB
        resume = await self.get_resume(resume_id)
        if resume:
            # Cache for 1 hour
            await self.cache.setex(cache_key, ttl, resume.model_dump_json())
        
        return resume
```

---

## 2. n8n Automation Integration

### Webhook Connection Pattern
```python
# File: app/routes/n8n_integration.py
from fastapi import APIRouter, Request, HTTPException
import httpx
from app.config.settings import get_settings

router = APIRouter(prefix="/api/n8n", tags=["n8n Webhooks"])

@router.post("/trigger/optimize")
async def trigger_n8n_workflow(resume_id: str):
    """Trigger n8n workflow when resume is optimized."""
    settings = get_settings()
    webhook_url = f"{settings.N8N_WEBHOOK_URL}/webhook/resume-optimized"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                webhook_url,
                json={
                    "resume_id": resume_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "optimization_complete"
                },
                headers={"Authorization": f"Bearer {settings.N8N_API_KEY}"}
            )
            response.raise_for_status()
            logger.info(f"n8n workflow triggered for {resume_id}")
            return {"status": "triggered", "webhook": webhook_url}
    except httpx.HTTPError as e:
        logger.error(f"Webhook call failed: {e}")
        raise HTTPException(status_code=500, detail="Workflow trigger failed")
```

### n8n Workflow Structure
```json
{
  "name": "CV Optimization Complete",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "resume-optimized",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Fetch Resume Data",
      "type": "n8n-nodes-base.http",
      "parameters": {
        "url": "http://powercv:8080/api/resume/{{ $json.resume_id }}",
        "method": "GET"
      }
    },
    {
      "name": "Send Email Notification",
      "type": "n8n-nodes-base.sendGrid",
      "parameters": {
        "email": "{{ $json.user_email }}",
        "subject": "Your resume is ready!",
        "htmlBody": "<p>Your optimized resume has been generated.</p><p>ATS Score: {{ $json.ats_score }}</p>"
      }
    },
    {
      "name": "Log to Analytics",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "INSERT INTO analytics (resume_id, ats_score) VALUES ($1, $2)",
        "values": "{{ $json.resume_id }}, {{ $json.ats_score }}"
      }
    }
  ]
}
```

### Listening for n8n Callbacks
```python
# File: app/routes/n8n_integration.py
@router.post("/callback/pdf-generated")
async def n8n_pdf_generated_callback(request: Request):
    """Receive callback when n8n finishes PDF generation."""
    data = await request.json()
    
    # Validate webhook signature
    signature = request.headers.get("X-N8N-Signature")
    if not verify_n8n_signature(signature, data, get_settings().N8N_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Update resume with PDF URL
    repo = ResumeRepository()
    await repo.update_resume(data["resume_id"], {
        "pdf_url": data["pdf_url"],
        "pdf_generated_at": datetime.utcnow()
    })
    
    logger.info(f"PDF generated callback received for {data['resume_id']}")
    return {"status": "acknowledged"}
```

### Environment Configuration
```bash
# .env
N8N_WEBHOOK_URL=http://n8n:5678
N8N_API_KEY=your_n8n_api_key
N8N_ENCRYPTION_KEY=random_32_char_encryption_key
```

---

## 3. Testing Strategies

### Unit Tests (pytest + asyncio)
```python
# tests/test_cv_analyzer.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.cv_analyzer import CVAnalyzer
from app.config.logging_config import logger

@pytest.fixture
def analyzer():
    return CVAnalyzer()

@pytest.fixture
def sample_cv():
    return """
    John Doe
    Senior Software Engineer
    Skills: Python, FastAPI, MongoDB, React
    Experience: 8 years in full-stack development
    """

@pytest.fixture
def sample_jd():
    return """
    Job: Senior Backend Engineer
    Requirements: Python, FastAPI, MongoDB, Docker
    Responsibilities: API development, database design
    """

@pytest.mark.asyncio
async def test_analyze_returns_realistic_ats_score(analyzer, sample_cv, sample_jd):
    """ATS scores must be between 60-95 (realistic range)."""
    result = await analyzer.analyze(sample_cv, sample_jd)
    
    assert result["ats_score"] >= 60, "Score too low (inflated expectations)"
    assert result["ats_score"] <= 95, "Score too high (unrealistic)"
    assert isinstance(result["ats_score"], int)

@pytest.mark.asyncio
async def test_analyze_includes_keyword_analysis(analyzer, sample_cv, sample_jd):
    result = await analyzer.analyze(sample_cv, sample_jd)
    
    assert "keyword_analysis" in result
    assert "matched_keywords" in result["keyword_analysis"]
    assert "missing_critical" in result["keyword_analysis"]
    assert len(result["keyword_analysis"]["matched_keywords"]) > 0

@pytest.mark.asyncio
async def test_analyze_empty_input_raises_error(analyzer):
    with pytest.raises(ValueError, match="CV cannot be empty"):
        await analyzer.analyze("", "Job description")

@pytest.mark.asyncio
async def test_analyze_respects_rate_limits(analyzer):
    """Test retry logic on rate limit."""
    with patch.object(analyzer, '_call_ai_api') as mock_api:
        # Simulate rate limit then success
        mock_api.side_effect = [
            HTTPStatusError(status_code=429),  # Rate limited
            {"ats_score": 75, "analysis": {}}  # Success on retry
        ]
        
        result = await analyzer.analyze("CV", "JD")
        assert result["ats_score"] == 75
        assert mock_api.call_count == 2  # Called twice (1 fail + 1 retry)
```

### Integration Tests (API Testing)
```python
# tests/test_api_optimize.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_optimize_endpoint_full_workflow(client):
    """Test complete optimization pipeline."""
    response = await client.post(
        "/api/v2/optimize",
        json={
            "cv_text": "John Doe\nSoftware Engineer\nPython, JavaScript, MongoDB",
            "jd_text": "Senior Backend Dev\nRequires: Python, MongoDB, FastAPI",
            "generate_cover_letter": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert "ats_score" in data
    assert "analysis" in data
    assert "optimized_cv" in data
    assert "cover_letter" in data or data["cover_letter"] is None
    assert "resume_id" in data
    
    # Validate ATS score range
    assert 60 <= data["ats_score"] <= 95

@pytest.mark.asyncio
async def test_optimize_missing_required_fields(client):
    """Test validation error handling."""
    response = await client.post(
        "/api/v2/optimize",
        json={"cv_text": "Short"}  # Missing jd_text
    )
    
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_optimize_rate_limit_handling(client):
    """Test behavior under rate limiting."""
    # This tests the retry logic in the service layer
    response = await client.post(
        "/api/v2/optimize",
        json={
            "cv_text": "A" * 100,
            "jd_text": "B" * 100
        }
    )
    
    # Should succeed (not fail) even if provider is rate limited
    assert response.status_code == 200
```

### Frontend Tests (Vitest + React Testing Library)
```typescript
// frontend/src/components/__tests__/OptimizeForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OptimizeForm } from '../OptimizeForm';

describe('OptimizeForm', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  const renderForm = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <OptimizeForm />
      </QueryClientProvider>
    );
  };

  test('submits form with CV and JD', async () => {
    const user = userEvent.setup();
    renderForm();

    const cvInput = screen.getByLabelText(/cv text/i);
    const jdInput = screen.getByLabelText(/job description/i);
    const submitBtn = screen.getByRole('button', { name: /optimize/i });

    await user.type(cvInput, 'John Doe\nSoftware Engineer');
    await user.type(jdInput, 'Senior Backend Developer');
    await user.click(submitBtn);

    // Button should show loading state
    expect(submitBtn).toHaveAttribute('disabled');
    expect(submitBtn).toHaveTextContent(/optimizing/i);
  });

  test('displays error message on API failure', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/cv text/i), 'Short');
    await user.click(screen.getByRole('button', { name: /optimize/i }));

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  test('displays ATS score in result', async () => {
    renderForm();
    
    // Mock successful API response
    const cvInput = screen.getByLabelText(/cv text/i);
    await userEvent.type(cvInput, 'Full CV content');
    
    await waitFor(() => {
      expect(screen.getByText(/ats score: \d+/i)).toBeInTheDocument();
    });
  });
});
```

### Coverage Targets
```bash
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
python_files = test_*.py
python_functions = test_*
addopts = --cov=app --cov-fail-under=90 --cov-report=html

# Run with coverage
pytest --cov=app --cov-fail-under=90 --cov-report=term-missing
```

---

## 4. Deployment & Scaling

### Docker Build Optimization
```dockerfile
# File: Dockerfile (multi-stage build)
FROM python:3.12-slim as builder

WORKDIR /app
RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Production stage (smaller image)
FROM python:3.12-slim

WORKDIR /app

# Copy only necessary files
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY app ./app
COPY .env .env
COPY pyproject.toml ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Docker Compose for Production
```yaml
# docker-compose.yml (production-ready)
version: '3.9'

services:
  powercv:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: powercv-api
    restart: unless-stopped
    ports:
      - "8081:8080"
    environment:
      - CEREBRAS_API_KEY=${CEREBRAS_API_KEY}
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/app/data  # Persist generated files
      - ./logs:/app/logs  # Log files
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - powercv-net
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  mongodb:
    image: mongo:7.0
    container_name: powercv-mongodb
    restart: unless-stopped
    ports:
      - "27018:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGODB_ROOT_USER:-admin}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD}
      - MONGO_INITDB_DATABASE=powercv
    volumes:
      - mongodb_data:/data/db
    networks:
      - powercv-net
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: powercv-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - powercv-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  mongodb_data:
  redis_data:

networks:
  powercv-net:
    driver: bridge
```

### Environment Configuration
```bash
# .env (template)
# AI Provider
CEREBRAS_API_KEY=your_key
CEREBRAS_MODEL=gpt-oss-120b
CEREBRAS_API_BASE=https://api.cerebras.ai/v1

# Database
MONGODB_URI=mongodb://admin:password@mongodb:27017/powercv?authSource=admin
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=secure_password

# Cache
REDIS_URL=redis://redis:6379

# Application
APP_HOST=0.0.0.0
APP_PORT=8080
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here

# n8n
N8N_WEBHOOK_URL=http://n8n:5678
N8N_API_KEY=your_n8n_key
```

### Health Check & Monitoring
```python
# File: app/main.py (health endpoint)
@app.get("/health")
async def health_check():
    """Health check for container orchestration."""
    try:
        # Check MongoDB
        await MongoConnectionManager.get_instance().db.command('ping')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        db_status = "unhealthy"
    
    try:
        # Check Redis
        redis_conn = await redis.from_url(get_settings().REDIS_URL)
        await redis_conn.ping()
        redis_status = "healthy"
        await redis_conn.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "database": db_status,
        "cache": redis_status,
        "version": app.version,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Scaling Strategies
```bash
# Horizontal scaling with Docker Swarm
docker service create \
  --name powercv \
  --replicas 3 \
  --port 8080:8080 \
  --env-file .env \
  ghcr.io/illnar-nizami/powercv:latest

# Load balancer (Traefik example)
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.powercv.rule=Host(\`api.powercv.local\`)"
  - "traefik.http.services.powercv.loadbalancer.server.port=8080"
```

---

## 5. Frontend State Management

### Zustand Store Pattern
```typescript
// File: frontend/src/stores/optimizationStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface OptimizationResult {
  ats_score: number;
  analysis: Record<string, any>;
  optimized_cv: string;
  cover_letter?: string;
  resume_id?: string;
}

interface OptimizationStore {
  // State
  cvText: string;
  jdText: string;
  isOptimizing: boolean;
  results: OptimizationResult | null;
  error: string | null;
  lastOptimized: Date | null;
  
  // Actions
  setCVText: (text: string) => void;
  setJDText: (text: string) => void;
  setOptimizing: (loading: boolean) => void;
  setResults: (results: OptimizationResult) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  clearResults: () => void;
}

export const useOptimizationStore = create<OptimizationStore>()(
  persist(
    (set) => ({
      // Initial state
      cvText: '',
      jdText: '',
      isOptimizing: false,
      results: null,
      error: null,
      lastOptimized: null,
      
      // Actions
      setCVText: (text) => set({ cvText: text }),
      setJDText: (text) => set({ jdText: text }),
      setOptimizing: (loading) => set({ isOptimizing: loading }),
      setResults: (results) => set({ 
        results, 
        lastOptimized: new Date(),
        error: null 
      }),
      setError: (error) => set({ error, isOptimizing: false }),
      reset: () => set({
        cvText: '',
        jdText: '',
        results: null,
        error: null
      }),
      clearResults: () => set({ results: null })
    }),
    {
      name: 'optimization-store',
      partialize: (state) => ({
        cvText: state.cvText,
        jdText: state.jdText,
        results: state.results,
        lastOptimized: state.lastOptimized
      })
    }
  )
);
```

### React Query Pattern
```typescript
// File: frontend/src/hooks/useOptimizeCV.ts
import { useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useOptimizationStore } from '@/stores/optimizationStore';
import { AxiosError } from 'axios';

interface OptimizeRequest {
  cv_text: string;
  jd_text: string;
  generate_cover_letter?: boolean;
}

export function useOptimizeCV() {
  const store = useOptimizationStore();
  
  return useMutation<any, AxiosError, OptimizeRequest>({
    mutationFn: async (data) => {
      store.setOptimizing(true);
      try {
        const response = await api.post('/api/v2/optimize', data, {
          timeout: 30000  // 30 second timeout
        });
        return response.data;
      } finally {
        store.setOptimizing(false);
      }
    },
    onSuccess: (result) => {
      store.setResults(result);
    },
    onError: (error) => {
      const errorMsg = error.response?.data?.detail || 'Optimization failed';
      store.setError(errorMsg);
    }
  });
}

// Usage in component
export function TailorForm() {
  const { cvText, jdText, isOptimizing } = useOptimizationStore();
  const optimizeMutation = useOptimizeCV();
  
  const handleOptimize = () => {
    optimizeMutation.mutate({
      cv_text: cvText,
      jd_text: jdText,
      generate_cover_letter: true
    });
  };
  
  return (
    <form onSubmit={(e) => { e.preventDefault(); handleOptimize(); }}>
      {/* Form fields */}
      <button disabled={isOptimizing || optimizeMutation.isPending}>
        {isOptimizing ? 'Optimizing...' : 'Optimize'}
      </button>
    </form>
  );
}
```

### Error Boundary Pattern
```typescript
// File: frontend/src/components/ErrorBoundary.tsx
import React, { ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error('ErrorBoundary caught:', error);
    // Send to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded">
          <AlertCircle className="text-red-600" />
          <div>
            <h3 className="font-semibold text-red-900">Something went wrong</h3>
            <p className="text-red-700">{this.state.error?.message}</p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
<ErrorBoundary>
  <OptimizeForm />
</ErrorBoundary>
```

---

## 6. AI Provider Integration

### Multi-Provider Fallback Chain
```python
# File: app/services/ai_providers.py
from enum import Enum
from typing import Optional
import httpx
from app.config.logging_config import logger

class AIProvider(Enum):
    CEREBRAS = "cerebras"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"

class AIProviderClient:
    """Multi-provider AI client with automatic fallback."""
    
    def __init__(self):
        self.primary = AIProvider.CEREBRAS
        self.fallback_chain = [AIProvider.CEREBRAS, AIProvider.OPENAI, AIProvider.DEEPSEEK]
    
    async def chat_completion(
        self, 
        system_prompt: str, 
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Call AI with fallback."""
        last_error = None
        
        for provider in self.fallback_chain:
            try:
                logger.info(f"Attempting {provider.value}...")
                result = await self._call_provider(
                    provider, 
                    system_prompt, 
                    user_message,
                    temperature,
                    max_tokens
                )
                logger.info(f"Success with {provider.value}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"{provider.value} failed: {e}, trying next...")
                continue
        
        raise Exception(f"All AI providers failed. Last error: {last_error}")
    
    async def _call_provider(
        self,
        provider: AIProvider,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call specific provider."""
        if provider == AIProvider.CEREBRAS:
            return await self._call_cerebras(system_prompt, user_message, temperature, max_tokens)
        elif provider == AIProvider.OPENAI:
            return await self._call_openai(system_prompt, user_message, temperature, max_tokens)
        elif provider == AIProvider.DEEPSEEK:
            return await self._call_deepseek(system_prompt, user_message, temperature, max_tokens)
    
    async def _call_cerebras(self, system_prompt: str, user_message: str, temperature: float, max_tokens: int) -> str:
        """Cerebras API call."""
        from app.config.settings import get_settings
        settings = get_settings()
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.CEREBRAS_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.CEREBRAS_API_KEY}"},
                json={
                    "model": settings.CEREBRAS_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    
    async def _call_openai(self, system_prompt: str, user_message: str, temperature: float, max_tokens: int) -> str:
        """OpenAI API call (fallback)."""
        from app.config.settings import get_settings
        settings = get_settings()
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    
    async def _call_deepseek(self, system_prompt: str, user_message: str, temperature: float, max_tokens: int) -> str:
        """Deepseek API call (last resort fallback)."""
        from app.config.settings import get_settings
        settings = get_settings()
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.DEEPSEEK_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
```

### Retry Logic with Exponential Backoff
```python
# File: app/services/retry_handler.py
import asyncio
from functools import wraps
from typing import Callable, Any
import random

def exponential_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for exponential backoff retry logic."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # Check if retryable error
                    if isinstance(e, (httpx.HTTPStatusError, asyncio.TimeoutError)):
                        if attempt < max_attempts - 1:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            continue
                    
                    raise
            
            raise last_error
        
        return wrapper
    return decorator

# Usage
@exponential_backoff(max_attempts=3, base_delay=1.0)
async def call_ai_api(prompt: str) -> str:
    # API call that might timeout or rate limit
    pass
```

### Rate Limit Handling
```python
# File: app/services/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.window = 60  # seconds
        self.tokens = defaultdict(lambda: deque())
    
    async def acquire(self, key: str = "default"):
        """Acquire a token, wait if necessary."""
        now = datetime.utcnow()
        tokens = self.tokens[key]
        
        # Remove old tokens outside window
        while tokens and tokens[0] < now - timedelta(seconds=self.window):
            tokens.popleft()
        
        # Check if we can proceed
        if len(tokens) < self.calls_per_minute:
            tokens.append(now)
            return
        
        # Wait until oldest token is out of window
        sleep_time = (tokens[0] + timedelta(seconds=self.window) - now).total_seconds()
        logger.warning(f"Rate limit reached, waiting {sleep_time:.2f}s...")
        await asyncio.sleep(sleep_time)
        tokens.append(datetime.utcnow())

# Usage in service
limiter = RateLimiter(calls_per_minute=60)

async def call_cerebras_api(prompt):
    await limiter.acquire("cerebras")
    # Call API
```

---

## 7. PDF Generation Pipeline

### Typst Template Structure
```typst
// File: data/templates/resume.typ
#let project(name, location, position, start_date, end_date, description) = {
  block(
    below: 1em,
    [
      *#name* (#location) | _#position_ | #start_date – #end_date
      #description
    ]
  )
}

#let cv(
  author: "John Doe",
  location: "New York, NY",
  phone: "+1 234 567 8900",
  email: "john@example.com",
  body
) = {
  set document(title: "CV - " + author, author: author)
  set page(margin: (top: 2cm, bottom: 2cm, left: 2cm, right: 2cm))
  set text(font: "Calibri", size: 11pt)
  
  // Header
  block(
    below: 1.5em,
    [
      #heading(level: 1, author)
      #location | #link("tel:" + phone) | #link("mailto:" + email)
    ]
  )
  
  body
}

// Content
#show: cv.with(
  author: "{{ candidate_name }}",
  location: "{{ location }}",
  phone: "{{ phone }}",
  email: "{{ email }}"
)

== Experience

#project(
  name: "Senior Software Engineer",
  location: "Tech Company",
  position: "Full-stack Development",
  start_date: "2022",
  end_date: "Present",
  description: [
    - Led development of microservices architecture
    - Improved API performance by 40%
  ]
)
```

### PDF Generation Service
```python
# File: app/services/pdf_generator.py
import subprocess
from pathlib import Path
from app.config.logging_config import logger
from app.database.models.resume import Resume

class PdfGenerator:
    """Generate PDFs using Typst."""
    
    def __init__(self, templates_dir: str = "data/templates"):
        self.templates_dir = Path(templates_dir)
    
    async def generate_pdf(
        self,
        resume: Resume,
        template: str = "resume.typ",
        output_dir: str = "data/generated"
    ) -> str:
        """Generate PDF and return file path."""
        try:
            # Prepare template file
            template_path = self.templates_dir / template
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template}")
            
            # Prepare output
            output_path = Path(output_dir) / f"{resume._id}.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare context data
            context = {
                "candidate_name": resume.optimized_data.get("name", "Unknown"),
                "location": resume.optimized_data.get("location", ""),
                "email": resume.email or "",
                "phone": resume.optimized_data.get("phone", ""),
                "summary": resume.optimized_data.get("summary", ""),
                "skills": resume.matching_skills,
                "experience": resume.optimized_data.get("experience", []),
                "education": resume.optimized_data.get("education", [])
            }
            
            # Render Typst
            typst_input = self._render_template(template_path, context)
            
            # Call typst CLI
            result = subprocess.run(
                [
                    "typst",
                    "compile",
                    "--root", str(self.templates_dir),
                    "-",  # Read from stdin
                    str(output_path)
                ],
                input=typst_input.encode(),
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Typst compilation failed: {result.stderr.decode()}")
            
            logger.info(f"PDF generated: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            raise
    
    def _render_template(self, template_path: Path, context: dict) -> str:
        """Render Typst template with context."""
        with open(template_path) as f:
            template = f.read()
        
        # Replace variables
        for key, value in context.items():
            if isinstance(value, list):
                value = "\n".join(f"- {item}" for item in value)
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        
        return template
```

### Template Selection Logic
```python
# File: app/api/routers/resume/router.py
from app.config.templates import AVAILABLE_TEMPLATES

AVAILABLE_TEMPLATES = {
    "resume.typ": {"name": "Classic", "description": "Clean, traditional layout"},
    "modern.typ": {"name": "Modern", "description": "Contemporary two-column design"},
    "brilliant-cv/cv.typ": {"name": "Brilliant CV", "description": "Professional with icons"},
    "simple-xd-resume/cv.typ": {"name": "Simple XD", "description": "ATS-friendly design"}
}

@router.get("/templates")
async def list_templates():
    """Get available CV templates."""
    return {
        "templates": [
            {
                "id": key,
                "name": value["name"],
                "description": value["description"]
            }
            for key, value in AVAILABLE_TEMPLATES.items()
        ]
    }

@router.post("/resume/{resume_id}/export")
async def export_resume_pdf(
    resume_id: str,
    template: str = "resume.typ",
    repo: ResumeRepository = Depends()
):
    """Export resume as PDF."""
    # Validate template
    if template not in AVAILABLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template}")
    
    # Get resume
    resume = await repo.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Generate PDF
    pdf_generator = PdfGenerator()
    pdf_path = await pdf_generator.generate_pdf(resume, template)
    
    # Generate professional filename
    filename = generate_pdf_filename(
        doc_type="cv",
        first_name=resume.optimized_data.get("name", "").split()[0],
        last_name=resume.optimized_data.get("name", "").split()[-1] if " " in resume.optimized_data.get("name", "") else "",
        company=resume.target_company or "target",
        role=resume.target_role or "role"
    )
    
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf"
    )
```

### Export Flow
```python
# File: app/services/export.py
import re
from datetime import date

def generate_pdf_filename(
    doc_type: str,  # "cv" or "cl"
    first_name: str,
    last_name: str,
    company: str,
    role: str
) -> str:
    """Generate professional PDF filename.
    
    Format: {type}_{initial}.{surname}_{company}_{role}_{date}.pdf
    Example: cv_j.doe_google_software-engineer_20.01.26.pdf
    """
    initial = first_name[0].lower() if first_name else "u"
    surname = last_name.lower() if last_name else "unknown"
    company_slug = re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')
    role_slug = re.sub(r'[^a-z0-9]+', '-', role.lower()).strip('-')
    date_str = date.today().strftime('%d.%m.%y')
    
    return f"{doc_type}_{initial}.{surname}_{company_slug}_{role_slug}_{date_str}.pdf"
```

---

## Summary Table: Where to Find Everything

| Topic | Key File | When to Edit |
|-------|----------|--------------|
| **Database Queries** | `app/database/repositories/` | Adding new query patterns |
| **MongoDB Models** | `app/database/models/resume.py` | Changing resume schema |
| **n8n Webhooks** | `app/routes/n8n_integration.py` | Triggering workflows |
| **Unit Tests** | `tests/test_*.py` | Adding test coverage |
| **Integration Tests** | `tests/test_api_*.py` | Testing endpoints |
| **Frontend Tests** | `frontend/src/**/__tests__/` | Component testing |
| **Docker Config** | `docker-compose.yml` | Service setup, scaling |
| **Health Checks** | `app/main.py` | Monitoring endpoints |
| **State Management** | `frontend/src/stores/` | Global state logic |
| **React Queries** | `frontend/src/hooks/` | Data fetching logic |
| **Error Boundaries** | `frontend/src/components/ErrorBoundary.tsx` | Error handling |
| **AI Providers** | `app/services/ai_providers.py` | Adding fallbacks |
| **Rate Limiting** | `app/services/rate_limiter.py` | API throttling |
| **PDF Generation** | `app/services/pdf_generator.py` | Template rendering |
| **Typst Templates** | `data/templates/*.typ` | Resume layout |

---