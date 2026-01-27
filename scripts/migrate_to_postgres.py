#!/usr/bin/env python3
"""
MongoDB to PostgreSQL migration script for PowerCV.

This script migrates data from MongoDB to PostgreSQL for the PowerCV application.
"""

import asyncio
import logging
from typing import Dict, List

from app.config import get_settings
from app.database.connector import MongoConnectionManager, PostgresConnectionManager
from app.database.models.resume import Resume

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_resumes():
    """Migrate resumes from MongoDB to PostgreSQL."""
    settings = get_settings()

    if not all(
        [
            settings.postgres_user,
            settings.postgres_password,
            settings.postgres_db,
            settings.postgres_host,
        ]
    ):
        logger.error("PostgreSQL configuration is incomplete")
        return

    try:
        # Initialize connection managers
        mongo_manager = MongoConnectionManager.get_instance()
        postgres_manager = PostgresConnectionManager.get_instance()

        # Get all resumes from MongoDB
        logger.info("Fetching resumes from MongoDB...")
        async with mongo_manager.get_collection("powercv", "resumes") as collection:
            cursor = collection.find({})
            resumes = await cursor.to_list(length=None)

        logger.info(f"Found {len(resumes)} resumes in MongoDB")

        # Migrate resumes to PostgreSQL
        logger.info("Migrating resumes to PostgreSQL...")
        migrated_count = 0

        conn = await postgres_manager.get_connection()
        try:
            for resume_doc in resumes:
                try:
                    # Handle MongoDB document directly
                    import json

                    # Insert into PostgreSQL
                    await conn.execute(
                        """
                        INSERT INTO resumes (
                            id, user_id, original_content, job_description,
                            optimized_data, ats_score, original_ats_score,
                            matching_skills, missing_skills, score_improvement,
                            recommendation, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (id) DO UPDATE SET
                            user_id = EXCLUDED.user_id,
                            original_content = EXCLUDED.original_content,
                            job_description = EXCLUDED.job_description,
                            optimized_data = EXCLUDED.optimized_data,
                            ats_score = EXCLUDED.ats_score,
                            original_ats_score = EXCLUDED.original_ats_score,
                            matching_skills = EXCLUDED.matching_skills,
                            missing_skills = EXCLUDED.missing_skills,
                            score_improvement = EXCLUDED.score_improvement,
                            recommendation = EXCLUDED.recommendation,
                            updated_at = EXCLUDED.updated_at
                        """,
                        str(resume_doc.get("_id")),
                        resume_doc.get("user_id"),
                        resume_doc.get("original_content"),
                        resume_doc.get("job_description"),
                        json.dumps(resume_doc.get("optimized_data"))
                        if resume_doc.get("optimized_data")
                        else None,
                        resume_doc.get("ats_score"),
                        resume_doc.get("original_ats_score"),
                        resume_doc.get("matching_skills", []),
                        resume_doc.get("missing_skills", []),
                        resume_doc.get("score_improvement"),
                        resume_doc.get("recommendation"),
                        resume_doc.get("created_at"),
                        resume_doc.get("updated_at"),
                    )

                    migrated_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to migrate resume {resume_doc.get('_id')}: {e}"
                    )
                    continue
        finally:
            await conn.close()

        logger.info(f"Successfully migrated {migrated_count} resumes to PostgreSQL")

    except Exception as e:
        logger.error(f"Failed to migrate resumes: {e}")


async def migrate_users():
    """Migrate users from MongoDB to PostgreSQL."""
    settings = get_settings()

    if not all(
        [
            settings.postgres_user,
            settings.postgres_password,
            settings.postgres_db,
            settings.postgres_host,
        ]
    ):
        logger.error("PostgreSQL configuration is incomplete")
        return

    try:
        # Initialize connection managers
        mongo_manager = MongoConnectionManager.get_instance()
        postgres_manager = PostgresConnectionManager.get_instance()

        # Get all users from MongoDB
        logger.info("Fetching users from MongoDB...")
        async with mongo_manager.get_collection("powercv", "users") as collection:
            cursor = collection.find({})
            users = await cursor.to_list(length=None)

        logger.info(f"Found {len(users)} users in MongoDB")

        # Migrate users to PostgreSQL
        logger.info("Migrating users to PostgreSQL...")
        migrated_count = 0

        conn = await postgres_manager.get_connection()
        try:
            for user_doc in users:
                try:
                    # Insert into PostgreSQL
                    await conn.execute(
                        """
                        INSERT INTO users (
                            id, email, first_name, last_name, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO UPDATE SET
                            email = EXCLUDED.email,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            updated_at = EXCLUDED.updated_at
                        """,
                        str(user_doc.get("_id")),
                        user_doc.get("email"),
                        user_doc.get("first_name"),
                        user_doc.get("last_name"),
                        user_doc.get("created_at"),
                        user_doc.get("updated_at"),
                    )

                    migrated_count += 1

                except Exception as e:
                    logger.error(f"Failed to migrate user {user_doc.get('_id')}: {e}")
                    continue
        finally:
            await conn.close()

        logger.info(f"Successfully migrated {migrated_count} users to PostgreSQL")

    except Exception as e:
        logger.error(f"Failed to migrate users: {e}")


async def run_migration():
    """Run the full migration process."""
    logger.info("Starting MongoDB to PostgreSQL migration...")

    # Migrate users first (foreign key dependency)
    await migrate_users()

    # Migrate resumes
    await migrate_resumes()

    logger.info("Migration completed!")


if __name__ == "__main__":
    asyncio.run(run_migration())
