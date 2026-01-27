#!/usr/bin/env python3
"""
Check PostgreSQL table schema for PowerCV.
"""

import asyncio
import logging

from app.database.connector import PostgresConnectionManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_schema():
    """Check PostgreSQL table schema."""
    try:
        postgres_manager = PostgresConnectionManager.get_instance()
        conn = await postgres_manager.get_connection()
        try:
            # Check resumes table columns
            result = await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'resumes'"
            )
            logger.info("Resumes table columns:")
            for row in result:
                logger.info(f"  {row[0]}")

            # Check users table columns
            result = await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
            )
            logger.info("Users table columns:")
            for row in result:
                logger.info(f"  {row[0]}")

        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to check schema: {e}")


if __name__ == "__main__":
    asyncio.run(check_schema())
