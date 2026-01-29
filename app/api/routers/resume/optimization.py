"""Resume optimization operations module.

This module provides AI-powered resume optimization, scoring, and cover letter generation
including comprehensive ATS analysis, content optimization, and iterative improvement.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.database.repositories.resume_repository import ResumeRepository
from app.services.master_cv import MasterCV
from app.services.workflow_orchestrator import CVWorkflowOrchestrator

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class OptimizeResumeRequest(BaseModel):
    """Schema for optimizing a resume."""

    job_description: str = Field(
        ..., description="Job description to tailor the resume for"
    )
    target_company: Optional[str] = Field(
        None, description="Target company for which this resume is optimized"
    )
    target_role: Optional[str] = Field(
        None, description="Target position/role for which this resume is optimized"
    )
    email: Optional[str] = Field(
        None, description="Email address to include in the optimized resume"
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="Custom instructions for optimization (e.g., 'emphasize leadership')",
    )


class ScoreResumeRequest(BaseModel):
    """Schema for scoring a resume."""

    job_description: str = Field(..., description="Job description to score against")
    resume_text: str = Field(..., description="Resume text to score")


class CoverLetterRequest(BaseModel):
    """Schema for generating a cover letter."""

    job_description: str = Field(..., description="Job description")
    resume_content: str = Field(..., description="Resume content")
    company_name: Optional[str] = Field(None, description="Company name")
    contact_person: Optional[str] = Field(None, description="Contact person name")
    tone: str = Field(
        "professional",
        description="Tone of the cover letter (professional, casual, etc.)",
    )


class OptimizeResponse(BaseModel):
    """Response model for resume optimization."""

    success: bool = Field(..., description="Whether optimization was successful")
    original_resume: str = Field(..., description="Original resume content")
    optimized_resume: str = Field(..., description="Optimized resume content")
    ats_score: float = Field(..., description="ATS compatibility score")
    original_ats_score: float = Field(
        0.0, description="Original ATS compatibility score"
    )
    improvements: List[str] = Field(..., description="List of improvements made")
    keywords_matched: List[str] = Field(..., description="Keywords that were matched")
    keywords_missing: List[str] = Field(..., description="Keywords that are missing")
    analysis: Dict[str, Any] = Field(..., description="Detailed analysis data")


class ScoreResponse(BaseModel):
    """Response model for resume scoring."""

    ats_score: float = Field(..., description="ATS compatibility score")
    readability_score: float = Field(..., description="Readability score")
    keyword_density: Dict[str, float] = Field(
        ..., description="Keyword density analysis"
    )
    strengths: List[str] = Field(..., description="Identified strengths")
    weaknesses: List[str] = Field(..., description="Identified weaknesses")
    recommendations: List[str] = Field(..., description="Improvement recommendations")


class CoverLetterResponse(BaseModel):
    """Response model for cover letter generation."""

    cover_letter: str = Field(..., description="Generated cover letter")
    word_count: int = Field(..., description="Word count of the cover letter")
    key_points_addressed: List[str] = Field(
        ..., description="Key points from job description addressed"
    )
    personalized_elements: List[str] = Field(
        ..., description="Personalized elements included"
    )


# =============================================================================
# Dependencies
# =============================================================================


async def get_resume_repository(request: Request) -> ResumeRepository:
    """Get resume repository instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        ResumeRepository: Repository instance

    Raises:
        HTTPException: If repository not available
    """
    try:
        return request.app.state.resume_repo
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume repository not available",
        )


async def get_orchestrator() -> CVWorkflowOrchestrator:
    """Get CV workflow orchestrator instance.

    Returns:
        CVWorkflowOrchestrator: Orchestrator instance
    """
    return CVWorkflowOrchestrator()


async def get_master_cv() -> MasterCV:
    """Get MasterCV instance.

    Returns:
        MasterCV: MasterCV instance
    """
    return MasterCV()


# =============================================================================
# Optimization Endpoints
# =============================================================================


async def optimize_resume(
    request: Request,
    resume_id: str,
    optimize_request: OptimizeResumeRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    orchestrator: CVWorkflowOrchestrator = Depends(get_orchestrator),
) -> OptimizeResponse:
    """Optimize a resume for a specific job description.

    Args:
        resume_id: Resume identifier
        request: Optimization request data
        repository: Resume repository instance
        orchestrator: CV workflow orchestrator

    Returns:
        OptimizeResponse: Optimization results

    Raises:
        HTTPException: If optimization fails or resume not found
    """
    try:
        logger.info(f"Starting resume optimization for resume {resume_id}")

        # Get resume from repository
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            object_id = ObjectId(resume_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resume ID format",
            )

        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Perform optimization using workflow orchestrator
        optimization_result = await orchestrator.optimize_cv_for_job(
            cv_text=resume.get("original_content", ""),
            jd_text=optimize_request.job_description,
            generate_cover_letter=False,  # Optimization only
            email=optimize_request.email,
        )

        # Update resume with optimized content
        update_data = {
            "optimized_content": optimization_result.get("optimized_cv", ""),
            "job_description": optimize_request.job_description,
            "ats_score": optimization_result.get("ats_score", 0.0),
            "original_ats_score": optimization_result.get("original_ats_score", 0.0),
            "keywords_matched": optimization_result.get("matched_keywords", []),
            "status": "optimized",
            "updated_at": datetime.utcnow(),
        }

        await repository.update(object_id, update_data)

        logger.info(f"Resume {resume_id} optimized successfully")

        return OptimizeResponse(
            success=True,
            original_resume=resume.get("original_content", ""),
            optimized_resume=str(optimization_result.get("optimized_cv", "")),
            ats_score=optimization_result.get("ats_score", 0.0),
            original_ats_score=optimization_result.get("original_ats_score", 0.0),
            improvements=optimization_result.get("improvements", []),
            keywords_matched=optimization_result.get("matched_keywords", []),
            keywords_missing=optimization_result.get("missing_keywords", []),
            analysis=optimization_result.get("analysis", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize resume: {str(e)}",
        )


async def score_resume(
    request: Request,
    resume_id: str,
    score_request: ScoreResumeRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    master_cv: MasterCV = Depends(get_master_cv),
) -> ScoreResponse:
    """Score a resume against a job description.

    Args:
        resume_id: Resume identifier
        request: Scoring request data
        repository: Resume repository instance
        master_cv: MasterCV instance for scoring

    Returns:
        ScoreResponse: Scoring results

    Raises:
        HTTPException: If scoring fails or resume not found
    """
    try:
        logger.info(f"Starting resume scoring for resume {resume_id}")

        # Get resume from repository
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            object_id = ObjectId(resume_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resume ID format",
            )

        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Use resume content if no specific resume_text provided
        resume_text = score_request.resume_text or resume.get("original_content", "")

        # Perform scoring using master CV scoring system
        scoring_result = await master_cv.score_resume(
            resume_text=resume_text,
            job_description=score_request.job_description,
        )

        logger.info(f"Resume {resume_id} scored successfully")

        return ScoreResponse(
            ats_score=scoring_result.get("ats_score", 0.0),
            readability_score=scoring_result.get("readability_score", 0.0),
            keyword_density=scoring_result.get("keyword_density", {}),
            strengths=scoring_result.get("strengths", []),
            weaknesses=scoring_result.get("weaknesses", []),
            recommendations=scoring_result.get("recommendations", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to score resume: {str(e)}",
        )


async def generate_cover_letter(
    request: Request,
    resume_id: str,
    cover_request: CoverLetterRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    orchestrator: CVWorkflowOrchestrator = Depends(get_orchestrator),
) -> CoverLetterResponse:
    """Generate a cover letter for a resume and job description.

    Args:
        resume_id: Resume identifier
        request: Cover letter request data
        repository: Resume repository instance
        orchestrator: CV workflow orchestrator

    Returns:
        CoverLetterResponse: Generated cover letter

    Raises:
        HTTPException: If generation fails or resume not found
    """
    try:
        logger.info(f"Starting cover letter generation for resume {resume_id}")

        # Get resume from repository
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            object_id = ObjectId(resume_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resume ID format",
            )

        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Use resume content if no specific resume_content provided
        resume_content = cover_request.resume_content or resume.get(
            "original_content", ""
        )

        # Generate cover letter using workflow orchestrator
        cover_letter_result = await orchestrator.optimize_cv_for_job(
            cv_text=resume_content,
            jd_text=cover_request.job_description,
            generate_cover_letter=True,
        )

        cover_letter_text = cover_letter_result.get("cover_letter", "")

        # Count words in cover letter
        word_count = len(cover_letter_text.split())

        logger.info(f"Cover letter generated successfully for resume {resume_id}")

        return CoverLetterResponse(
            cover_letter=cover_letter_text,
            word_count=word_count,
            key_points_addressed=cover_letter_result.get("key_points", []),
            personalized_elements=cover_letter_result.get("personalized_elements", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating cover letter for resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cover letter: {str(e)}",
        )


# =============================================================================
# Router Configuration
# =============================================================================


# Create router for optimization operations
router = APIRouter(
    prefix="/optimization",
    tags=["Resume Optimization"],
    responses={404: {"description": "Not found"}},
)

# Register endpoints
router.add_api_route(
    "/{resume_id}",
    optimize_resume,
    methods=["POST"],
    response_model=OptimizeResponse,
)

router.add_api_route(
    "/{resume_id}/score",
    score_resume,
    methods=["POST"],
    response_model=ScoreResponse,
)

router.add_api_route(
    "/{resume_id}/cover-letter",
    generate_cover_letter,
    methods=["POST"],
    response_model=CoverLetterResponse,
)

logger.info("Resume optimization router initialized")
