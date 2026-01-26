"""CV optimization service using AI microservice."""

import logging
import re
from typing import Dict, List, Optional

from .cv_validator import CVValidator

EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

logger = logging.getLogger(__name__)


class CVOptimizer:
    """Optimize CV sections based on job description using AI microservice."""

    def __init__(self):
        """Initialize optimizer."""
        logger.info("CVOptimizer initialized with comprehensive support")

    async def optimize_comprehensive(
        self,
        cv_text: str,
        jd_text: str,
        analysis: Optional[Dict] = None,
        email: Optional[str] = None,
    ) -> Dict:
        """Perform one-shot comprehensive CV optimization.

        Args:
            cv_text: Original CV text
            jd_text: Job description text
            analysis: Preliminary analysis from analyzer

        Returns:
            dict: Fully structured ResumeData JSON
        """
        logger.info("Starting comprehensive one-shot optimization")

        try:
            from .ai_client import get_ai_client

            client = get_ai_client()
            result = await client.optimize(cv_text, jd_text, analysis, email)

            optimized_cv = result.get("optimized_cv", {})

            validation = CVValidator.validate_optimization(cv_text, optimized_cv)
            optimized_cv["_validation"] = validation

            if not validation["valid"]:
                for error in validation["errors"]:
                    logger.error(f"CV Optimization Validation Error: {error}")

            if validation["warnings"]:
                for warning in validation["warnings"]:
                    logger.warning(f"CV Optimization Warning: {warning}")

            logger.info("Comprehensive optimization completed successfully")
            return optimized_cv

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._get_fallback_comprehensive_structure(cv_text, email)

    def optimize_section(
        self,
        original_section: str,
        jd_text: str,
        keywords: List[str],
        optimization_focus: str,
    ) -> Dict:
        """Optimize a specific CV section."""
        logger.info(f"Optimizing CV section with {len(keywords)} keywords")

        return {
            "optimized_content": original_section,
            "keywords_used": keywords,
            "improvements_made": ["Section optimization uses full CV optimization"],
        }

    def optimize_professional_summary(
        self, cv_data: str, jd_text: str, keywords: List[str]
    ) -> Dict:
        """Optimize professional summary section."""
        return {
            "optimized_content": cv_data if isinstance(cv_data, str) else "",
            "keywords_used": keywords,
            "improvements_made": [
                "Professional summary optimization uses full CV optimization"
            ],
        }

    def _get_fallback_comprehensive_structure(
        self, cv_text: str = "", email: Optional[str] = None
    ) -> Dict:
        """Get fallback comprehensive structure."""
        name = "Candidate"

        if not email and cv_text:
            email_match = EMAIL_REGEX.search(cv_text)
            if email_match:
                email = email_match.group()

        if not email:
            email = "please-add-your-email@example.com"

        logger.warning("Using fallback optimization structure")

        return {
            "user_information": {
                "name": name,
                "email": email,
                "phone": "",
                "address": "",
                "profile_description": "Experienced professional with technical expertise.",
                "skills": {"hard_skills": [], "soft_skills": []},
                "experiences": [],
                "education": [],
            },
            "projects": [],
            "certificate": [],
            "extra_curricular_activities": [],
            "_validation": {
                "valid": True,
                "errors": [],
                "warnings": ["Fallback structure used due to AI service unavailable"],
                "original_contact": {},
                "optimized_contact": {},
            },
        }

    def optimize_professional_summary(
        self, cv_data: str, jd_text: str, keywords: List[str]
    ) -> Dict:
        """Optimize professional summary section."""
        return {
            "optimized_content": cv_data if isinstance(cv_data, str) else "",
            "keywords_used": keywords,
            "improvements_made": [
                "Professional summary optimization uses full CV optimization"
            ],
        }

    def _get_fallback_comprehensive_structure(
        self, cv_text: str = "", email: Optional[str] = None
    ) -> Dict:
        """Get fallback comprehensive structure."""
        name = "Candidate"

        if not email and cv_text:
            email_match = EMAIL_REGEX.search(cv_text)
            if email_match:
                email = email_match.group()

        if not email:
            email = "please-add-your-email@example.com"

        logger.warning("Using fallback optimization structure")

        return {
            "user_information": {
                "name": name,
                "email": email,
                "phone": "",
                "address": "",
                "profile_description": "Experienced professional with technical expertise.",
                "skills": {"hard_skills": [], "soft_skills": []},
                "experiences": [],
                "education": [],
            },
            "projects": [],
            "certificate": [],
            "extra_curricular_activities": [],
            "_validation": {
                "valid": True,
                "errors": [],
                "warnings": ["Fallback structure used due to AI service unavailable"],
                "original_contact": {},
                "optimized_contact": {},
            },
        }
