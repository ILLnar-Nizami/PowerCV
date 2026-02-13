"""Universal Resume-Job Scorer.

Provider-agnostic resume scoring using the universal LLM interface.
"""

import logging
from typing import Dict, List, Optional

from ..llm.universal import get_llm

logger = logging.getLogger(__name__)


class UniversalResumeScorer:
    """Universal resume scorer that works with any LLM provider."""

    def __init__(self, **llm_config):
        """Initialize the scorer with LLM configuration."""
        self.llm = get_llm(**llm_config)

    async def calculate_match_score(
        self, resume_text: str, job_description: str, user_id: Optional[str] = None
    ) -> Dict:
        """Calculate match score between resume and job description.

        Args:
            resume_text: The resume text
            job_description: The job description
            user_id: Optional user ID for tracking

        Returns:
            Dictionary with score and analysis
        """
        try:
            result = await self.llm.analyze_match(
                resume_text=resume_text,
                job_description=job_description,
                temperature=0.1,
            )

            # Ensure all required fields exist
            return {
                "score": min(100, max(0, int(result.get("score", 50)))),
                "matching_skills": self._ensure_list(result.get("matching_skills", [])),
                "missing_skills": self._ensure_list(result.get("missing_skills", [])),
                "recommendation": str(result.get("recommendation", ""))[:500],
                "rationale": str(result.get("rationale", ""))[:500],
                "user_id": user_id,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error in resume scoring: {e}")
            return {
                "score": 50,
                "matching_skills": [],
                "missing_skills": [],
                "recommendation": "Scoring failed. Please try again.",
                "rationale": f"Error: {str(e)}",
                "user_id": user_id,
                "success": False,
            }

    async def score_resume(
        self, resume_text: str, job_description: str, user_id: Optional[str] = None
    ) -> Dict:
        """Score a resume against a job description.

        Args:
            resume_text: The resume text
            job_description: The job description
            user_id: Optional user ID for tracking

        Returns:
            Dictionary with score and analysis in the format expected by the API
        """
        try:
            match_result = await self.calculate_match_score(
                resume_text, job_description, user_id
            )

            return {
                "ats_score": match_result.get("score", 50.0),
                "readability_score": 75.0,  # Default readability score
                "keyword_density": {},
                "strengths": ["Good formatting"],
                "weaknesses": ["Missing keywords"],
                "recommendations": ["Add more skills"],
                "matching_skills": match_result.get("matching_skills", []),
                "missing_skills": match_result.get("missing_skills", []),
                "keyword_analysis": {
                    "matching": match_result.get("matching_skills", []),
                    "missing": match_result.get("missing_skills", []),
                },
            }

        except Exception as e:
            logger.error(f"Error in resume scoring: {e}")
            return {
                "ats_score": 50.0,
                "readability_score": 50.0,
                "keyword_density": {},
                "strengths": [],
                "weaknesses": ["Scoring failed"],
                "recommendations": ["Please try again"],
                "matching_skills": [],
                "missing_skills": [],
                "keyword_analysis": {},
            }

    def _ensure_list(self, value) -> List[str]:
        """Ensure the value is a list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value if item]
        elif isinstance(value, str):
            return [value]
        else:
            return [str(value)] if value else []


# Convenience function for backward compatibility
async def compute_match_score(
    resume_text: str,
    job_description: str,
    weights: Optional[Dict] = None,
    user_id: Optional[str] = None,
    **llm_config,
) -> Dict:
    """Compute match score between resume and job description."""
    scorer = UniversalResumeScorer(**llm_config)
    return await scorer.calculate_match_score(resume_text, job_description, user_id)
