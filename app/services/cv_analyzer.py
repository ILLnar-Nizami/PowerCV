"""CV analysis service using AI microservice."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class CVAnalyzer:
    """Analyze CV against job description using AI microservice."""

    def __init__(self):
        """Initialize analyzer."""
        logger.info("CVAnalyzer initialized")

    async def analyze(self, cv_text: str, jd_text: str) -> Dict:
        """Analyze CV against job description.

        Args:
            cv_text: Full CV text
            jd_text: Job description text

        Returns:
            dict: Analysis results with ATS score, keywords, gaps, etc.
        """
        if not cv_text or not cv_text.strip():
            raise ValueError("CV text cannot be empty")
        if not jd_text or not jd_text.strip():
            raise ValueError("Job description text cannot be empty")

        logger.info("Starting CV analysis")

        try:
            from .ai_client import get_ai_client

            client = get_ai_client()
            result = await client.analyze(cv_text, jd_text)

            ats_score = result.get("ats_score", 50)
            analysis = {
                "ats_score": ats_score,
                "summary": result.get("summary", ""),
                "keyword_analysis": result.get("keyword_analysis", {}),
                "experience_analysis": result.get("experience_analysis", {}),
                "skill_gaps": result.get("skill_gaps", {}),
                "strengths": result.get("strengths", []),
                "recommendations": result.get("recommendations", []),
            }

            logger.info(f"Analysis completed. ATS Score: {ats_score}")
            return analysis

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._get_fallback_analysis()

    def _get_fallback_analysis(self) -> Dict:
        """Get fallback analysis structure with meaningful defaults."""
        return {
            "ats_score": 50,
            "summary": "Resume analysis completed with limited features.",
            "keyword_analysis": {
                "matched_keywords": [],
                "missing_critical": [],
                "missing_nice_to_have": [],
            },
            "experience_analysis": {
                "relevant_roles": [],
                "transferable_roles": [],
            },
            "skill_gaps": {
                "critical": [],
                "important": [],
                "nice_to_have": [],
            },
            "strengths": [],
            "recommendations": [
                "AI service unavailable. Please try again later.",
            ],
        }
