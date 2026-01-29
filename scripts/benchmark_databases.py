#!/usr/bin/env python3
"""
Database benchmark script for PowerCV.

This script benchmarks PostgreSQL and MongoDB performance for critical queries.
"""

import asyncio
import logging
import time
from typing import Dict, List

from app.config import get_settings
from app.database.connector import (MongoConnectionManager,
                                    PostgresConnectionManager)
from app.database.models.resume import Resume, ResumeData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_sample_resumes(count: int = 100) -> List[Resume]:
    """Generate sample resumes for benchmarking."""
    resumes = []
    import uuid

    for i in range(count):
        # Use UUID to ensure unique IDs
        unique_id = str(uuid.uuid4())
        resume = Resume(
            user_id=f"user_{i % 10}",  # Distribute among 10 users
            title=f"Resume {unique_id}",
            original_content=f"Sample resume content for user {i}",
            job_description=f"Job description for position {i}",
            optimized_data=ResumeData(
                user_information={
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "phone": f"123-456-{i:04d}",
                    "location": f"City {i}",
                    "url": f"https://example.com/user{i}",
                    "summary": f"Summary for user {i}",
                    "main_job_title": f"Job Title {i}",
                    "profile_description": f"Profile description for user {i}",
                    "experiences": [],
                    "education": [],
                    "skills": {"hard_skills": [], "soft_skills": []},
                },
                education=[],
                experience=[],
                skills={"hard_skills": [], "soft_skills": []},
                projects=[],
                certifications=[],
                languages=[],
                interests=[],
                meta={},
            ),
            ats_score=70 + (i % 30),  # ATS scores between 70-100
        )
        resumes.append(resume)
    return resumes


async def benchmark_mongodb(resumes: List[Resume]) -> Dict[str, float]:
    """Benchmark MongoDB performance."""
    mongo_manager = MongoConnectionManager.get_instance()
    results = {}

    # Benchmark insert
    start_time = time.time()
    for resume in resumes:
        async with mongo_manager.get_collection("powercv", "resumes") as collection:
            await collection.insert_one(resume.model_dump(by_alias=True))
    results["mongodb_insert"] = time.time() - start_time

    # Benchmark query by user_id
    start_time = time.time()
    async with mongo_manager.get_collection("powercv", "resumes") as collection:
        await collection.find({"user_id": "user_0"}).to_list(length=100)
    results["mongodb_query_user"] = time.time() - start_time

    # Benchmark query by ATS score
    start_time = time.time()
    async with mongo_manager.get_collection("powercv", "resumes") as collection:
        await collection.find({"ats_score": {"$gte": 80}}).to_list(length=100)
    results["mongodb_query_ats"] = time.time() - start_time

    return results


async def benchmark_postgres(resumes: List[Resume]) -> Dict[str, float]:
    """Benchmark PostgreSQL performance."""
    postgres_manager = PostgresConnectionManager.get_instance()
    results = {}

    # Benchmark insert
    start_time = time.time()
    conn = await postgres_manager.get_connection()
    try:
        for resume in resumes:
            import json

            await conn.execute(
                """
                INSERT INTO resumes (
                    id, user_id, original_content, job_description,
                    optimized_data, ats_score, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                resume.title,  # Use title as ID for simplicity
                resume.user_id,
                resume.original_content,
                resume.job_description,
                (
                    json.dumps(resume.optimized_data.model_dump())
                    if resume.optimized_data
                    else None
                ),
                70 + (resumes.index(resume) % 30),  # ATS scores between 70-100
                resume.created_at,
                resume.updated_at,
            )
    finally:
        await conn.close()
    results["postgres_insert"] = time.time() - start_time

    # Benchmark query by user_id
    start_time = time.time()
    conn = await postgres_manager.get_connection()
    try:
        await conn.fetch(
            "SELECT * FROM resumes WHERE user_id = $1",
            "user_0",
        )
    finally:
        await conn.close()
    results["postgres_query_user"] = time.time() - start_time

    # Benchmark query by ATS score
    start_time = time.time()
    conn = await postgres_manager.get_connection()
    try:
        await conn.fetch(
            "SELECT * FROM resumes WHERE ats_score >= $1",
            80,
        )
    finally:
        await conn.close()
    results["postgres_query_ats"] = time.time() - start_time

    return results


async def run_benchmark():
    """Run the benchmark and print results."""
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

    # Generate sample data
    resumes = await generate_sample_resumes(100)
    logger.info(f"Generated {len(resumes)} sample resumes")

    # Benchmark MongoDB
    logger.info("Benchmarking MongoDB...")
    mongodb_results = await benchmark_mongodb(resumes)

    # Benchmark PostgreSQL
    logger.info("Benchmarking PostgreSQL...")
    postgres_results = await benchmark_postgres(resumes)

    # Print results
    logger.info("\nBenchmark Results:")
    logger.info("-" * 50)
    logger.info("MongoDB:")
    for key, value in mongodb_results.items():
        logger.info(f"  {key}: {value:.4f} seconds")

    logger.info("\nPostgreSQL:")
    for key, value in postgres_results.items():
        logger.info(f"  {key}: {value:.4f} seconds")

    logger.info("-" * 50)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
