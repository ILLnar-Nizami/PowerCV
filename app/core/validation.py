"""Input validation utilities for PowerCV.

This module provides comprehensive input validation functions for file uploads,
API parameters, and user inputs to ensure security and data integrity.
"""

import re
import magic
from pathlib import Path
from typing import List, Dict, Any
from fastapi import HTTPException, status, UploadFile
from pydantic import BaseModel, validator
import logging

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/rtf",
    "application/rtf",
}

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",  # JavaScript URLs
    r"on\w+\s*=",  # Event handlers
    r"eval\s*\(",  # eval() calls
    r"exec\s*\(",  # exec() calls
]

class ValidationError(Exception):
    """Custom validation error."""
    pass


class FileValidationResult(BaseModel):
    """Result of file validation."""
    is_valid: bool
    file_type: str
    file_size: int
    mime_type: str
    errors: List[str] = []
    warnings: List[str] = []


def validate_file_upload(file: UploadFile, max_size: int = MAX_FILE_SIZE) -> FileValidationResult:
    """Validate uploaded file for security and integrity.
    
    Args:
        file: UploadFile object from FastAPI
        max_size: Maximum allowed file size in bytes
        
    Returns:
        FileValidationResult with validation status and details
        
    Raises:
        HTTPException: If file is invalid
    """
    result = FileValidationResult(
        is_valid=False,
        file_type="unknown",
        file_size=0,
        mime_type="unknown"
    )
    
    try:
        # Check if file was provided
        if not file or not file.filename:
            result.errors.append("No file provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Validate filename
        filename = file.filename
        if not validate_filename(filename):
            result.errors.append(f"Invalid filename: {filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filename: {filename}"
            )
        
        # Get file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            result.errors.append(f"File type not allowed: {file_ext}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content for validation
        content = file.file.read(max_size + 1)  # Read max_size + 1 to check size
        file.file.seek(0)  # Reset file pointer
        
        actual_size = len(content)
        result.file_size = actual_size
        
        # Check file size
        if actual_size > max_size:
            result.errors.append(f"File too large: {actual_size} bytes (max: {max_size})")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
        
        # Validate MIME type using python-magic
        try:
            mime_type = magic.from_buffer(content, mime=True)
            result.mime_type = mime_type
            
            if mime_type not in ALLOWED_MIME_TYPES:
                result.errors.append(f"MIME type not allowed: {mime_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not detected as valid document"
                )
        except Exception as e:
            logger.warning(f"Could not determine MIME type: {e}")
            result.warnings.append("Could not verify file type")
        
        # Check for malicious content in text files
        if mime_type.startswith("text/") or file_ext in ['.txt', '.rtf']:
            try:
                text_content = content.decode('utf-8', errors='ignore')
                if contains_malicious_content(text_content):
                    result.errors.append("File contains potentially malicious content")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File contains potentially malicious content"
                    )
            except Exception:
                pass  # If we can't decode as text, skip content validation
        
        result.file_type = file_ext
        result.is_valid = True
        
        logger.info(f"File validation successful: {filename} ({actual_size} bytes, {mime_type})")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File validation error: {e}")
        result.errors.append(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File validation failed"
        )
    
    return result


def validate_filename(filename: str) -> bool:
    """Validate filename for security.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if filename is safe, False otherwise
    """
    if not filename:
        return False
    
    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    
    # Check for null bytes
    if "\x00" in filename:
        return False
    
    # Check for dangerous characters
    dangerous_chars = ["<", ">", ":", "\"", "|", "?", "*"]
    if any(char in filename for char in dangerous_chars):
        return False
    
    # Check length
    if len(filename) > 255:
        return False
    
    # Check for valid extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True


def contains_malicious_content(content: str) -> bool:
    """Check if text content contains potentially malicious patterns.
    
    Args:
        content: Text content to check
        
    Returns:
        True if malicious content is found, False otherwise
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return True
    return False


def sanitize_text_input(text: str, max_length: int = 10000) -> str:
    """Sanitize text input to prevent injection attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    # Remove potentially dangerous HTML-like content
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Remove common formatting characters
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Check if it's a reasonable length (10-15 digits)
    return 10 <= len(cleaned) <= 15 and cleaned.startswith('+') or cleaned.isdigit()


class SecureUploadHandler:
    """Secure file upload handler with validation."""
    
    def __init__(self, upload_dir: str = "uploads", max_size: int = MAX_FILE_SIZE):
        self.upload_dir = Path(upload_dir)
        self.max_size = max_size
        self.upload_dir.mkdir(exist_ok=True)
    
    async def save_file(self, file: UploadFile, user_id: str = None) -> Dict[str, Any]:
        """Save uploaded file with validation.
        
        Args:
            file: UploadFile object
            user_id: Optional user ID for file organization
            
        Returns:
            Dictionary with file information
            
        Raises:
            HTTPException: If validation fails
        """
        # Validate file
        validation_result = validate_file_upload(file, self.max_size)
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Generate secure filename
        filename = self._generate_secure_filename(file.filename, user_id)
        file_path = self.upload_dir / filename
        
        # Save file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"File saved successfully: {file_path}")
            
            return {
                "filename": filename,
                "original_filename": file.filename,
                "file_path": str(file_path),
                "file_size": validation_result.file_size,
                "mime_type": validation_result.mime_type,
                "file_type": validation_result.file_type,
            }
            
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            # Clean up if save failed
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            )
    
    def _generate_secure_filename(self, original_filename: str, user_id: str = None) -> str:
        """Generate secure filename to prevent conflicts and attacks.
        
        Args:
            original_filename: Original filename
            user_id: Optional user ID
            
        Returns:
            Secure filename
        """
        import uuid
        import time
        
        # Get file extension
        ext = Path(original_filename).suffix.lower()
        
        # Generate unique identifier
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        # Build filename
        if user_id:
            filename = f"{user_id}_{timestamp}_{unique_id}{ext}"
        else:
            filename = f"{timestamp}_{unique_id}{ext}"
        
        return filename


# Pydantic models for request validation
class CVUploadRequest(BaseModel):
    """Request model for CV upload."""
    job_description: str
    generate_cover_letter: bool = False
    
    @validator('job_description')
    def validate_jd(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Job description must be at least 10 characters long")
        if len(v) > 10000:
            raise ValueError("Job description too long (max 10000 characters)")
        return sanitize_text_input(v, 10000)


class JobDescriptionRequest(BaseModel):
    """Request model for job description URL."""
    url: str
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return v


# Middleware for request validation
def validate_request_size(request_size: int, max_size: int = 10 * 1024 * 1024) -> None:
    """Validate request size to prevent DoS attacks.
    
    Args:
        request_size: Size of request in bytes
        max_size: Maximum allowed size
        
    Raises:
        HTTPException: If request is too large
    """
    if request_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request too large. Maximum size: {max_size // (1024*1024)}MB"
        )
