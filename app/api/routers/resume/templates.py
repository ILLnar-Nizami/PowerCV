"""Template management and download operations module.

This module provides endpoints for managing resume templates and downloading
resume files including PDF generation, template customization, and file serving.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config.templates import TemplateConfig
from app.database.repositories.resume_repository import ResumeRepository
from app.middleware.rate_limit import light_limit
from app.services.resume.typst_generator import TypstGenerator

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class TemplateRequest(BaseModel):
    """Schema for template operations."""

    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., description="Template category")
    style: Optional[str] = Field(None, description="Template style")
    is_custom: bool = Field(False, description="Whether this is a custom template")
    template_data: Optional[Dict[str, Any]] = Field(
        None, description="Template configuration data"
    )


class TemplateResponse(BaseModel):
    """Response model for template data."""

    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., description="Template category")
    style: Optional[str] = Field(None, description="Template style")
    is_custom: bool = Field(..., description="Whether this is a custom template")
    template_data: Optional[Dict[str, Any]] = Field(
        None, description="Template configuration data"
    )
    preview_image: Optional[str] = Field(
        None, description="URL to template preview image"
    )
    download_count: int = Field(0, description="Number of times downloaded")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DownloadRequest(BaseModel):
    """Schema for resume download requests."""

    format: str = Field(..., description="Output format (pdf, docx, html)")
    template_id: Optional[str] = Field(None, description="Template to use")
    include_cover_letter: bool = Field(
        False, description="Include cover letter in download"
    )
    custom_options: Optional[Dict[str, Any]] = Field(
        None, description="Custom formatting options"
    )


class DownloadResponse(BaseModel):
    """Response model for resume download."""

    success: bool = Field(..., description="Whether download was successful")
    download_url: Optional[str] = Field(None, description="URL to download the file")
    file_name: Optional[str] = Field(None, description="Generated file name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time")


class TemplateListResponse(BaseModel):
    """Response model for template list."""

    templates: List[TemplateResponse] = Field(..., description="List of templates")
    total: int = Field(..., description="Total number of templates")
    categories: List[str] = Field(..., description="Available categories")


# =============================================================================
# Template Configuration
# =============================================================================

# Built-in templates configuration
BUILTIN_TEMPLATES = {
    "professional": {
        "name": "Professional",
        "description": "Clean, professional template suitable for corporate environments",
        "category": "business",
        "style": "formal",
        "is_custom": False,
        "preview_image": "/static/templates/professional_preview.png",
    },
    "modern": {
        "name": "Modern",
        "description": "Contemporary design with clean lines and modern typography",
        "category": "creative",
        "style": "modern",
        "is_custom": False,
        "preview_image": "/static/templates/modern_preview.png",
    },
    "creative": {
        "name": "Creative",
        "description": "Artistic template perfect for design and creative roles",
        "category": "creative",
        "style": "creative",
        "is_custom": False,
        "preview_image": "/static/templates/creative_preview.png",
    },
    "technical": {
        "name": "Technical",
        "description": "Template optimized for technical and engineering roles",
        "category": "technical",
        "style": "technical",
        "is_custom": False,
        "preview_image": "/static/templates/technical_preview.png",
    },
    "executive": {
        "name": "Executive",
        "description": "Elegant template for senior management and executive positions",
        "category": "business",
        "style": "executive",
        "is_custom": False,
        "preview_image": "/static/templates/executive_preview.png",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================


def validate_format(format: str) -> str:
    """Validate download format.

    Args:
        format: Requested format

    Returns:
        str: Validated format

    Raises:
        HTTPException: If format is not supported
    """
    supported_formats = ["pdf", "docx", "html", "txt"]
    if format.lower() not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Supported formats: {', '.join(supported_formats)}",
        )
    return format.lower()


def get_template_categories() -> List[str]:
    """Get list of available template categories.

    Returns:
        List[str]: List of categories
    """
    categories = set()
    for template in BUILTIN_TEMPLATES.values():
        categories.add(template["category"])
    return sorted(list(categories))


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


async def get_template_config() -> TemplateConfig:
    """Get template configuration instance.

    Returns:
        TemplateConfig: Template configuration
    """
    return TemplateConfig()


async def get_typst_generator() -> TypstGenerator:
    """Get Typst PDF generator instance.

    Returns:
        TypstGenerator: Generator instance
    """
    return TypstGenerator()


# =============================================================================
# Template Endpoints
# =============================================================================


@light_limit()
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    style: Optional[str] = Query(None, description="Filter by style"),
    include_custom: bool = Query(True, description="Include custom templates"),
) -> TemplateListResponse:
    """Get available resume templates.

    Args:
        category: Filter templates by category
        style: Filter templates by style
        include_custom: Whether to include custom templates

    Returns:
        TemplateListResponse: List of available templates

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info("Retrieving resume templates")

        # Start with built-in templates
        templates = []
        template_id = 1

        for template_key, template_data in BUILTIN_TEMPLATES.items():
            # Apply filters
            if category and template_data["category"] != category:
                continue
            if style and template_data["style"] != style:
                continue

            templates.append(
                TemplateResponse(
                    id=str(template_id),
                    name=template_data["name"],
                    description=template_data["description"],
                    category=template_data["category"],
                    style=template_data["style"],
                    is_custom=template_data["is_custom"],
                    template_data=template_data,
                    preview_image=template_data["preview_image"],
                    download_count=0,  # Built-in templates start with 0
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            template_id += 1

        # Add custom templates from database if requested
        if include_custom:
            # TODO: Implement custom template retrieval from database
            pass

        categories = get_template_categories()

        logger.info(f"Retrieved {len(templates)} templates")

        return TemplateListResponse(
            templates=templates,
            total=len(templates),
            categories=categories,
        )

    except Exception as e:
        logger.error(f"Error retrieving templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates",
        )


@light_limit()
async def get_template_by_id(
    template_id: str,
) -> TemplateResponse:
    """Get a specific template by ID.

    Args:
        template_id: Template identifier

    Returns:
        TemplateResponse: Template data

    Raises:
        HTTPException: If template not found
    """
    try:
        logger.info(f"Retrieving template {template_id}")

        # Check if it's a built-in template
        template_index = int(template_id) - 1
        template_keys = list(BUILTIN_TEMPLATES.keys())

        if 0 <= template_index < len(template_keys):
            template_key = template_keys[template_index]
            template_data = BUILTIN_TEMPLATES[template_key]

            return TemplateResponse(
                id=template_id,
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                style=template_data["style"],
                is_custom=template_data["is_custom"],
                template_data=template_data,
                preview_image=template_data["preview_image"],
                download_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        # Check custom templates (TODO: Implement database lookup)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid template ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template",
        )


@light_limit()
async def create_custom_template(
    request: TemplateRequest,
) -> TemplateResponse:
    """Create a custom template.

    Args:
        request: Template creation data

    Returns:
        TemplateResponse: Created template data

    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info("Creating custom template")

        # TODO: Implement custom template creation in database
        # For now, return a mock response

        template_id = str(datetime.utcnow().timestamp())

        return TemplateResponse(
            id=template_id,
            name=request.name,
            description=request.description,
            category=request.category,
            style=request.style,
            is_custom=True,
            template_data=request.template_data,
            preview_image=None,
            download_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error creating custom template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom template",
        )


# =============================================================================
# Download Endpoints
# =============================================================================


@light_limit()
async def download_resume(
    resume_id: str,
    request: DownloadRequest,
    repository: ResumeRepository = Depends(get_resume_repository),
    typst_generator: TypstGenerator = Depends(get_typst_generator),
) -> DownloadResponse:
    """Download a resume in the specified format.

    Args:
        resume_id: Resume identifier
        request: Download request data
        repository: Resume repository instance
        typst_generator: PDF generator instance

    Returns:
        DownloadResponse: Download information

    Raises:
        HTTPException: If download fails or resume not found
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId

        logger.info(f"Starting resume download for {resume_id}")

        # Validate and convert ID
        try:
            object_id = ObjectId(resume_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resume ID format",
            )

        # Get resume from repository
        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Validate format
        validated_format = validate_format(request.format)

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(
            c for c in resume.title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        file_name = f"{safe_title}_{timestamp}.{validated_format}"

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file_name)

        try:
            # Generate file based on format
            if validated_format == "pdf":
                # Use Typst generator for PDF
                await typst_generator.generate_pdf(
                    resume_content=resume.original_content,
                    output_path=file_path,
                    template_id=request.template_id,
                )
            elif validated_format == "html":
                # Generate HTML content
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{resume.title}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        .header {{ text-align: center; margin-bottom: 30px; }}
                        .section {{ margin-bottom: 20px; }}
                        .section h2 {{ border-bottom: 1px solid #ccc; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>{resume.title}</h1>
                    </div>
                    <div class="section">
                        <pre>{resume.original_content}</pre>
                    </div>
                </body>
                </html>
                """
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
            elif validated_format == "txt":
                # Generate plain text
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(resume.original_content)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Format {validated_format} not yet implemented",
                )

            # Get file size
            file_size = os.path.getsize(file_path)

            # TODO: Implement file serving with expiration
            download_url = f"/api/v1/resumes/downloads/{file_name}"

            logger.info(f"Resume {resume_id} downloaded successfully as {file_name}")

            return DownloadResponse(
                success=True,
                download_url=download_url,
                file_name=file_name,
                file_size=file_size,
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )

        finally:
            # Clean up temporary file after some time
            # In production, implement proper file cleanup with background task
            pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download resume: {str(e)}",
        )


@light_limit()
async def download_resume_file(
    file_name: str,
) -> FileResponse:
    """Serve a downloaded resume file.

    Args:
        file_name: Name of the file to serve

    Returns:
        FileResponse: The resume file

    Raises:
        HTTPException: If file not found
    """
    try:
        logger.info(f"Serving downloaded file: {file_name}")

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file_name)

        # Validate file path (security check)
        if not os.path.abspath(file_path).startswith(os.path.abspath(temp_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path"
            )

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        logger.info(f"File {file_name} served successfully")

        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file {file_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve file",
        )


@light_limit()
async def generate_pdf_preview(
    resume_id: str,
    template_id: Optional[str] = None,
    repository: ResumeRepository = Depends(get_resume_repository),
    typst_generator: TypstGenerator = Depends(get_typst_generator),
) -> FileResponse:
    """Generate a PDF preview of a resume.

    Args:
        resume_id: Resume identifier
        template_id: Optional template to use
        repository: Resume repository instance
        typst_generator: PDF generator instance

    Returns:
        FileResponse: PDF preview file

    Raises:
        HTTPException: If generation fails or resume not found
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId

        logger.info(f"Generating PDF preview for resume {resume_id}")

        # Validate and convert ID
        try:
            object_id = ObjectId(resume_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resume ID format",
            )

        # Get resume from repository
        resume = await repository.get_by_id(object_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Generate PDF preview
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        preview_filename = f"preview_{resume_id}_{timestamp}.pdf"
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, preview_filename)

        await typst_generator.generate_pdf(
            resume_content=resume.original_content,
            output_path=file_path,
            template_id=template_id,
            is_preview=True,
        )

        logger.info(f"PDF preview generated for resume {resume_id}")

        return FileResponse(
            path=file_path,
            filename=preview_filename,
            media_type="application/pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF preview for resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF preview",
        )


# =============================================================================
# Router Configuration
# =============================================================================

# Create router for templates and downloads
router = APIRouter(
    prefix="/templates",
    tags=["Templates and Downloads"],
    responses={404: {"description": "Not found"}},
)

# Register template endpoints
router.add_api_route(
    "/",
    get_templates,
    methods=["GET"],
    response_model=TemplateListResponse,
)

router.add_api_route(
    "/{template_id}",
    get_template_by_id,
    methods=["GET"],
    response_model=TemplateResponse,
)

router.add_api_route(
    "/custom",
    create_custom_template,
    methods=["POST"],
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)

# Register download endpoints
router.add_api_route(
    "/{resume_id}/download",
    download_resume,
    methods=["POST"],
    response_model=DownloadResponse,
)

router.add_api_route(
    "/downloads/{file_name}",
    download_resume_file,
    methods=["GET"],
)

router.add_api_route(
    "/{resume_id}/preview",
    generate_pdf_preview,
    methods=["GET"],
)

logger.info("Templates and downloads router initialized")
