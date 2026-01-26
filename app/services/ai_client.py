"""HTTP client for AI Service."""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8082")


class AIServiceClient:
    """HTTP client for the AI microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or AI_SERVICE_URL

    async def analyze(self, cv_text: str, jd_text: str) -> Dict[str, Any]:
        """Analyze CV against job description."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v2/analyze",
                json={"cv_text": cv_text, "jd_text": jd_text},
            )
            response.raise_for_status()
            return response.json()

    async def optimize(
        self,
        cv_text: str,
        jd_text: str,
        analysis: Optional[Dict] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Optimize CV for a job description."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v2/optimize",
                json={
                    "cv_text": cv_text,
                    "jd_text": jd_text,
                    "analysis": analysis,
                    "email": email,
                },
            )
            response.raise_for_status()
            return response.json()

    async def generate_cover_letter(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        tone: str = "Professional",
    ) -> Dict[str, Any]:
        """Generate a cover letter."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v2/cover-letter",
                json={
                    "candidate_data": candidate_data,
                    "job_data": job_data,
                    "tone": tone,
                },
            )
            response.raise_for_status()
            return response.json()


_client: Optional[AIServiceClient] = None


def get_ai_client() -> AIServiceClient:
    """Get the AI service client singleton."""
    global _client
    if _client is None:
        _client = AIServiceClient()
    return _client


async def analyze_cv(cv_text: str, jd_text: str) -> Dict[str, Any]:
    """Analyze CV against job description."""
    client = get_ai_client()
    return await client.analyze(cv_text, jd_text)


async def optimize_cv(
    cv_text: str,
    jd_text: str,
    analysis: Optional[Dict] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """Optimize CV for a job description."""
    client = get_ai_client()
    return await client.optimize(cv_text, jd_text, analysis, email)


async def generate_cover_letter(
    candidate_data: Dict[str, Any],
    job_data: Dict[str, Any],
    tone: str = "Professional",
) -> Dict[str, Any]:
    """Generate a cover letter."""
    client = get_ai_client()
    return await client.generate_cover_letter(candidate_data, job_data, tone)
