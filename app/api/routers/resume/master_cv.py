"""Master CV operations module.

This module provides endpoints for managing Master CV templates and operations
including upload, retrieval, replacement, and testing of master CVs.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     Request, UploadFile, status)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.database.repositories.resume_repository import ResumeRepository
from app.services.file_validator import (SecureFileValidator,
                                         store_file_securely)
from app.services.resume.universal_scorer import UniversalResumeScorer
from app.utils.file_handling import extract_text_from_file

logger = logging.getLogger(__name__)

# Supported file extensions for master CV uploads
MASTER_CV_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".md", ".markdown"]


# =============================================================================
# Pydantic Models
# =============================================================================


class MasterCVRequest(BaseModel):
    """Schema for Master CV operations."""

    user_id: str = Field(..., description="Unique identifier for the user")
    title: str = Field(..., description="Title of the master CV")
    description: Optional[str] = Field(None, description="Description of the master CV")
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing the master CV"
    )


class MasterCVResponse(BaseModel):
    """Response model for Master CV data."""

    id: str = Field(..., description="Master CV ID")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Master CV title")
    description: Optional[str] = Field(None, description="Master CV description")
    content: str = Field(..., description="Master CV content")
    file_path: Optional[str] = Field(None, description="Path to uploaded file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File type")
    tags: Optional[List[str]] = Field(None, description="Tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Whether this is the active master CV")
    usage_count: int = Field(0, description="Number of times used")


class MasterCVTestRequest(BaseModel):
    """Schema for testing Master CV."""

    job_description: str = Field(..., description="Job description to test against")
    target_role: Optional[str] = Field(None, description="Target role for testing")
    target_company: Optional[str] = Field(
        None, description="Target company for testing"
    )


class MasterCVTestResponse(BaseModel):
    """Response model for Master CV testing."""

    success: bool = Field(..., description="Whether test was successful")
    ats_score: float = Field(..., description="ATS compatibility score")
    readability_score: float = Field(..., description="Readability score")
    strengths: List[str] = Field(..., description="Identified strengths")
    weaknesses: List[str] = Field(..., description="Identified weaknesses")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    keyword_analysis: Dict[str, Any] = Field(
        ..., description="Keyword analysis results"
    )
    optimized_sections: Dict[str, str] = Field(
        ..., description="Optimized sections for the job"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def validate_object_id(object_id: str) -> ObjectId:
    """Validate and convert string to ObjectId."""
    try:
        return ObjectId(object_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
        )


def validate_master_cv_file(file: UploadFile) -> None:
    """Validate uploaded master CV file."""
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in MASTER_CV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported types: {', '.join(MASTER_CV_EXTENSIONS)}",
        )
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 10MB.",
        )


async def get_resume_repository(request: Request) -> ResumeRepository:
    """Get resume repository instance from app state."""
    try:
        return request.app.state.resume_repo
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume repository not available",
        )


async def get_file_validator() -> SecureFileValidator:
    """Get secure file validator instance."""
    return SecureFileValidator()


# =============================================================================
# Master CV Endpoints
# =============================================================================


async def upload_master_cv(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(lambda request: request.state.user),
    user_id: str = Form(..., description="User ID"),
    title: str = Form(..., description="Master CV title"),
    description: Optional[str] = Form(None, description="Master CV description"),
    tags: Optional[str] = Form(None, description="Tags (comma-separated)"),
    repository: ResumeRepository = Depends(get_resume_repository),
    file_validator: SecureFileValidator = Depends(get_file_validator),
) -> MasterCVResponse:
    """Upload a new Master CV."""
    try:
        logger.info(f"Uploading master CV for user {user_id}")
        validate_master_cv_file(file)
        content = await file.read()
        _, safe_filename, _ = await file_validator.validate_upload(file)
        file_path = store_file_securely(content, safe_filename, user_id)

        file_extension = Path(file.filename).suffix.lower() or ".txt"
        content = extract_text_from_file(str(file_path), file_extension)

        tag_list = (
            [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None
        )

        master_cv_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "content": content,
            "document_type": "master_cv",
            "file_path": str(file_path),
            "file_size": file.size,
            "file_type": file.content_type,
            "tags": tag_list,
            "is_active": False,
            "usage_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        master_cv_id = await repository.create(master_cv_data)
        logger.info(f"Master CV uploaded successfully: {master_cv_id}")

        return MasterCVResponse(
            id=str(master_cv_id),
            user_id=user_id,
            title=title,
            description=description,
            content=content,
            file_path=str(file_path),
            file_size=file.size,
            file_type=file.content_type,
            tags=tag_list,
            created_at=master_cv_data["created_at"],
            updated_at=master_cv_data["updated_at"],
            is_active=False,
            usage_count=0,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading master CV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload master CV: {str(e)}",
        )


async def get_master_cvs(
    request: Request,
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of master CVs to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of master CVs to return"
    ),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> List[MasterCVResponse]:
    """Get all Master CVs for a user."""
    try:
        logger.info(f"Retrieving master CVs for user {user_id}")
        master_cvs = await repository.find_many(
            {"user_id": user_id, "document_type": "master_cv"},
            sort=[("created_at", -1)],
            skip=skip,
            limit=limit,
        )

        response_list = []
        for master_cv in master_cvs:
            cv_id = master_cv.get("_id") or master_cv.get("id", "")
            response_list.append(
                MasterCVResponse(
                    id=str(cv_id),
                    user_id=master_cv.get("user_id", user_id),
                    title=master_cv.get("title", "Untitled"),
                    description=master_cv.get("description"),
                    content=master_cv.get("content", ""),
                    file_path=master_cv.get("file_path"),
                    file_size=master_cv.get("file_size"),
                    file_type=master_cv.get("file_type"),
                    tags=master_cv.get("tags"),
                    created_at=master_cv.get("created_at", datetime.utcnow()),
                    updated_at=master_cv.get("updated_at", datetime.utcnow()),
                    is_active=master_cv.get("is_active", False),
                    usage_count=master_cv.get("usage_count", 0),
                )
            )

        logger.info(f"Retrieved {len(response_list)} master CVs for user {user_id}")
        return response_list
    except Exception as e:
        logger.error(f"Error retrieving master CVs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve master CVs",
        )


async def get_master_cv(
    request: Request,
    master_cv_id: str,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> MasterCVResponse:
    """Get a specific Master CV by ID."""
    try:
        object_id = validate_object_id(master_cv_id)
        master_cv = await repository.get_by_id(object_id)
        if not master_cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Master CV not found"
            )

        cv_id = str(master_cv.get("_id") or getattr(master_cv, "id", master_cv_id))
        user_id = master_cv.get("user_id") or getattr(master_cv, "user_id", "")
        title = master_cv.get("title") or getattr(master_cv, "title", "Untitled")
        description = master_cv.get("description") or getattr(
            master_cv, "description", None
        )
        content = master_cv.get("content") or getattr(master_cv, "content", "")
        file_path = master_cv.get("file_path") or getattr(master_cv, "file_path", None)
        file_size = master_cv.get("file_size") or getattr(master_cv, "file_size", None)
        file_type = master_cv.get("file_type") or getattr(master_cv, "file_type", None)
        tags = master_cv.get("tags") or getattr(master_cv, "tags", None)
        created_at = master_cv.get("created_at") or getattr(
            master_cv, "created_at", datetime.utcnow()
        )
        updated_at = master_cv.get("updated_at") or getattr(
            master_cv, "updated_at", datetime.utcnow()
        )
        is_active = master_cv.get("is_active") or getattr(master_cv, "is_active", False)
        usage_count = master_cv.get("usage_count") or getattr(
            master_cv, "usage_count", 0
        )

        return MasterCVResponse(
            id=cv_id,
            user_id=user_id,
            title=title,
            description=description,
            content=content,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
            is_active=is_active,
            usage_count=usage_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving master CV {master_cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve master CV",
        )


async def replace_master_cv(
    request: Request,
    master_cv_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(lambda request: request.state.user),
    title: Optional[str] = Form(None, description="Updated title"),
    description: Optional[str] = Form(None, description="Updated description"),
    tags: Optional[str] = Form(None, description="Updated tags (comma-separated)"),
    repository: ResumeRepository = Depends(get_resume_repository),
    file_validator: SecureFileValidator = Depends(get_file_validator),
) -> MasterCVResponse:
    """Replace an existing Master CV with a new file."""
    try:
        object_id = validate_object_id(master_cv_id)
        existing_master_cv = await repository.get_by_id(object_id)
        if not existing_master_cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Master CV not found"
            )

        validate_master_cv_file(file)
        content = await file.read()
        _, safe_filename, _ = await file_validator.validate_upload(file)

        user_id = existing_master_cv.get("user_id") or getattr(
            existing_master_cv, "user_id"
        )
        file_path = store_file_securely(content, safe_filename, user_id)

        file_extension = Path(file.filename).suffix.lower() or ".txt"
        content = extract_text_from_file(str(file_path), file_extension)

        tag_list = (
            [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None
        )

        update_data = {
            "content": content,
            "file_path": str(file_path),
            "file_size": file.size,
            "file_type": file.content_type,
            "updated_at": datetime.utcnow(),
        }
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if tag_list is not None:
            update_data["tags"] = tag_list

        updated_master_cv = await repository.update(object_id, update_data)
        if not updated_master_cv:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update master CV",
            )

        logger.info(f"Master CV {master_cv_id} replaced successfully")

        cv_id = str(
            updated_master_cv.get("_id")
            or getattr(updated_master_cv, "id", master_cv_id)
        )
        final_title = updated_master_cv.get("title") or getattr(
            updated_master_cv, "title", "Untitled"
        )
        final_description = updated_master_cv.get("description") or getattr(
            updated_master_cv, "description", None
        )
        final_content = content
        final_file_path = str(file_path)
        final_file_size = file.size
        final_file_type = file.content_type
        final_tags = tag_list
        created_at = updated_master_cv.get("created_at") or getattr(
            updated_master_cv, "created_at", datetime.utcnow()
        )
        updated_at = updated_master_cv.get("updated_at") or getattr(
            updated_master_cv, "updated_at", datetime.utcnow()
        )
        is_active = updated_master_cv.get("is_active") or getattr(
            updated_master_cv, "is_active", False
        )
        usage_count = updated_master_cv.get("usage_count") or getattr(
            updated_master_cv, "usage_count", 0
        )

        return MasterCVResponse(
            id=cv_id,
            user_id=user_id,
            title=final_title,
            description=final_description,
            content=final_content,
            file_path=final_file_path,
            file_size=final_file_size,
            file_type=final_file_type,
            tags=final_tags,
            created_at=created_at,
            updated_at=updated_at,
            is_active=is_active,
            usage_count=usage_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing master CV {master_cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replace master CV: {str(e)}",
        )


async def delete_master_cv(
    request: Request,
    master_cv_id: str,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> Dict[str, str]:
    """Delete a Master CV."""
    try:
        object_id = validate_object_id(master_cv_id)
        existing_master_cv = await repository.get_by_id(object_id)
        if not existing_master_cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Master CV not found"
            )

        success = await repository.delete(object_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete master CV",
            )

        file_path = existing_master_cv.get("file_path") or getattr(
            existing_master_cv, "file_path", None
        )
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")

        logger.info(f"Master CV {master_cv_id} deleted successfully")
        return {"message": "Master CV deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting master CV {master_cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete master CV",
        )


async def test_master_cv_endpoint(
    request: Request,
    master_cv_id: str,
    test_request: MasterCVTestRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    universal_scorer: UniversalResumeScorer = Depends(),
) -> MasterCVTestResponse:
    """Test a Master CV against a job description."""
    try:
        logger.info(f"Testing master CV {master_cv_id}")
        object_id = validate_object_id(master_cv_id)
        master_cv = await repository.get_by_id(object_id)
        if not master_cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Master CV not found"
            )

        content = master_cv.get("content") or getattr(master_cv, "content", "")
        file_path = master_cv.get("file_path") or getattr(master_cv, "file_path", None)
        if not content and file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading master CV file: {e}")

        scoring_result = await universal_scorer.score_resume(
            resume_text=content,
            job_description=test_request.job_description,
        )

        optimized_sections = {
            "summary": f"Experienced professional seeking {test_request.target_role or 'new opportunities'} at {test_request.target_company or 'target company'}",
            "experience": "Optimized experience section would go here",
            "skills": "Optimized skills section would go here",
        }

        logger.info(f"Master CV {master_cv_id} tested successfully")
        return MasterCVTestResponse(
            success=True,
            ats_score=scoring_result.get("ats_score", 0.0),
            readability_score=scoring_result.get("readability_score", 0.0),
            strengths=scoring_result.get("strengths", []),
            weaknesses=scoring_result.get("weaknesses", []),
            recommendations=scoring_result.get("recommendations", []),
            keyword_analysis=scoring_result.get("keyword_analysis", {}),
            optimized_sections=optimized_sections,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing master CV {master_cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test master CV: {str(e)}",
        )


async def download_original_resume(
    request: Request,
    master_cv_id: str,
    repository: ResumeRepository = Depends(get_resume_repository),
) -> FileResponse:
    """Download the original uploaded file for a Master CV."""
    try:
        object_id = validate_object_id(master_cv_id)
        master_cv = await repository.get_by_id(object_id)
        if not master_cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Master CV not found"
            )

        file_path = master_cv.get("file_path") or getattr(master_cv, "file_path", None)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Original file not found"
            )

        usage_count = master_cv.get("usage_count") or getattr(
            master_cv, "usage_count", 0
        )
        await repository.update(object_id, {"usage_count": usage_count + 1})

        logger.info(f"Master CV {master_cv_id} file downloaded")
        filename = os.path.basename(file_path)
        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading master CV file {master_cv_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        )


# =============================================================================
# Router Configuration
# =============================================================================

router = APIRouter(
    prefix="/master-cv",
    tags=["Master CV"],
    responses={404: {"description": "Not found"}},
)

router.add_api_route(
    "/upload",
    upload_master_cv,
    methods=["POST"],
    response_model=MasterCVResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/user/{user_id}",
    get_master_cvs,
    methods=["GET"],
    response_model=List[MasterCVResponse],
)
router.add_api_route(
    "/{master_cv_id}", get_master_cv, methods=["GET"], response_model=MasterCVResponse
)
router.add_api_route(
    "/{master_cv_id}/replace",
    replace_master_cv,
    methods=["PUT"],
    response_model=MasterCVResponse,
)
router.add_api_route(
    "/{master_cv_id}",
    delete_master_cv,
    methods=["DELETE"],
    responses={200: {"description": "Success"}},
)
router.add_api_route(
    "/{master_cv_id}/test",
    test_master_cv_endpoint,
    methods=["POST"],
    response_model=MasterCVTestResponse,
)
router.add_api_route(
    "/{master_cv_id}/download", download_original_resume, methods=["GET"]
)

logger.info("Master CV router initialized")
