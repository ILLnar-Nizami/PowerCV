#!/usr/bin/env python3
"""
PostgreSQL initialization script for PowerCV.

This script creates the necessary tables for the PowerCV application in PostgreSQL.
"""

import asyncio
import logging
from typing import Optional

from app.config import get_settings
from app.database.connector import PostgresConnectionManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create PostgreSQL tables for PowerCV."""
    settings = get_settings()

    if not all(
        [
            settings.postgres_user or "powercv",
            settings.postgres_password or "powercv",
            settings.postgres_db or "powercv",
            settings.postgres_host or "localhost",
        ]
    ):
        logger.error("PostgreSQL configuration is incomplete")
        return

    try:
        postgres_manager = PostgresConnectionManager.get_instance()
        conn = await postgres_manager.get_connection()
        try:
            # Create users table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE,
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create resumes table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resumes (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES users(id),
                    title VARCHAR(255),
                    original_content TEXT,
                    job_description TEXT,
                    optimized_data JSONB,
                    ats_score INTEGER,
                    original_ats_score INTEGER,
                    matching_skills TEXT[],
                    missing_skills TEXT[],
                    score_improvement INTEGER,
                    recommendation TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create index on user_id for faster queries
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id)"
            )

            # Create index on ats_score for analytics
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_resumes_ats_score ON resumes(ats_score)"
            )

            logger.info("PostgreSQL tables created successfully")
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to create PostgreSQL tables: {e}")


if __name__ == "__main__":
    asyncio.run(create_tables())
