"""HTTP client for AI Service."""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8082")

# Timeout configuration from environment with secure defaults
DEFAULT_TIMEOUT = float(os.getenv("AI_SERVICE_TIMEOUT", "120.0"))


class AIServiceClient:
    """HTTP client for the AI microservice.

    Uses connection pooling via a shared httpx.AsyncClient for better performance.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url or AI_SERVICE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            # Configure connection pooling for better performance
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
            )
            logger.info(
                f"Created AI service HTTP client with connection pooling to {self.base_url}"
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def analyze(self, cv_text: str, jd_text: str) -> Dict[str, Any]:
        """Analyze CV against job description."""
        client = await self._get_client()
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
        client = await self._get_client()
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
        client = await self._get_client()
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


async def close_ai_client():
    """Close the AI service client (call on application shutdown)."""
    global _client
    if _client:
        await _client.close()
        _client = None


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
