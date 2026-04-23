# PowerCV Agent Consolidated Rules

**Consolidated:** 2026-02-01  
**Version:** 4.0.0  
**Sources:** 6 documentation files consolidated  
**Purpose:** Single source of truth for all agents operating on PowerCV codebase

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Task Workflows](#2-task-workflows)
3. [Communication Standards](#3-communication-standards)
4. [Technical Guidelines](#4-technical-guidelines)
5. [Constraints and Rules](#5-constraints-and-rules)
6. [File Naming Conventions](#6-file-naming-conventions)
7. [Performance Targets](#7-performance-targets)
8. [Quick Reference](#8-quick-reference)

---

## 1. Core Principles

### 1.1 Project Identity

**PowerCV** is an AI-powered CV optimization platform that:

- Parses CVs (PDF/DOCX/JSON) extracting 150+ fields (87% baseline accuracy)
- Tailors resumes to job descriptions with ATS scoring (98% target)
- Generates cover letters in multiple languages (EN, NL, RU)
- Exports to JSON, HTML, and PDF formats
- Maintains GDPR compliance and bias-free outputs

**Repository:** https://github.com/powercv/powercv  
**Mode:** Use "powercv" mode for all PowerCV-specific tasks

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     PowerCV Architecture                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Frontend  │────▶│  Main API   │────▶│  MongoDB    │   │
│  │  React/Vite │     │  FastAPI    │     │  (primary)  │   │
│  │  :3000      │     │  :8081      │     └─────────────┘   │
│  └─────────────┘     └──────┬──────┘          │            │
│                             │                 │            │
│                             ▼                 ▼            │
│                      ┌─────────────┐     ┌─────────────┐   │
│                      │  AI Service │────▶│  PostgreSQL │   │
│                      │  FastAPI    │     │  (dual-write)│   │
│                      │  :8082      │     └─────────────┘   │
│                      └─────────────┘                       │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐                       │
│  │   Redis     │◀────│  Rate Limit │                       │
│  │  (:6379)    │     │  & Cache    │                       │
│  └─────────────┘     └─────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Backend** | Python 3.11+, FastAPI, AsyncIO | Async-first, Pydantic v2 |
| **Frontend** | React 19, TypeScript strict, Vite, TailwindCSS | <200KB gzipped |
| **Database** | MongoDB (primary), PostgreSQL (dual-write) | Motor async driver |
| **Cache** | Redis | AI responses, workflow results, TTL 3600s |
| **AI** | Cerebras (primary), OpenAI (fallback) | Groq also supported |
| **Container** | Docker Compose | 5 services: app, mongodb, redis, postgres, n8n |
| **Testing** | pytest | 90%+ coverage gate |

### 1.4 Key Directories

```
PowerCV/
├── app/
│   ├── api/routers/          # API endpoints (comprehensive_optimizer, parser, cover_letter)
│   ├── services/             # Business logic (workflow_orchestrator, ai_providers)
│   ├── database/             # Models and repositories
│   ├── config/               # Settings, Redis, logging
│   ├── middleware/           # Rate limiting, debugging
│   ├── utils/                # Shared utilities
│   └── tests/                # Test suite
├── ai-service/               # Separate AI microservice (:8082)
├── frontend/                 # React frontend (:3000)
├── scripts/                  # Utility scripts
├── data/                     # Templates and storage
├── n8n_workflows/            # Workflow automation (preserve!)
├── docker-compose.yml        # Container orchestration
├── pyproject.toml            # Python dependencies
└── CHANGELOG.md              # Semantic versioning (update on changes!)
```

---

## 2. Task Workflows

### 2.1 Pre-Implementation Checklist (30 seconds)

Before any code changes, always run:

```bash
# 1. Check database state
./scripts/migration_status.sh

# 2. Review pending tasks
grep "TODO" implementation_checklist.md

# 3. Verify service health
docker-compose ps

# 4. Check environment
cat .env | head -10
```

### 2.2 Development Workflow

**Option 1: Full Local (No Docker)**

```bash
# Terminal 1: Start AI Service
cd /path/to/PowerCV
source .venv/bin/activate
cd ai-service
python -m uvicorn main:app --host 0.0.0.0 --port 8082

# Terminal 2: Start Main API
cd /path/to/PowerCV
source .venv/bin/activate
python scripts/run.sh
```

**Option 2: With Docker (AI Service only)**

```bash
# Start only AI Service with Docker
docker-compose up -d ai-service

# Run main API locally
python scripts/run.sh
```

### 2.3 Backend Pattern (Python 3.11+)

```python
# app/api/v1/cv.py
from fastapi import APIRouter, Depends, BackgroundTasks
from app.schemas import CVTailorRequest, CVResponse
from app.services import TailoringService
from app.middleware.rate_limiter import rate_limit_api

@router.post("/tailor", response_model=CVResponse)
async def tailor_cv(
    request: CVTailorRequest,
    bg_tasks: BackgroundTasks,
    service: TailoringService = Depends(),
    _: None = Depends(rate_limit_api),
) -> CVResponse:
    """Tailor CV: 95%+ ATS, <3s cached/<8s cold, GDPR Article 22"""
    result = await service.tailor(request, cache_key=request.cache_hash)
    bg_tasks.add_task(service.log_analytics, result.metadata)
    return result
```

**Rules:**
- Async-first, all endpoints must be `async def`
- Use Pydantic v2 models with `response_model`
- Rate limit heavy endpoints (10 calls/minute)
- Use BackgroundTasks for non-blocking operations
- Cache results with Redis (SHA-256 hash of inputs, TTL 3600s)

### 2.4 Frontend Pattern (React 19 + TypeScript)

```typescript
// frontend/src/components/TailorForm.tsx
import { useMutation } from '@tanstack/react-query';
import { tailorCV } from '@/services/api';

export function TailorForm() {
  const mutation = useMutation({ mutationFn: tailorCV });
  return (
    <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(data); }}>
      <textarea 
        aria-describedby="help" 
        className="w-full border rounded-lg p-3" 
      />
      <button disabled={mutation.isPending} className="btn-primary">
        Optimize
      </button>
    </form>
  );
}
```

**Rules:**
- React Query for data fetching and mutations
- TypeScript strict mode, no `any` type
- Tailwind utilities only, no custom CSS
- ARIA labels for accessibility (WCAG 2.2 AA)
- Bundle size <200KB gzipped

### 2.5 Validation Pipeline (Required Before Commit)

```bash
./scripts/run.sh test
```

This runs:
1. `poetry install` - Dependencies
2. `black .` - Code formatting
3. `ruff check . --fix` - Linting
4. `mypy . --strict` - Type checking
5. `pytest --cov-fail-under=90` - Tests with coverage gate
6. `docker-compose -f docker-compose.ci.yml up --build` - Container build
7. `curl http://localhost:8000/health` - Health check
8. `mkdocs build --strict` - Documentation

**Gates:**
- ❌ <90% coverage = FAIL
- ❌ Mypy errors = BLOCK
- ❌ Docker >500MB = OPTIMIZE
- ❌ Broken links = FIX

---

## 3. Communication Standards

### 3.1 Output Format (Strict)

Every code change must include:

```
SUMMARY: Changes | Impact (metrics) | Coverage (Δ%)

FILES:
## app/api/v1/cv.py (modified)
```python
[full code with # NEW: comments]
```

TESTS: tests/test_*.py + coverage snippet
VALIDATION: [pytest/docker/mkdocs logs]
DOCS: CHANGELOG.md diff
NEXT: ./run.sh test && ./scripts/commit_review_fixes.sh "feat: description"

✅ VALIDATED: pytest 90%+ | docker <500MB | mkdocs served | changelog updated
```

### 3.2 Documentation Requirements

**Changelog Format:**
```markdown
## [1.3.0] - 2026-01-12
### Added
- Multilingual tailoring EN/NL/RU (#47)
  Impact: +35% international users
  Files: app/core/ai/multilingual.py
```

**Inline Documentation:**
- Pydoc/JSDoc on all public functions
- Type hints on all function signatures
- Complex logic must have inline comments

**MkDocs:**
- Create `docs/features/*.md` for new features
- Update `mkdocs.yml` navigation

### 3.3 Error Handling

Use `ErrorHandler` class from `app/utils/error_handler.py`:

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

### 3.4 Logging

Use structured JSON logging from `app/config/logging_config.py`:

```python
from app.config.logging_config import logger

logger.info("Starting optimization", extra={"cv_length": 1500, "jd_length": 800})
logger.warning("Rate limit approaching", extra={"remaining": 5})
logger.error("AI API failed", exc_info=True)  # Logs traceback
```

**NEVER use `print()` in production code** - use logger instead.

---

## 4. Technical Guidelines

### 4.1 Backend Guidelines

**File Structure:**
- `app/api/routers/` - API endpoint definitions
- `app/services/` - Business logic
- `app/database/models/` - Pydantic models
- `app/database/repositories/` - Data access layer
- `app/config/` - Configuration and settings

**Service Pattern:**
```python
# app/services/cv_analyzer.py
class CVAnalyzer:
    async def analyze(self, cv_text: str, jd_text: str) -> AnalysisResult:
        """Analyze CV against job description for ATS scoring."""
        # Implementation
        pass
```

**Repository Pattern:**
```python
# app/database/repositories/resume_repository.py
class ResumeRepository(BaseRepository):
    async def create_resume(self, resume_data: dict) -> str:
        """Create new resume in MongoDB."""
        result = await self.collection.insert_one(resume_data)
        return str(result.inserted_id)
```

### 4.2 Database Guidelines

**MongoDB (Primary):**
- Use Motor async driver
- Collection name: `resumes`, `cover_letters`
- Use ObjectId for document IDs
- Connection: `app/database/connector.py`

**PostgreSQL (Dual-write):**
- Use asyncpg for async operations
- Dual-write alongside MongoDB for structured queries
- Connection: `app/database/connector.py`
- Migration: `scripts/migrate_to_postgres.py`

**NEVER** use raw SQL - use SQLAlchemy or repositories.

### 4.3 Redis Caching Guidelines

**Implementation:** `app/config/redis.py`

**Usage Patterns:**
```python
# Cache AI responses
cache_key = f"ai:{hash(prompt + messages)}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)

# Cache workflow results
cache_key = f"workflow:{hash(cv_text + jd_text)}"
redis.setex(cache_key, 3600, json.dumps(result))

# Use get_redis() singleton pattern
redis = await get_redis()
```

**Target:** >60% cache hit rate, TTL 3600s (1 hour)

### 4.4 AI Integration Guidelines

**Primary Provider:** Cerebras (gpt-oss-120b)
**Fallback:** OpenAI, Groq

**Client:** `app/services/ai_providers.py`

**Cost Tracking:**
- Token usage monitoring enabled
- Endpoint: `/api/comprehensive/cost-tracking`
- Monitor via `scripts/monitor_performance.py`

**AI Response Parsing:**
```python
# app/utils/shared_utils.py
def safe_json_parse(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt repair with JSONParser.repair_json()
        repaired = JSONParser.repair_json(text)
        return json.loads(repaired)
```

### 4.5 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/optimize` | POST | Full CV optimization workflow |
| `/api/v2/analyze` | POST | ATS scoring only |
| `/api/v2/cover-letter` | POST | Cover letter generation |
| `/api/comprehensive/optimize/master` | POST | Master resume optimization |
| `/api/comprehensive/cost-tracking` | GET | AI cost and usage monitoring |
| `/health` | GET | Health check |

### 4.6 Testing Guidelines

**Coverage Gate:** 90%+

**Test Structure:**
```python
# tests/test_services.py
import pytest
from app.services.cv_analyzer import CVAnalyzer

@pytest.fixture
def analyzer():
    return CVAnalyzer()

@pytest.mark.asyncio
async def test_analyze(analyzer):
    result = await analyzer.analyze("CV text", "JD text")
    assert result.ats_score > 0
    assert result.matched_skills is not None
```

**Mock External Dependencies:**
- AI service: Mock HTTP responses
- Database: Use AsyncMock for Motor operations
- Redis: Use fakeredis for testing

---

## 5. Constraints and Rules

### 5.1 NEVER (Prohibited)

| Constraint | Reason |
|------------|--------|
| Direct DB writes without Alembic | Schema changes must be migrations |
| Dependencies >50MB | Keep image size small |
| Blocking I/O in async code | Event loop must remain responsive |
| Raw SQL | Use SQLAlchemy or repositories |
| Production deployments | Development only |
| Hardcoded secrets | Use `.env` variables |
| `print()` statements | Use structured logging |

### 5.2 ALWAYS (Required)

| Requirement | Target |
|-------------|--------|
| Async-first code | <500ms API response |
| Redis caching | >60% hit rate |
| OWASP security practices | Input validation, sanitization |
| ATS compatibility | 98% scoring accuracy |
| Multilingual tests | EN, NL, RU coverage |
| WCAG 2.2 AA | Frontend accessibility |
| TypeScript strict | No `any` types |

### 5.3 Preserve (Do Not Modify)

```bash
# These must always be preserved:
- scripts/run.sh volumes
- n8n_workflows/
- existing API endpoints (maintain backward compatibility)
- CHANGELOG.md structure
```

---

## 6. File Naming Conventions

### 6.1 PDF Export Naming (Critical)

**Format:** `{type}_{initial}.{surname}_{company}_{role}_{date}.pdf`

**Components:**
- `type`: "cv" or "cl" (cover letter)
- `initial`: First letter of first name (lowercase)
- `surname`: Full last name (lowercase)
- `company`: Company name (lowercase, no spaces/special chars)
- `role`: Position title (lowercase, no spaces/special chars)
- `date`: dd.mm.yy format

**Examples:**
```
cv_j.doe_google_software-engineer_19.01.26.pdf
cl_m.smith_amazon_data-scientist_15.03.26.pdf
cv_a.johnson_microsoft_product-manager_01.12.25.pdf
```

**Implementation:**
```python
# app/services/export.py
def generate_filename(
    doc_type: str,  # "cv" or "cl"
    first_name: str,
    last_name: str,
    company: str,
    role: str
) -> str:
    from datetime import datetime
    import re
    
    initial = first_name[0].lower()
    surname = last_name.lower()
    company_slug = re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')
    role_slug = re.sub(r'[^a-z0-9]+', '-', role.lower()).strip('-')
    date = datetime.now().strftime('%d.%m.%y')
    
    return f"{doc_type}_{initial}.{surname}_{company_slug}_{role_slug}_{date}.pdf"
```

### 6.2 Code File Naming

| Type | Convention | Example |
|------|------------|---------|
| Services | verb + noun | `cv_analyzer.py`, `cover_letter_gen.py` |
| Routers | plural nouns | `resume/`, `cover_letter.py` |
| Models | entity names | `resume.py` → `Resume` class |
| Utils | descriptive | `shared_utils.py`, `error_handler.py` |

---

## 7. Performance Targets

### 7.1 API Response Times

| Operation | Target | Cached |
|-----------|--------|--------|
| CV optimization | p95 < 10s | < 3s |
| ATS analysis | p95 < 5s | < 2s |
| Cover letter | p95 < 8s | < 3s |
| Health check | < 100ms | N/A |

### 7.2 Quality Gates

| Metric | Target | Measured By |
|--------|--------|-------------|
| Test coverage | ≥90% | pytest --cov |
| Docker image | <500MB | docker build |
| Frontend bundle | <200KB gzipped | npm run build |
| ATS score | 60-95 (realistic) | AI analysis |
| Keyword match | >70% | Job requirements |
| PDF generation | <3s | Typst compilation |

### 7.3 Cache Performance

**Redis Caching:**
- TTL: 3600s (1 hour)
- Target hit rate: >60%
- Keys:
  - AI responses: `ai:{hash(prompt+messages)}`
  - Workflow results: `workflow:{hash(cv_text+jd_text)}`

---

## 8. Quick Reference

### 8.1 Essential Commands

```bash
# Start development
python scripts/run.sh

# Run tests
./scripts/run.sh test

# Code formatting
black . && ruff check . --fix

# Type checking
mypy . --strict

# Health check
curl http://localhost:8081/health

# View logs
docker-compose logs -f powercv
```

### 8.2 Environment Variables

```env
# Database
MONGODB_URI=mongodb://localhost:27017/powercv
MONGODB_DB=powercv

# Redis
REDIS_URL=redis://localhost:6379

# AI Provider
AI_PROVIDER=cerebras
CEREBRAS_API_KEY=your_key_here
CEREBRAS_MODEL=gpt-oss-120b

# App Settings
DEBUG=True
ENVIRONMENT=development
APP_HOST=0.0.0.0
APP_PORT=8080
AI_SERVICE_URL=http://localhost:8082
```

### 8.3 API Documentation

- **Main API:** http://localhost:8081/docs
- **AI Service:** http://localhost:8082/docs
- **OpenAPI JSON:** http://localhost:8081/openapi.json

### 8.4 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| powercv-api | 8081 | Main API |
| powercv-ai | 8082 | AI Service |
| powercv-mongodb | 27018 | MongoDB |
| powercv-redis | 6379 | Redis |
| powercv-n8n | 5678 | Workflow automation |

---

## Source Documents

This consolidated document combines rules from:

1. `.agent/rules/powercv.md` (2043 lines) - **MASTER**
2. `.cursor/rules/powercv.mdc` (212 lines) - Cursor-specific
3. `.windsurf/rules/powercv.md` (178 lines) - Windsurf-specific
4. `.github/copilot-instructions.md` (380 lines) - Copilot instructions
5. `HANDOVER.md` (263 lines) - Project handoff
6. `CODEBASE_ANALYSIS_REPORT.md` (450+ lines) - Analysis report

**Recommendation:** Use this file (AGENT_CONSOLIDATED_RULES.md) as the single source of truth for agent operations.

---

**Last Updated:** 2026-02-01  
**Next Review:** 2026-03-01
