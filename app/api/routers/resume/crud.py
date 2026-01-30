"""CRUD operations for resume management.

This module provides Create, Read, Update, Delete operations for resume entities
including validation, repository access, and proper error handling.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.database.repositories.resume_repository import ResumeRepository
from app.services.file_validator import SecureFileValidator
from app.services.resume.typst_generator import TypstGenerator

logger = logging.getLogger(__name__)

# Supported file extensions for resume uploads
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".md", ".markdown"]


# =============================================================================
# Pydantic Models
# =============================================================================


class CreateResumeRequest(BaseModel):
    """Schema for creating a new resume."""

    user_id: str = Field(..., description="Unique identifier for the user")
    title: str = Field(..., description="Title of the resume")
    original_content: str = Field(..., description="Original content of the resume")
    job_description: str = Field(
        ..., description="Job description to tailor the resume for"
    )


class UpdateResumeRequest(BaseModel):
    """Schema for updating an existing resume."""

    title: Optional[str] = Field(None, description="Updated title of the resume")
    content: Optional[str] = Field(None, description="Updated content of the resume")
    job_description: Optional[str] = Field(None, description="Updated job description")


class ResumeResponse(BaseModel):
    """Response model for resume data."""

    id: str = Field(..., description="Resume ID")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Resume title")
    original_content: str = Field(..., description="Original resume content")
    optimized_content: Optional[str] = Field(
        None, description="Optimized resume content"
    )
    job_description: str = Field(..., description="Job description")
    status: str = Field(..., description="Resume status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    file_path: Optional[str] = Field(None, description="Path to uploaded file")
    ats_score: Optional[float] = Field(None, description="ATS compatibility score")
    keywords_matched: Optional[List[str]] = Field(None, description="Matched keywords")


# =============================================================================
# Helper Functions
# =============================================================================


def validate_object_id(object_id: str) -> ObjectId:
    """Validate and convert string to ObjectId.

    Args:
        object_id: String representation of ObjectId

    Returns:
        ObjectId: Validated ObjectId instance

    Raises:
        HTTPException: If the object_id is invalid
    """
    try:
        return ObjectId(object_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
        )


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


async def get_file_validator() -> SecureFileValidator:
    """Get secure file validator instance.

    Returns:
        SecureFileValidator: File validator instance
    """
    return SecureFileValidator()


# =============================================================================
# CRUD Endpoints
# =============================================================================


async def create_resume(
    request: CreateResumeRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    file_validator: SecureFileValidator = Depends(get_file_validator),
) -> ResumeResponse:
    """Create a new resume record.

    Args:
        request: Resume creation data
        repository: Resume repository instance
        file_validator: File validation service

    Returns:
        ResumeResponse: Created resume data

    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(f"Creating resume for user {request.user_id}")

        # Create resume document
        resume_data = {
            "user_id": request.user_id,
            "title": request.title,
            "original_content": request.original_content,
            "job_description": request.job_description,
            "status": "created",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Insert into database
        resume_id = await repository.create(resume_data)

        logger.info(f"Resume created successfully: {resume_id}")

        # Return created resume
        # Return created resume
        created_resume = await repository.get_by_id(resume_id)
        if not created_resume:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created resume"
            )

        # Ensure proper ID handling
        c_resume_id = (
            str(created_resume.get("_id", ""))
            if "_id" in created_resume
            else str(created_resume.get("id", ""))
        )

        return ResumeResponse(
            id=c_resume_id,
            user_id=created_resume.get("user_id", ""),
            title=created_resume.get("title", "Untitled"),
            original_content=created_resume.get("original_content", ""),
            job_description=created_resume.get("job_description", ""),
            status=created_resume.get("status") or "created",
            created_at=created_resume.get("created_at") or datetime.utcnow(),
            updated_at=created_resume.get("updated_at") or datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error creating resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resume: {str(e)}",
        )


async def get_resume(
    resume_id: str,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeResponse:
    """Get a specific resume by ID.

    Args:
        resume_id: Resume identifier
        repository: Resume repository instance

    Returns:
        ResumeResponse: Resume data

    Raises:
        HTTPException: If resume not found
    """
    try:
        # Validate and convert ID
        object_id = validate_object_id(resume_id)

        # Retrieve resume
        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Ensure proper ID handling
        c_resume_id = (
            str(resume.get("_id", "")) if "_id" in resume else str(resume.get("id", ""))
        )

        return ResumeResponse(
            id=c_resume_id,
            user_id=resume.get("user_id", ""),
            title=resume.get("title", "Untitled"),
            original_content=resume.get("original_content", ""),
            optimized_content=resume.get("optimized_content"),
            job_description=resume.get("job_description", ""),
            status=resume.get("status") or "created",
            created_at=resume.get("created_at") or datetime.utcnow(),
            updated_at=resume.get("updated_at") or datetime.utcnow(),
            file_path=resume.get("file_path"),
            ats_score=resume.get("ats_score"),
            keywords_matched=resume.get("keywords_matched"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume",
        )


async def get_user_resumes(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of resumes to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of resumes to return"
    ),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> List[ResumeResponse]:
    """Get all resumes for a specific user.

    Args:
        user_id: User identifier
        skip: Number of items to skip
        limit: Maximum number of items to return
        repository: Resume repository instance

    Returns:
        List[ResumeResponse]: List of user's resumes

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Retrieving resumes for user {user_id}")

        # Get resumes from repository
        resumes = await repository.get_by_user_id(
            user_id=user_id, skip=skip, limit=limit
        )

        # Convert to response format
        response_list = []
        for resume in resumes:
            # Ensure proper ID handling
            resume_id = (
                str(resume.get("_id", ""))
                if "_id" in resume
                else str(resume.get("id", ""))
            )

            response_list.append(
                ResumeResponse(
                    id=resume_id,
                    user_id=resume.get("user_id", ""),
                    title=resume.get("title", "Untitled"),
                    original_content=resume.get("original_content", ""),
                    optimized_content=resume.get("optimized_content"),
                    job_description=resume.get("job_description", ""),
                    status=resume.get("status") or "created",
                    created_at=resume.get("created_at") or datetime.utcnow(),
                    updated_at=resume.get("updated_at") or datetime.utcnow(),
                    file_path=resume.get("file_path"),
                    ats_score=resume.get("ats_score"),
                    keywords_matched=resume.get("keywords_matched"),
                )
            )

        logger.info(f"Retrieved {len(response_list)} resumes for user {user_id}")
        return response_list

    except Exception as e:
        logger.error(f"Error retrieving user resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes",
        )


async def update_resume(
    resume_id: str,
    request: UpdateResumeRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeResponse:
    """Update an existing resume.

    Args:
        resume_id: Resume identifier
        request: Update data
        repository: Resume repository instance

    Returns:
        ResumeResponse: Updated resume data

    Raises:
        HTTPException: If update fails or resume not found
    """
    try:
        # Validate and convert ID
        object_id = validate_object_id(resume_id)

        # Check if resume exists
        existing_resume = await repository.get_by_id(object_id)
        if not existing_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}

        if request.title is not None:
            update_data["title"] = request.title
        if request.content is not None:
            update_data["original_content"] = request.content
        if request.job_description is not None:
            update_data["job_description"] = request.job_description

        # Perform update
        updated_resume = await repository.update(object_id, update_data)

        if not updated_resume:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update resume",
            )

        logger.info(f"Resume {resume_id} updated successfully")

        # Ensure proper ID handling
        c_resume_id = (
            str(updated_resume.get("_id", ""))
            if "_id" in updated_resume
            else str(updated_resume.get("id", ""))
        )

        return ResumeResponse(
            id=c_resume_id,
            user_id=updated_resume.get("user_id", ""),
            title=updated_resume.get("title", "Untitled"),
            original_content=updated_resume.get("original_content", ""),
            optimized_content=updated_resume.get("optimized_content"),
            job_description=updated_resume.get("job_description", ""),
            status=updated_resume.get("status") or "created",
            created_at=updated_resume.get("created_at") or datetime.utcnow(),
            updated_at=updated_resume.get("updated_at") or datetime.utcnow(),
            file_path=updated_resume.get("file_path"),
            ats_score=updated_resume.get("ats_score"),
            keywords_matched=updated_resume.get("keywords_matched"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resume",
        )


async def delete_resume(
    resume_id: str,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> Dict[str, str]:
    """Delete a resume.

    Args:
        resume_id: Resume identifier
        repository: Resume repository instance

    Returns:
        Dict[str, str]: Success message

    Raises:
        HTTPException: If deletion fails or resume not found
    """
    try:
        # Validate and convert ID
        object_id = validate_object_id(resume_id)

        # Check if resume exists
        existing_resume = await repository.get_by_id(object_id)
        if not existing_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Delete from database
        success = await repository.delete(object_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete resume",
            )

        # Clean up associated files if any
        if existing_resume.file_path:
            try:
                import os

                if os.path.exists(existing_resume.file_path):
                    os.remove(existing_resume.file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to clean up file {existing_resume.file_path}: {e}"
                )

        logger.info(f"Resume {resume_id} deleted successfully")

        return {"message": "Resume deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume",
        )


async def download_resume_pdf(
    request: Request,
    resume_id: str,
    template: str = Query(
        "modern.typ", description="Template to use for PDF generation"
    ),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> FileResponse:
    """Download a resume as PDF using specified template.

    Args:
        resume_id: Resume identifier
        template: Template filename (e.g., 'modern.typ', 'resume.typ')
        repository: Resume repository instance

    Returns:
        FileResponse: PDF file download

    Raises:
        HTTPException: If resume not found or generation fails
    """
    try:
        logger.info(f"Downloading resume {resume_id} with template {template}")

        # Validate and convert ID
        object_id = validate_object_id(resume_id)

        # Retrieve resume
        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Get optimized data for PDF generation
        optimized_data = resume.get("optimized_data")
        if not optimized_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume has not been optimized yet. Please optimize first.",
            )

        # Initialize Typst generator
        generator = TypstGenerator()

        # Load the optimized data into the generator
        if isinstance(optimized_data, str):
            generator.parse_json_from_string(optimized_data)
        else:
            generator.json_data = optimized_data

        # Create temp file for PDF output
        temp_dir = tempfile.gettempdir()
        title = resume.get("title", "resume").replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{title}_{timestamp}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)

        # Generate PDF
        success = generator.generate_pdf(template, pdf_path)
        if not success or not os.path.exists(pdf_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate PDF. Check server logs for details.",
            )

        logger.info(f"Resume {resume_id} downloaded as PDF: {pdf_filename}")

        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type="application/pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download resume: {str(e)}",
        )


# =============================================================================
# Router Configuration
# =============================================================================

# Create router for CRUD operations
router = APIRouter(
    prefix="",
    tags=["Resume CRUD"],
    responses={404: {"description": "Not found"}},
)

# Register endpoints
router.add_api_route(
    "/",
    create_resume,
    methods=["POST"],
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)

router.add_api_route(
    "/{resume_id}",
    get_resume,
    methods=["GET"],
    response_model=ResumeResponse,
)

router.add_api_route(
    "/user/{user_id}",
    get_user_resumes,
    methods=["GET"],
    response_model=List[ResumeResponse],
)

router.add_api_route(
    "/{resume_id}",
    update_resume,
    methods=["PUT"],
    response_model=ResumeResponse,
)

router.add_api_route(
    "/{resume_id}",
    delete_resume,
    methods=["DELETE"],
    responses={200: {"description": "Success"}},
)

router.add_api_route(
    "/{resume_id}/download",
    download_resume_pdf,
    methods=["GET"],
    responses={200: {"description": "PDF file download"}},
)

logger.info("Resume CRUD router initialized")
