"""Repository for custom template operations."""

from datetime import datetime
from typing import List

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.logging_config import logger
from app.database.models.custom_template import (
    CustomTemplate,
    CustomTemplateCreate,
    CustomTemplateUpdate,
)
from app.database.repositories.base_repo import BaseRepository


class CustomTemplateRepository(BaseRepository):
    """Repository for custom template database operations."""

    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        super().__init__(db)
        self.collection_name = "custom_templates"

    async def create_template(
        self, template_data: CustomTemplateCreate, user_id: str
    ) -> str:
        """Create a new custom template."""
        try:
            template = CustomTemplate(user_id=user_id, **template_data.model_dump())

            result = await self.db[self.collection_name].insert_one(
                template.model_dump()
            )
            template_id = str(result.inserted_id)

            logger.info(f"Created custom template: {template_id}")
            return template_id

        except Exception as e:
            logger.error(f"Failed to create custom template: {e}")
            raise

    async def get_template(self, template_id: str) -> CustomTemplate | None:
        """Get a custom template by ID."""
        try:
            doc = await self.db[self.collection_name].find_one(
                {"_id": ObjectId(template_id)}
            )
            return CustomTemplate(**doc) if doc else None

        except Exception as e:
            logger.error(f"Failed to get custom template {template_id}: {e}")
            raise

    async def get_user_templates(
        self, user_id: str, limit: int = 50
    ) -> List[CustomTemplate]:
        """Get all templates for a specific user."""
        try:
            cursor = (
                self.db[self.collection_name]
                .find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(limit)
            )

            docs = await cursor.to_list(length=limit)
            return [CustomTemplate(**doc) for doc in docs]

        except Exception as e:
            logger.error(f"Failed to get user templates for {user_id}: {e}")
            raise

    async def get_public_templates(self, limit: int = 100) -> List[CustomTemplate]:
        """Get all public templates."""
        try:
            cursor = (
                self.db[self.collection_name]
                .find({"is_public": True})
                .sort("download_count", -1)
                .limit(limit)
            )

            docs = await cursor.to_list(length=limit)
            return [CustomTemplate(**doc) for doc in docs]

        except Exception as e:
            logger.error(f"Failed to get public templates: {e}")
            raise

    async def update_template(
        self, template_id: str, update_data: CustomTemplateUpdate
    ) -> bool:
        """Update a custom template."""
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()

            result = await self.db[self.collection_name].update_one(
                {"_id": ObjectId(template_id)}, {"$set": update_dict}
            )

            success = result.modified_count > 0
            if success:
                logger.info(f"Updated custom template: {template_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update custom template {template_id}: {e}")
            raise

    async def delete_template(self, template_id: str) -> bool:
        """Delete a custom template."""
        try:
            result = await self.db[self.collection_name].delete_one(
                {"_id": ObjectId(template_id)}
            )

            success = result.deleted_count > 0
            if success:
                logger.info(f"Deleted custom template: {template_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete custom template {template_id}: {e}")
            raise

    async def increment_download_count(self, template_id: str) -> bool:
        """Increment the download count for a template."""
        try:
            result = await self.db[self.collection_name].update_one(
                {"_id": ObjectId(template_id)}, {"$inc": {"download_count": 1}}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to increment download count for {template_id}: {e}")
            raise

    async def search_templates(
        self, query: str, limit: int = 50
    ) -> List[CustomTemplate]:
        """Search templates by name or description."""
        try:
            search_filter = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"category": {"$regex": query, "$options": "i"}},
                ],
                "is_public": True,
            }

            cursor = (
                self.db[self.collection_name]
                .find(search_filter)
                .sort("rating", -1)
                .limit(limit)
            )
            docs = await cursor.to_list(length=limit)

            return [CustomTemplate(**doc) for doc in docs]

        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            raise
