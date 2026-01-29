"""Custom template model for user-defined resume templates."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from bson import ObjectId


class CustomTemplate(BaseModel):
    """Custom template model for user-defined resume templates."""
    
    id: str | None = Field(None, alias="_id")
    user_id: str = Field(..., description="User who created the template")
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: str | None = Field(None, max_length=500, description="Template description")
    category: str = Field(..., description="Template category")
    typst_content: str = Field(..., description="Typst template content")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    preview_image: str | None = Field(None, description="Preview image URL")
    is_public: bool = Field(default=False, description="Whether template is public")
    download_count: int = Field(default=0, description="Download count")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average rating")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class CustomTemplateCreate(BaseModel):
    """Model for creating custom templates."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    category: str = Field(...)
    typst_content: str = Field(...)
    variables: List[str] = Field(default_factory=list)
    preview_image: str | None = None
    is_public: bool = False


class CustomTemplateUpdate(BaseModel):
    """Model for updating custom templates."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    category: str | None = None
    typst_content: str | None = None
    variables: List[str] | None = None
    preview_image: str | None = None
    is_public: bool | None = None
