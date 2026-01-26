"""Main resume router that combines all sub-routers.

This module creates the main APIRouter instance for resume operations
by combining all specialized sub-routers for different resume functionalities.
"""

import logging

from fastapi import APIRouter

from . import crud, master_cv, optimization, templates

logger = logging.getLogger(__name__)

# Create main resume router
resume_router = APIRouter(
    prefix="/api/v1/resumes",
    tags=["Resumes"],
    responses={404: {"description": "Not found"}},
)

# Include sub-routers
resume_router.include_router(crud.router, prefix="", tags=["CRUD"])
resume_router.include_router(master_cv.router, prefix="", tags=["Master CV"])
resume_router.include_router(optimization.router, prefix="", tags=["Optimization"])
resume_router.include_router(templates.router, prefix="", tags=["Templates"])


# Legacy endpoint compatibility - redirect /api/resume/{id} to /api/v1/resumes/{id}
# This is handled by the frontend expecting /api/resume/{id} format
@resume_router.api_route(
    "/legacy/{resume_id}",
    methods=["GET"],
    include_in_schema=False,
)
async def legacy_resume_redirect(resume_id: str):
    """Legacy endpoint for backward compatibility with frontend."""
    from fastapi import RedirectResponse

    return RedirectResponse(url=f"/api/v1/resumes/{resume_id}", status_code=301)


logger.info("Resume router initialized with all sub-routers")
