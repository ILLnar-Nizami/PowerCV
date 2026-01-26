"""CV Optimizer - Optimizes CVs for job descriptions."""

import json
import logging
import re
from typing import Any, Dict, Optional

from ..clients.providers import get_ai_client

logger = logging.getLogger(__name__)


class CVOptimizer:
    """Optimizes CV content for specific job descriptions."""

    def __init__(self, provider: str = "cerebras"):
        self.provider = provider
        self.client = get_ai_client(provider)

    async def optimize_comprehensive(
        self,
        cv_text: str,
        jd_text: str,
        analysis: Optional[Dict] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive CV optimization with retry logic.

        Args:
            cv_text: Original CV text
            jd_text: Job description
            analysis: Pre-computed analysis (optional)
            email: Candidate email for the optimized CV

        Returns:
            dict: Optimized CV data structure
        """
        logger.info(
            f"Received CV text length: {len(cv_text)}, JD text length: {len(jd_text)}"
        )

        prompt = self._create_optimization_prompt(cv_text, jd_text, analysis)

        messages = [
            {
                "role": "system",
                "content": "You are an expert resume writer. Optimize CVs to match job descriptions. Output only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            logger.info(f"AI response length: {len(content)}")
            result = self._parse_response(content)

            # Validate result has meaningful content
            if self._is_valid_optimization(result, cv_text):
                return result
            else:
                logger.warning("AI returned incomplete data, using enhanced fallback")
                return self._get_enhanced_fallback(cv_text, email)

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._get_enhanced_fallback(cv_text, email)

    def _is_valid_optimization(self, result: Dict, cv_text: str) -> bool:
        """Check if optimization result has meaningful content."""
        if not result or not isinstance(result, dict):
            return False

        user_info = result.get("user_information", {})
        if not user_info:
            return False

        # Check for basic required fields
        name = user_info.get("name", "").strip()
        profile = user_info.get("profile_description", "").strip()
        experiences = user_info.get("experiences", [])

        # Should have at least a name and some profile content
        has_name = len(name) > 0 and name != "Candidate"
        has_profile = len(profile) > 20
        has_experiences = len(experiences) > 0

        return has_name and (has_profile or has_experiences)

    def _extract_info_from_cv(self, cv_text: str) -> Dict[str, Any]:
        """Extract contact and basic info from original CV text."""
        info = {
            "name": "",
            "email": "",
            "phone": "",
            "address": "",
            "linkedin": "",
            "github": "",
        }

        # Extract email
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", cv_text)
        if email_match:
            info["email"] = email_match.group()

        # Extract phone
        phone_match = re.search(r"[\+\d\s\-\(\)]{10,}", cv_text)
        if phone_match:
            info["phone"] = phone_match.group()

        # Extract name (first line usually)
        lines = cv_text.strip().split("\n")
        if lines:
            info["name"] = lines[0].strip().replace("#", "").strip()

        return info

    def _create_optimization_prompt(
        self, cv_text: str, jd_text: str, analysis: Optional[Dict] = None
    ) -> str:
        """Create the optimization prompt."""
        skill_gaps = ""
        if analysis and "skill_gaps" in analysis:
            gaps = analysis["skill_gaps"]
            critical = gaps.get("critical", [])
            important = gaps.get("important", [])
            skill_gaps = f"Critical skills to highlight: {', '.join(critical)}\n"
            skill_gaps += f"Important skills to add: {', '.join(important)}"

        return f"""
Optimize this CV for the job description. Keep all real information but:
1. Highlight relevant experience and skills
2. Use keywords from the job description
3. Quantify achievements where possible
4. Keep the same structure but improve wording

CV:
{cv_text}

Job Description:
{jd_text}

{skill_gaps}

Return the optimized CV in this JSON format:
{{
    "user_information": {{
        "name": "<extracted name>",
        "email": "<email or empty>",
        "phone": "<phone or empty>",
        "address": "<address or empty>",
        "profile_description": "<improved professional summary>",
        "skills": {{
            "hard_skills": ["<skill1>", "<skill2>"],
            "soft_skills": ["<skill1>", "<skill2>"]
        }},
        "experiences": [
            {{
                "job_title": "<title>",
                "company": "<company>",
                "location": "<location>",
                "start_date": "<start>",
                "end_date": "<end>",
                "four_tasks": ["<achievement1>", "<achievement2>", "<achievement3>", "<achievement4>"]
            }}
        ],
        "education": [
            {{
                "institution": "<school>",
                "degree": "<degree>",
                "location": "<location>",
                "start_date": "<start>",
                "end_date": "<end>"
            }}
        ]
    }},
    "projects": [],
    "certifications": [],
    "languages": []
}}

Only output valid JSON, no markdown. Ensure you include ALL contact information (email, phone, LinkedIn, GitHub) from the original CV.
"""

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse the AI response into a dict."""
        try:
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimization response: {e}")
            return self._get_fallback_optimization("")

    def _get_enhanced_fallback(
        self, cv_text: str, email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return enhanced fallback structure preserving original CV data."""
        extracted = self._extract_info_from_cv(cv_text)

        # Use email from param if provided, otherwise extract from CV
        final_email = email or extracted.get("email", "")

        # Extract profile/summary from CV
        profile = self._extract_profile_from_cv(cv_text)

        # Extract skills from CV
        skills = self._extract_skills_from_cv(cv_text)

        # Extract experiences from CV
        experiences = self._extract_experiences_from_cv(cv_text)

        # Extract education from CV
        education = self._extract_education_from_cv(cv_text)

        logger.warning("Using enhanced fallback optimization with original CV data")

        return {
            "user_information": {
                "name": extracted.get("name", "Candidate"),
                "email": final_email,
                "phone": extracted.get("phone", ""),
                "address": extracted.get("address", ""),
                "profile_description": profile
                or "Experienced professional with technical expertise.",
                "skills": skills,
                "experiences": experiences,
                "education": education,
            },
            "projects": [],
            "certifications": [],
            "languages": [],
        }

    def _get_fallback_optimization(self, cv_text: str) -> Dict[str, Any]:
        """Return basic structure when AI fails - delegate to enhanced fallback."""
        return self._get_enhanced_fallback(cv_text)

    def _extract_profile_from_cv(self, cv_text: str) -> str:
        """Extract professional summary/profile from CV."""
        patterns = [
            r"(?:PROFESSIONAL SUMMARY|SUMMARY|PROFILE|BIO|OBJECTIVE)[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cv_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]
        return ""

    def _extract_skills_from_cv(self, cv_text: str) -> Dict[str, list]:
        """Extract skills from CV."""
        hard_skills = []
        soft_skills = []

        # Common technical skills to look for
        tech_keywords = [
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "angular",
            "vue",
            "django",
            "fastapi",
            "flask",
            "spring",
            "nodejs",
            "express",
            "postgresql",
            "mysql",
            "mongodb",
            "redis",
            "elasticsearch",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "git",
            "github",
            "gitlab",
            "ci/cd",
            "jenkins",
            "github actions",
            "rest api",
            "graphql",
            "microservices",
            "sql",
            "nosql",
            "pandas",
            "numpy",
            "scikit-learn",
            "tensorflow",
            "pytorch",
            "html",
            "css",
            "sass",
            "bootstrap",
            "tailwind",
            "linux",
            "unix",
            "bash",
            "shell",
        ]

        cv_lower = cv_text.lower()
        for skill in tech_keywords:
            if skill in cv_lower:
                # Capitalize properly
                if skill in [
                    "python",
                    "java",
                    "sql",
                    "html",
                    "css",
                    "aws",
                    "gcp",
                    "api",
                    "ci",
                    "cd",
                    "ui",
                    "ux",
                ]:
                    hard_skills.append(skill.upper())
                else:
                    hard_skills.append(skill.title())

        # Remove duplicates
        hard_skills = list(dict.fromkeys(hard_skills))

        return {
            "hard_skills": hard_skills,
            "soft_skills": soft_skills
            or ["Problem Solving", "Communication", "Teamwork"],
        }

    def _extract_experiences_from_cv(self, cv_text: str) -> list:
        """Extract work experience from CV."""
        experiences = []

        # Look for experience section
        exp_pattern = r"(?:EXPERIENCE|WORK EXPERIENCE|PROFESSIONAL EXPERIENCE)[:\s]*\n(.*?)(?=\n\n(?:EDUCATION|SKILLS|PROJECTS)|$)"
        match = re.search(exp_pattern, cv_text, re.IGNORECASE | re.DOTALL)

        if match:
            exp_section = match.group(1)
            # Split by potential job headers
            lines = exp_section.split("\n")
            current_job = {}
            current_tasks = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if this looks like a job header
                if "|" in line and (
                    "Present" in line or "202" in line or len(line) < 80
                ):
                    # Save previous job
                    if current_job and current_tasks:
                        current_job["four_tasks"] = current_tasks
                        experiences.append(current_job)

                    parts = line.split("|")
                    current_job = {
                        "job_title": parts[0].strip(),
                        "company": parts[1].strip() if len(parts) > 1 else "",
                        "location": "",
                        "start_date": "",
                        "end_date": "",
                        "four_tasks": [],
                    }
                    current_tasks = []

                    if len(parts) > 2:
                        dates = parts[2].split("-")
                        if len(dates) >= 1:
                            current_job["start_date"] = dates[0].strip()
                        if len(dates) > 1:
                            current_job["end_date"] = dates[1].strip()
                elif line.startswith("-") or line.startswith("•"):
                    task = line.lstrip("-• ").strip()
                    if task:
                        current_tasks.append(task)
                elif current_job and not current_tasks and not line.upper() == line:
                    current_job["company"] = line

            # Save last job
            if current_job and current_tasks:
                current_job["four_tasks"] = current_tasks
                experiences.append(current_job)

        return experiences

    def _extract_education_from_cv(self, cv_text: str) -> list:
        """Extract education from CV."""
        education = []

        edu_pattern = r"(?:EDUCATION|ACADEMIC|QUALIFICATIONS)[:\s]*\n(.*?)(?=\n\n(?:EXPERIENCE|SKILLS|PROJECTS)|$)"
        match = re.search(edu_pattern, cv_text, re.IGNORECASE | re.DOTALL)

        if match:
            edu_section = match.group(1)
            lines = edu_section.split("\n")

            for line in lines:
                line = line.strip()
                if not line or line.startswith("-") or line.startswith("•"):
                    continue

                # Check if it looks like a degree
                degree_patterns = [
                    r"(Bachelor|Master|PhD|BSc|MSc|BA|MA|B\.?A\.?|M\.?S\.?|Ph\.?D\.?)['\s]*(?:of|in)?['\s]*(.*)",
                    r"(Diploma|Certificate)",
                ]

                for pattern in degree_patterns:
                    deg_match = re.search(pattern, line, re.IGNORECASE)
                    if deg_match:
                        degree = deg_match.group(0)
                        institution = ""

                        # Try to find institution name (usually on same line or next)
                        parts = line.split(degree)
                        if len(parts) > 1:
                            remaining = parts[1].strip()
                            if remaining:
                                institution = remaining.split(",")[0].strip()

                        education.append(
                            {
                                "institution": institution,
                                "degree": degree,
                                "location": "",
                                "start_date": "",
                                "end_date": "",
                            }
                        )
                        break

        return education
