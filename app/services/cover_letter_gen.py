"""Cover letter generation service using AI microservice."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generate cover letters using AI microservice."""

    def __init__(self):
        """Initialize generator."""
        logger.info("CoverLetterGenerator initialized")

    async def generate(
        self, candidate_data: Dict, job_data: Dict, tone: str = "Professional"
    ) -> Dict:
        """Generate a cover letter.

        Args:
            candidate_data: Dictionary containing candidate information
            job_data: Dictionary containing job information
            tone: Tone for the cover letter (Professional, Enthusiastic, Formal)

        Returns:
            dict: Generated cover letter and metadata
        """
        logger.info(f"Generating cover letter with {tone} tone")

        try:
            from .ai_client import get_ai_client

            client = get_ai_client()
            result = await client.generate_cover_letter(candidate_data, job_data, tone)

            return {
                "cover_letter": result.get("cover_letter", ""),
                "word_count": result.get("word_count", 0),
                "tone": tone,
            }

        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return self._get_fallback_result(candidate_data, job_data, tone)

    def _get_fallback_result(
        self, candidate_data: Dict, job_data: Dict, tone: str
    ) -> Dict:
        """Get fallback result structure."""
        name = candidate_data.get("name", "Candidate")
        company = job_data.get("company", "the company")
        position = job_data.get("position", "the position")

        cover_letter = f"""Dear Hiring Manager,

I am writing to express my interest in the {position} position at {company}. With my background and skills, I am confident I can contribute effectively to your team.

Please consider my application. I look forward to the opportunity to discuss how my skills and experience align with your needs.

Best regards,
{name}"""

        return {
            "cover_letter": cover_letter,
            "word_count": len(cover_letter.split()),
            "tone": tone,
        }
