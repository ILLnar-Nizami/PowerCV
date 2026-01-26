"""Cover Letter Generator - Generates personalized cover letters."""

import logging
from typing import Any, Dict

from ..clients.providers import get_ai_client

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generates personalized cover letters."""

    TONES = ["Professional", "Enthusiastic", "Formal", "Casual"]

    def __init__(self, provider: str = "cerebras"):
        self.provider = provider
        self.client = get_ai_client(provider)

    async def generate(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        tone: str = "Professional",
    ) -> Dict[str, Any]:
        """Generate a cover letter.

        Args:
            candidate_data: Candidate information (name, skills, experience, etc.)
            job_data: Job information (company, position, requirements, etc.)
            tone: Tone of the cover letter

        Returns:
            dict: Cover letter and metadata
        """
        if tone not in self.TONES:
            tone = "Professional"

        prompt = self._create_cover_letter_prompt(candidate_data, job_data, tone)

        messages = [
            {
                "role": "system",
                "content": f"You are a professional cover letter writer. Write in a {tone} tone. Output only the cover letter text, no JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            word_count = len(content.split())

            return {
                "cover_letter": content,
                "word_count": word_count,
                "tone": tone,
            }
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return self._get_fallback_cover_letter(candidate_data, job_data, tone)

    def _create_cover_letter_prompt(
        self, candidate_data: Dict[str, Any], job_data: Dict[str, Any], tone: str
    ) -> str:
        """Create the cover letter prompt."""
        name = candidate_data.get("name", "Candidate")
        current_title = candidate_data.get("current_title", "Professional")
        top_skills = candidate_data.get("top_skills", [])[:5]
        achievements = candidate_data.get("achievements", [])[:3]

        company = job_data.get("company", "the company")
        position = job_data.get("position", "the position")
        requirements = job_data.get("requirements", [])[:5]

        achievements_text = ""
        if achievements:
            achievements_text = "\n".join(f"- {a}" for a in achievements)

        skills_text = ", ".join(top_skills) if top_skills else "relevant skills"

        return f"""
Write a cover letter for a job application.

Candidate: {name}
Current Title: {current_title}
Top Skills: {skills_text}
Key Achievements:
{achievements_text}

Company: {company}
Position: {position}
Key Requirements: {", ".join(requirements) if requirements else "As described in the job posting"}

Write a compelling cover letter that:
1. Addresses the hiring manager professionally
2. Highlights how the candidate's skills match the job requirements
3. Mentions specific achievements
4. Shows enthusiasm for the role
5. Ends with a call to action

Keep it to one page, approximately 300-400 words.
"""

    def _get_fallback_cover_letter(
        self, candidate_data: Dict[str, Any], job_data: Dict[str, Any], tone: str
    ) -> Dict[str, Any]:
        """Return a basic cover letter when AI fails."""
        name = candidate_data.get("name", "Candidate")
        company = job_data.get("company", "the company")
        position = job_data.get("position", "the position")

        content = f"""Dear Hiring Manager,

I am writing to express my interest in the {position} position at {company}. With my background and skills, I believe I would be a valuable addition to your team.

I am confident that my experience and qualifications make me a strong candidate for this role. I look forward to the opportunity to discuss how I can contribute to your organization.

Sincerely,
{name}"""

        return {
            "cover_letter": content,
            "word_count": len(content.split()),
            "tone": tone,
        }
