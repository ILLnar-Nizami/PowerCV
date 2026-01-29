"""Main application entry point for PowerCV.

This module initializes the FastAPI application, configures routers, middleware,
and handles application startup and shutdown events. It serves as the central
coordination point for the entire application.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import sentry_sdk
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add parser router import comprehensive_router
from app.api.routers import comprehensive_optimizer, parser
from app.api.routers.cover_letter import cover_letter_router
from app.api.routers.resume.crud import ResumeRepository
from app.api.routers.resume.router import resume_router
from app.api.routers.token_usage import router as token_usage_router

# Import the old resume router from resume.py
from app.config.logging_config import logger
from app.config.settings import get_settings
from app.config.templates import TemplateConfig
from app.database.connector import MongoConnectionManager
from app.database.models.resume import Resume
from app.middleware.debugging import setup_debugging_middleware
from app.routes.n8n_integration import router as n8n_router
from app.services.ai_client import analyze_cv, generate_cover_letter, optimize_cv
from app.services.workflow_orchestrator import CVWorkflowOrchestrator
from app.utils.error_handler import ErrorContext, ErrorHandler, debug_endpoint

# Load environment variables from .env file
load_dotenv(override=True)


# Initialize Jinja2 templates for HTML rendering
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Initialize orchestrator
orchestrator = CVWorkflowOrchestrator()

# Configure secure logging and settings


# Request models
class OptimizationRequest(BaseModel):
    cv_text: str = Field(
        ..., min_length=100, max_length=25000, description="CV text to optimize"
    )
    jd_text: str = Field(
        ..., min_length=50, max_length=15000, description="Job description text"
    )
    generate_cover_letter: bool = Field(
        default=True, description="Whether to generate cover letter"
    )
    template: str = Field(
        default="resume.typ",
        pattern=TemplateConfig.get_template_pattern(),
        description=f"Template to use for CV generation ({', '.join(TemplateConfig.get_valid_templates())})",
    )
    email: Optional[str] = Field(
        default=None, description="Candidate email for the optimized CV"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cv_text": "John Doe\nSenior Software Engineer...",
                "jd_text": "We are looking for a Senior Software Engineer...",
                "generate_cover_letter": True,
                "template": "resume.typ",
                "email": "john@example.com",
            }
        }
    )


class CoverLetterRequest(BaseModel):
    candidate_data: dict = Field(..., description="Candidate information")
    job_data: dict = Field(..., description="Job information")

    tone: str = Field(
        default="Professional",
        pattern="^(Professional|Enthusiastic|Formal|Casual)$",
        description="Tone for cover letter",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "candidate_data": {
                    "name": "John Doe",
                    "current_title": "Software Engineer",
                    "top_skills": ["Python", "JavaScript"],
                },
                "job_data": {"company": "TechCorp", "position": "Senior Developer"},
                "tone": "Professional",
            }
        }
    )

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v):
        valid_tones = ["Professional", "Enthusiastic", "Formal", "Casual"]
        if v not in valid_tones:
            raise ValueError(f"tone must be one of: {valid_tones}")
        return v


class OptimizationResponse(BaseModel):
    """Response model for resume optimization."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"analysis": {}, "optimized_cv": {}, "ats_score": 85},
                "message": "Resume optimization completed successfully",
            }
        }
    )


async def startup_logic(app: FastAPI) -> None:
    """Execute startup logic for the FastAPI application.

    Initialize database connections, Sentry, and other resources needed by the application.

    Args:
        app: The FastAPI application instance

    Raises:
    ------
        Exception: If any startup operation fails
    """
    # Initialize Sentry
    settings = get_settings()
    if settings.sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[
                    StarletteIntegration(),
                    FastApiIntegration(),
                ],
                traces_sample_rate=1.0,
                environment="production" if not settings.debug else "development",
            )
            logger.info("Sentry initialized")
        except Exception as e:
            logger.warning(f"Sentry initialization failed: {e}")

    try:
        connection_manager = MongoConnectionManager.get_instance()
        app.state.mongo = connection_manager

        # Initialize repositories
        app.state.resume_repo = ResumeRepository()
        logger.info("Resume repository initialized")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


async def shutdown_logic(app: FastAPI) -> None:
    """Execute shutdown logic for the FastAPI application.

    Closes database connections and cleans up resources.

    Args:
        app: The FastAPI application instance
    """
    try:
        await app.state.mongo.close_all()
        logger.info("Successfully closed all database connections")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Shutting down background tasks.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup and shutdown."""
    # Startup logic
    await startup_logic(app)
    yield
    # Shutdown logic
    await shutdown_logic(app)


app = FastAPI(
    title="PowerCV API",
    summary="",
    description="""
    PowerCV is a resume generation system that adapts resumes to specific job descriptions.
    It leverages AI to provide customized resume content based on user input.
    """,
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    version="2.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# Rate limiting disabled - Cerebras has generous limits (30 req/min, 900/hour)
# init_rate_limiting(app)

# Setup debugging middleware
settings = get_settings()
setup_debugging_middleware(app, enable_debug=settings.debug)


# DEPRECATED: @app.on_event("startup") is deprecated in FastAPI 0.100+
# Replaced with lifespan context manager below
# @app.on_event("startup")
# async def startup_event():
#     """Handle application startup and configuration validation."""
#     # Startup logic moved to lifespan context manager


# Global exception handler for security
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that doesn't expose sensitive information.

    Args:
        request: The incoming request
        exc: The exception that was raised

    Returns:
        JSON response with sanitized error
    """
    # Log the full error securely (sensitive data is filtered by SensitiveDataFilter)
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}")

    # NEVER expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": (
                "An unexpected error occurred. Please contact support if this persists."
            ),
        },
    )


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom exception handler for HTTP exceptions.

    Renders the 404.html template for 404 errors.
    For other HTTP errors, renders a basic error page or returns JSON for API routes.

    Args:
        request: The incoming request
        exc: The HTTP exception that was raised

    Returns:
    -------
        An appropriate response based on the request type and error
    """
    if exc.status_code == 404:
        # Check if this is an API request or a web page request
        if request.url.path.startswith("/api"):
            return JSONResponse(
                status_code=404, content={"detail": "Resource not found"}
            )
        # For web requests, render our custom 404 page
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    # For API routes, return JSON error
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": str(exc.detail)}
        )

    # For other errors on web routes, show a simple error page
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "status_code": exc.status_code, "detail": str(exc.detail)},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom exception handler for request validation errors.

    Args:
        request: The incoming request
        exc: The validation error that was raised

    Returns:
    -------
        JSON response for API routes or template response for web routes
    """
    # Log validation errors securely (don't expose sensitive input data)
    logger.warning(
        f"Validation error on {request.url.path}: {len(exc.errors())} errors"
    )

    # Log detailed validation errors for debugging (but don't expose to client)
    for error in exc.errors():
        field_path = ".".join(str(x) for x in error["loc"])
        logger.warning(f"Validation error in {field_path}: {error['msg']}")

    # For API routes, return sanitized error
    if request.url.path.startswith("/api"):
        # Don't expose detailed validation errors that might contain sensitive data
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid input data. Please check your request."},
        )

    # For web routes, show an error page with validation details
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "status_code": 422,
            "detail": "Validation Error: Please check your input data.",
        },
        status_code=422,
    )


@app.middleware("http")
async def add_response_headers(request: Request, call_next):
    """Middleware to add response headers and handle flashed messages.

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
    -------
        The response with added security headers
    """
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response


# Add middleware and static file mounts
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount(
    "/templates",
    StaticFiles(directory=str(Path(__file__).parent / "templates")),
    name="templates",
)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)


@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    """Health check endpoint for monitoring and container orchestration.

    Returns:
    -------
        JSONResponse: Status information about the application.
    """
    return JSONResponse(
        content={"status": "healthy", "version": app.version, "service": "PowerCV"}
    )


# Cerebras v2 endpoints
_orchestrator = None


def get_orchestrator():
    """Get or create a singleton instance of the workflow orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        logger.info("Initializing CVWorkflowOrchestrator singleton")
        _orchestrator = CVWorkflowOrchestrator()
    return _orchestrator


async def get_resume_repository(request: Request) -> ResumeRepository:
    """Dependency for getting the resume repository instance.

    Args:
        request: The incoming request

    Returns:
    -------
        ResumeRepository: An instance of the resume repository
    """
    from app.database.repositories.resume_repository import ResumeRepository

    return ResumeRepository()


@app.post(
    "/api/v2/optimize",
    tags=["CV Optimization v2"],
    summary="Complete CV optimization workflow",
)
@debug_endpoint
async def optimize_cv_v2(
    request: OptimizationRequest,
    repo: ResumeRepository = Depends(get_resume_repository),
):
    """CV optimization endpoint utilizing modular prompts.
    Saves the optimized result and returns a resume ID for download.
    """
    try:
        with ErrorContext(
            "cv_optimization_v2",
            {
                "template": request.template,
                "generate_cover_letter": request.generate_cover_letter,
                "cv_length": len(request.cv_text),
                "jd_length": len(request.jd_text),
            },
        ):
            result = await optimize_cv(
                cv_text=request.cv_text,
                jd_text=request.jd_text,
                email=request.email,
            )

            optimized_data = result.get("optimized_cv", {})
            ats_score = result.get("ats_score", 0)
            original_ats_score = result.get("original_ats_score", 0)

            resume_id = None
            if optimized_data:
                try:
                    resume_data = Resume(
                        user_id="local-user",
                        title=f"Optimized Resume - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        original_content=request.cv_text,
                        job_description=request.jd_text,
                        optimized_data=optimized_data,
                        target_company="",
                        target_role="",
                        matching_score=ats_score,
                        matching_skills=[],
                        missing_skills=[],
                        recommendation=f"Improved ATS score from {original_ats_score} to {ats_score}",
                    )

                    resume_id = await repo.create_resume(resume_data)
                    if resume_id:
                        result["resume_id"] = resume_id
                        logger.info(f"Created optimized resume with ID: {resume_id}")
                except Exception as save_error:
                    logger.warning(
                        f"Failed to save optimized resume to DB: {save_error}"
                    )
                    result["resume_id"] = None
                    result["save_warning"] = (
                        "Resume optimized but could not be saved to database"
                    )

            return result
    except Exception as e:
        logger.error(f"Optimization error: {str(e)}", exc_info=True)
        raise ErrorHandler.handle_ai_api_error(
            e,
            provider="workflow_orchestrator",
            operation="cv_optimization",
            context={"template": request.template},
        )


@app.post(
    "/api/v2/analyze",
    tags=["CV Analysis v2"],
    summary="Analyze CV against job description",
)
@debug_endpoint
async def analyze_cv_v2(request: OptimizationRequest):
    """Analyze CV without optimization.
    Returns ATS score, keyword analysis, and recommendations.
    """
    try:
        with ErrorContext(
            "cv_analysis_v2",
            {"cv_length": len(request.cv_text), "jd_length": len(request.jd_text)},
        ):
            analysis = await analyze_cv(request.cv_text, request.jd_text)
            return analysis
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise ErrorHandler.handle_ai_api_error(
            e,
            provider="cv_analyzer",
            operation="cv_analysis",
            context={"cv_length": len(request.cv_text)},
        )


@app.post(
    "/api/v2/cover-letter", tags=["Cover Letter v2"], summary="Generate cover letter"
)
@debug_endpoint
async def generate_cover_letter_v2(request: CoverLetterRequest):
    """Generate cover letter based on candidate and job data."""
    try:
        with ErrorContext(
            "cover_letter_generation_v2",
            {
                "tone": request.tone,
                "candidate_name": request.candidate_data.get("name", "Unknown"),
                "company": request.job_data.get("company", "Unknown"),
            },
        ):
            result = await generate_cover_letter(
                request.candidate_data, request.job_data, request.tone
            )
            return result
    except Exception as e:
        logger.error(f"Cover letter generation error: {str(e)}", exc_info=True)
        raise ErrorHandler.handle_ai_api_error(
            e,
            provider="cover_letter_generator",
            operation="cover_letter_generation",
            context={"tone": request.tone},
        )


# Automation endpoints


@app.post(
    "/api/v1/scrape", tags=["Scraping"], summary="Scrape job description from URL"
)
async def scrape_job_description(
    url: str = Body(..., description="URL to job posting"),
):
    """Scrape job description from a LinkedIn, Indeed, or other job board URL.

    Returns extracted job title, company, location, and full description.
    """
    try:
        from app.utils.shared_utils import ValidationHelper

        # Validate URL
        validated_url = ValidationHelper.validate_url(url)

        from app.services.scraper import fetch_job_description

        result = await fetch_job_description(validated_url)
        return result

    except ValueError as e:
        logger.error(f"URL validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to scrape job description: {str(e)}"
        )


# Include routers - These must come BEFORE the catch-all route
app.include_router(resume_router)

app.include_router(cover_letter_router)
# Add token usage tracking API endpoints
app.include_router(token_usage_router)
# Add comprehensive optimizer API endpoints
app.include_router(comprehensive_optimizer.comprehensive_router)
app.include_router(parser.router)  # Register parser router
# Add n8n integration endpoints
app.include_router(n8n_router)


# Legacy endpoint for frontend compatibility - /api/resume/{id}
# This handles both master CVs and regular resumes
@app.get("/api/resume/{resume_id}")
async def legacy_resume_endpoint(resume_id: str, request: Request):
    """Legacy endpoint for frontend compatibility - supports both master CVs and regular resumes."""
    from bson.objectid import ObjectId
    from fastapi import HTTPException

    try:
        repo = request.app.state.resume_repo
        object_id = ObjectId(resume_id)

        # Try to get from database
        doc = await repo.get_by_id(object_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Check document type
        doc_type = doc.get("document_type", "")

        if doc_type == "master_cv":
            # Return master CV format for preview
            return {
                "id": str(doc["_id"]),
                "title": doc.get("title", "Untitled"),
                "original_content": doc.get("content", ""),
                "optimized_content": None,
                "target_company": doc.get("target_company", ""),
                "target_role": doc.get("target_role", ""),
                "matching_score": doc.get("matching_score"),
            }
        else:
            # Regular resume
            return {
                "id": str(doc["_id"]),
                "title": doc.get("title", "Untitled"),
                "original_content": doc.get("original_content", ""),
                "optimized_content": doc.get("optimized_content") or "",
                "target_company": doc.get("target_company", ""),
                "target_role": doc.get("target_role", ""),
                "matching_score": doc.get("matching_score"),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in legacy resume endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoint for PDF download - /api/resume/{id}/download
@app.get("/api/resume/{resume_id}/download")
async def legacy_download_endpoint(
    resume_id: str,
    request: Request,
    template: str = Query("modern.typ", description="Template to use"),
):
    """Legacy endpoint for PDF download - redirects to the actual download handler."""
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse

    try:
        # Validate resume exists
        from bson.objectid import ObjectId

        repo = request.app.state.resume_repo
        object_id = ObjectId(resume_id)
        doc = await repo.get_by_id(object_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Check if resume has optimized data
        optimized_data = doc.get("optimized_data")
        if not optimized_data:
            raise HTTPException(
                status_code=400,
                detail="Resume has not been optimized yet. Please optimize first.",
            )

        # Redirect to actual download endpoint
        return RedirectResponse(
            url=f"/api/v1/resumes/{resume_id}/download?template={template}",
            status_code=301,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in legacy download endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Test endpoint for Sentry error tracking
@app.get("/test-sentry-error", include_in_schema=False)
async def test_sentry_error():
    """Test endpoint to trigger a sample error for Sentry validation."""
    try:
        # Simulate an error
        raise ValueError("This is a test error for Sentry integration.")
    except Exception as e:
        logger.error(f"Test error for Sentry: {e}")
        raise


# Catch-all for not found pages - IMPORTANT: This must come AFTER including all routers
@app.get("/{path:path}", include_in_schema=False)
async def catch_all(request: Request, path: str):
    """Catch-all route handler for undefined paths.

    Backend is API-only; frontend is served by Vite dev server.

    Args:
        request: The incoming request
        path: The path that was not matched by any other route

    Returns:
    -------
        JSON 404 response
    """
    return JSONResponse(
        status_code=404,
        content={"detail": f"Path '/{path}' not found. API endpoints are under /api/"},
    )
