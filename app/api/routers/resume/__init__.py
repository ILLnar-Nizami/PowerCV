"""Resume API router module for resume management operations.

This module provides a modular structure for resume-related functionality including
resume creation, retrieval, optimization, PDF generation and deletion. It handles
the interface between HTTP requests and the resume repository, and coordinates
AI-powered resume optimization services.
"""

from .crud import (
    create_resume,
    delete_resume,
    get_resume,
    get_user_resumes,
    update_resume,
)
from .master_cv import (
    delete_master_cv,
    get_master_cv_by_id,
    get_master_cvs,
    replace_master_cv,
    test_master_cv_endpoint,
    upload_master_cv,
)
from .optimization import (
    generate_cover_letter,
    optimize_resume,
    score_resume,
)
from .router import resume_router
from .templates import (
    download_original_resume,
    download_resume,
    get_templates,
)

__all__ = [
    "resume_router",
    # CRUD operations
    "create_resume",
    "get_resume",
    "get_user_resumes",
    "update_resume",
    "delete_resume",
    # Optimization operations
    "optimize_resume",
    "score_resume",
    "generate_cover_letter",
    # Template operations
    "get_templates",
    "download_resume",
    "download_original_resume",
    # Master CV operations
    "replace_master_cv",
    "upload_master_cv",
    "get_master_cvs",
    "get_master_cv_by_id",
    "delete_master_cv",
    "test_master_cv_endpoint",
]
