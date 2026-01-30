"""Database models package for data representation.

This package contains Pydantic model classes that define the structure of data
used throughout the application. These models are used for data validation,
serialization/deserialization, and documentation of API endpoints.
"""

from .ai_cover_letter import AICoverLetterRequest, AICoverLetterResponse
from .base import BaseSchema
from .cover_letter import CoverLetter
from .custom_template import CustomTemplate
from .resume import Resume
from .token_usage import TokenUsage

__all__ = [
    "BaseSchema",
    "Resume",
    "CoverLetter",
    "AICoverLetterRequest",
    "AICoverLetterResponse",
    "TokenUsage",
    "CustomTemplate",
]
