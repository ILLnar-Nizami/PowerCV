"""File parsing router to extract text from uploads."""

import logging
import os
import shutil
import tempfile
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.utils.file_handling import extract_text_from_file

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/parser",
    tags=["Parser"],
    responses={404: {"description": "Not found"}},
)


@router.post("/parse", response_model=Dict[str, str])
async def parse_file(file: UploadFile = File(...)) -> Dict[str, str]:
    """Parse an uploaded file and extract its text content.

    Args:
        file: The uploaded file (PDF, DOCX, TXT, MD)

    Returns:
        Dict[str, str]: Extracted text content
    """
    temp_file_path = None
    try:
        # Create a temporary file
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            # Copy uploaded file content to temp file
            shutil.copyfileobj(file.file, temp_file)

        # Extract text
        file_extension = os.path.splitext(temp_file_path)[1]
        text = extract_text_from_file(temp_file_path, file_extension)

        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from file",
            )

        return {"text": text}

    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse file: {str(e)}",
        )
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
