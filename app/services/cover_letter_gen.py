"""Cover letter generation service using multi-provider AI."""

import asyncio
import logging
import re
from typing import Dict, List

from ..prompts.prompt_loader import PromptLoader
from ..utils.shared_utils import JSONParser
from .ai_client import get_ai_client

logger = logging.getLogger(__name__)

# Singleton instance and lock for thread-safe initialization
_cover_letter_generator_instance = None
_cover_letter_generator_lock = asyncio.Lock()


class CoverLetterGenerator:
    """Generate cover letters using multi-provider AI."""

    _system_prompt = None

    def __init__(self):
        """Initialize generator."""
        self._client = None
        if CoverLetterGenerator._system_prompt is None:
            loader = PromptLoader()
            CoverLetterGenerator._system_prompt = loader.load_prompt("cover_letter")
        logger.info("CoverLetterGenerator initialized")

    @property
    def client(self):
        """Lazy instantiation of AI client."""
        if self._client is None:
            self._client = get_ai_client()
        return self._client

    def generate(
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

        user_message = f"""
**CANDIDATE INFORMATION:**
Name: {candidate_data.get('name', 'N/A')}
Current Title: {candidate_data.get('current_title', 'N/A')}
Location: {candidate_data.get('location', 'N/A')}
Years of Experience: {candidate_data.get('years_exp', 'N/A')}
Top Skills: {', '.join(candidate_data.get('top_skills', []))}
Key Achievements: {self._format_achievements(candidate_data.get('achievements', []))}

**JOB INFORMATION:**
Company: {job_data.get('company', 'N/A')}
Position: {job_data.get('position', 'N/A')}
Location: {job_data.get('location', 'N/A')}
Requirements: {', '.join(job_data.get('requirements', []))}

**TONE:**
{tone}
"""

        # Call AI API with rate limit handling
        try:
            response = self.client.chat_completion(
                system_prompt=CoverLetterGenerator._system_prompt,
                user_message=user_message,
                temperature=0.7,  # Higher temp for creative writing
                max_tokens=1500,
            )

            # Parse text response with sections
            result = self._parse_cover_letter_response(response, tone)

            logger.info(
                f"Cover letter generated successfully ({len(result.get('cover_letter', ''))} chars)"
            )
            return result

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "too many requests" in error_msg or "rate limit" in error_msg:
                logger.warning("AI service rate limit exceeded for cover letter generation")
                # Return a basic fallback instead of retrying
                return {
                    "cover_letter": f"Dear Hiring Manager,\n\nI am writing to express my interest in the {job_data.get('position', 'position')} role at {job_data.get('company', 'Company')}. With my background and skills, I am confident I can contribute effectively to your team.\n\nPlease consider my application. I look forward to the opportunity to discuss how my skills and experience align with your needs.\n\nBest regards,\n{candidate_data.get('name', 'Candidate')}",
                    "word_count": 100,
                    "tone": tone,
                }
            else:
                logger.error(f"Error generating cover letter: {str(e)}")
                return self._get_fallback_result(tone)

    def _format_achievements(self, achievements: List[str]) -> str:
        """Format achievements list for the prompt.

        Args:
            achievements: List of achievement strings

        Returns:
            str: Formatted achievements text
        """
        if not achievements:
            return "No specific achievements provided"

        return "\n".join(f"- {achievement}" for achievement in achievements)

    async def generate_cover_letter(
        self,
        resume_content: str,
        company: str,
        position: str,
        job_description: str = "",
    ) -> str:
        """Generate a cover letter from resume content and job details.

        Args:
            resume_content: The full text content of the resume
            company: Company name
            position: Job position title
            job_description: Optional job description text

        Returns:
            str: Generated cover letter text
        """
        try:
            logger.info(f"Generating cover letter for {position} at {company}")

            # Create a simple prompt for cover letter generation
            # Limit resume content to first 2000 chars to avoid token limits
            truncated_resume = resume_content[:2000]
            truncated_job_desc = job_description[:1000] if job_description else ""

            user_message = f"""
Based on the following resume content, generate a professional cover letter for the position of {position} at {company}.

**RESUME CONTENT:**
{truncated_resume}

**JOB DETAILS:**
Company: {company}
Position: {position}
{f"Job Description: {truncated_job_desc}" if truncated_job_desc else ""}

**INSTRUCTIONS:**
- Write a compelling, professional cover letter
- Highlight relevant skills and experience from the resume
- Keep it concise (200-300 words)
- Use a professional tone
- Address the hiring manager appropriately
- End with a strong call to action

Generate the complete cover letter text:
"""

            # Call AI API without blocking the event loop
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat_completion(
                    system_prompt="You are an expert career counselor who writes compelling cover letters. Generate well-structured, professional cover letters that highlight relevant experience and skills.",
                    user_message=user_message,
                    temperature=0.7,
                    max_tokens=1000,
                ),
            )

            # Extract the cover letter text
            if isinstance(response, dict) and "content" in response:
                cover_letter = response["content"].strip()
            else:
                cover_letter = str(response).strip()

            # Clean up any markdown formatting
            cover_letter = re.sub(r"^[#*`\[\]]+", "", cover_letter, flags=re.MULTILINE)
            cover_letter = cover_letter.strip()

            if not cover_letter:
                cover_letter = f"Dear Hiring Manager,\n\nI am writing to express my interest in the {position} position at {company}. With my background in the relevant field, I am confident I can contribute effectively to your team.\n\nPlease consider my application. I look forward to the opportunity to discuss how my skills and experience align with your needs.\n\nBest regards,\n[Your Name]"

            logger.info(
                f"Cover letter generated successfully ({len(cover_letter)} chars)"
            )
            return cover_letter

        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            # Return a basic fallback cover letter
            return f"Dear Hiring Manager,\n\nI am excited to apply for the {position} position at {company}. My background and skills make me a strong candidate for this role.\n\nI would welcome the opportunity to discuss how I can contribute to your team.\n\nBest regards,\n[Your Name]"

    def _parse_cover_letter_response(self, response: str, tone: str) -> Dict:
        """Parse the cover letter response text into structured format.

        Args:
            response: Raw response from AI
            tone: Requested tone

        Returns:
            dict: Parsed cover letter data
        """
        try:
            # Extract cover letter from between markers
            cover_letter_match = re.search(
                r"=== FINAL COVER LETTER ===(.*?)(?:===|$)",
                response,
                re.DOTALL | re.IGNORECASE
            )

            if cover_letter_match:
                cover_letter = cover_letter_match.group(1).strip()
                # Clean up any extra markers
                cover_letter = re.sub(r"=== .*? ===", "", cover_letter, flags=re.IGNORECASE).strip()
            else:
                # Fallback: use the whole response as cover letter
                cover_letter = response.strip()

            # Count words (rough estimate)
            word_count = len(cover_letter.split())

            return {
                "cover_letter": cover_letter,
                "word_count": word_count,
                "tone": tone,
            }

        except Exception as e:
            logger.error(f"Error parsing cover letter response: {str(e)}")
            return self._get_fallback_result(tone)

    def _get_fallback_result(self, tone: str) -> Dict:
        """Get fallback result structure.

        Args:
            tone: Requested tone for the cover letter

        Returns:
            dict: Fallback result structure
        """
        return {
            "cover_letter": "Unable to generate cover letter due to parsing error.",
            "word_count": 0,
            "tone": tone,
        }


async def get_cover_letter_generator() -> CoverLetterGenerator:
    """Get singleton instance of CoverLetterGenerator to avoid repeated setup.

    Uses async lock to ensure thread-safe initialization under concurrent load.
    """
    global _cover_letter_generator_instance

    if _cover_letter_generator_instance is None:
        async with _cover_letter_generator_lock:
            # Double-check pattern to avoid race conditions
            if _cover_letter_generator_instance is None:
                _cover_letter_generator_instance = CoverLetterGenerator()

    return _cover_letter_generator_instance
