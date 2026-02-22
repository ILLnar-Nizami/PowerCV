# Deprecated and Unused Dependencies / Code – Investigation Report

Investigation date: 2026-02-22. Summary of deprecated packages, unused dependencies, dead code, and potential bugs.

---

## 1. Main app (`requirements.txt`)

### Unused (safe to remove or move to dev) – DONE

| Package | Notes | Status |
|--------|--------|--------|
| **pandas** | Not imported anywhere in `app/`. | Removed. |
| **mkdocs**, **mkdocs-material** | Not imported in app code. Only needed for building docs. | Moved to `requirements-dev.txt`. |
| **authlib** | No imports found. | Removed. |
| **fastapi-sso** | No imports found. | Removed. |
| **tiktoken** | Not directly imported in `app/`. | Removed. |
| **selenium**, **webdriver-manager** | Only used in `app/tests/selenium/`. | Moved to `requirements-dev.txt`. |
| **python-jose[cryptography]** | Migrated to PyJWT for better security. | **Removed** (2026-02-22). |
| **passlib[bcrypt]** | Security uses **bcrypt** directly. | Removed. |

### Duplicate / redundant – DONE

| Item | Notes | Status |
|------|--------|--------|
| **python-multipart** | Listed twice in `requirements.txt`. | Deduplicated; single entry kept. |
| **pyjwt** | Present alongside **python-jose**. | **Kept** - now the only JWT library. |

### Possible API mismatch (verify)

| Location | Issue |
|----------|-------|
| **app/services/file_validator.py** | Uses `magic.detect_from_content(content)` and error message says "pip install file-magic". **python-magic** (in requirements) exposes `from_buffer(bytes, mime=True)`, not `detect_from_content`. So either: (1) the code was written for the **file-magic** package and requirements are wrong, or (2) python-magic added this API in a newer version. Verify which package is installed and which API is correct; fix requirements or code accordingly. |
| **app/core/validation.py** | Uses `magic.from_buffer(content, mime=True)` (python-magic API). So the app uses two different magic APIs; ensure one consistent package (python-magic or file-magic) and one API style. |

---

## 2. AI service (`ai-service/requirements.txt`)

### Unused (safe to remove – large size impact) – DONE

| Package | Notes | Status |
|--------|--------|--------|
| **sentence-transformers** | Not imported anywhere. Pulls in PyTorch and large ML libs (~2GB+). | Removed. |
| **scikit-learn** | Not imported; only the string `"scikit-learn"` appears as a keyword in prompts. | Removed. |
| **tiktoken** | Not imported in ai-service. | Removed. |
| **langchain**, **langchain-community**, **langchain-openai**, **langchain-ollama** | No direct imports; all AI via **litellm**. | Removed. |

---

## 3. Dead or duplicate code

| Path | Issue | Status |
|------|--------|--------|
| **app/middleware/rate_limit.py** | Never imported; duplicated rate_limiter. | Deleted. |
| **app/services/resume/typst_generator.py** | No longer used (replaced by pdf_engine.py). | Deleted. |

---

## 4. Frontend (`frontend/package.json`)

Spot checks: **zustand**, **sonner**, **class-variance-authority** are used. No obviously unused production deps found in a quick scan. Dev deps (testing-library, vitest, playwright, etc.) are appropriate for dev/test.

---

## 5. Summary

### Completed (2026-02-22)

1. **Security migration**: Migrated from `python-jose` to **PyJWT** in `app/core/security.py`
2. **Docker optimization**: Updated Dockerfile to use uv for faster installs
3. **Dependencies cleanup**: Removed unused packages, organized requirements.txt
4. **Removed dead code**: Deleted `app/middleware/rate_limit.py`, `app/services/resume/typst_generator.py`

---

*Generated from codebase search and import analysis. Last updated 2026-02-22.*
