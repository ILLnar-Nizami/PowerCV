"""CV Analyzer - Analyzes CV against job descriptions."""

import json
import logging
import re
from typing import Any, Dict, List

from ..clients.providers import get_ai_client

logger = logging.getLogger(__name__)


class CVAnalyzer:
    """Analyzes CVs against job descriptions using AI."""

    def __init__(self, provider: str = "cerebras"):
        self.provider = provider
        self.client = get_ai_client(provider)

    async def analyze(self, cv_text: str, jd_text: str) -> Dict[str, Any]:
        """Analyze CV against job description.

        Args:
            cv_text: The CV/resume text
            jd_text: The job description text

        Returns:
            dict: Analysis results including ATS score, keyword analysis, etc.
        """
        logger.info(
            f"Received CV text length: {len(cv_text)}, JD text length: {len(jd_text)}"
        )

        prompt = self._create_analysis_prompt(cv_text, jd_text)

        messages = [
            {
                "role": "system",
                "content": "You are an expert CV reviewer and ATS (Applicant Tracking System) specialist. Analyze CVs against job descriptions and provide detailed feedback in valid JSON format.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            logger.info(f"AI response length: {len(content)}")
            return self._parse_response(content)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._get_fallback_analysis(cv_text, jd_text)

    def _create_analysis_prompt(self, cv_text: str, jd_text: str) -> str:
        """Create the analysis prompt."""
        return f"""
Analyze the following CV against the job description. Provide a comprehensive analysis in valid JSON format.

CV:
{cv_text}

Job Description:
{jd_text}

Provide analysis in this exact JSON format (no markdown, no comments):
{{
    "ats_score": <integer 0-100>,
    "summary": "<brief summary of the candidate>",
    "keyword_analysis": {{
        "matched_keywords": [{{"keyword": "<skill>", "jd_mentions": <count>, "cv_mentions": <count>}}],
        "missing_critical": [{{"keyword": "<missing skill>", "importance": "<high|medium|low>"}}],
        "missing_nice_to_have": [{{"keyword": "<nice to have skill>", "importance": "<medium|low>"}}]
    }},
    "experience_analysis": {{
        "relevant_roles": [{{"title": "<role>", "company": "<company>", "match_score": <0-10>, "key_achievements": ["<achievement>"]}}],
        "transferable_roles": []
    }},
    "skill_gaps": {{
        "critical": ["<missing critical skills>"],
        "important": ["<missing important skills>"],
        "nice_to_have": ["<nice to have skills>"]
    }},
    "strengths": ["<strength 1>", "<strength 2>"],
    "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}

Important:
- ats_score should be realistic: 60-95 range for most cases
- Be specific about skills and achievements
- Provide actionable recommendations
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
            logger.error(f"Failed to parse analysis response: {e}")
            return {
                "ats_score": 75,
                "summary": "Analysis parsing failed, using fallback",
                "keyword_analysis": {"matched_keywords": [], "missing_critical": []},
                "experience_analysis": {"relevant_roles": []},
                "skill_gaps": {"critical": [], "important": []},
                "strengths": [],
                "recommendations": ["Unable to generate detailed analysis"],
            }

    def _get_fallback_analysis(self, cv_text: str, jd_text: str) -> Dict[str, Any]:
        """Get a basic keyword-based analysis when AI fails."""
        cv_lower = cv_text.lower()

        keywords = self._extract_keywords(jd_text)
        matched = []
        missing = []

        for kw in keywords:
            if kw.lower() in cv_lower:
                matched.append({"keyword": kw, "jd_mentions": 1, "cv_mentions": 1})
            else:
                missing.append({"keyword": kw, "importance": "high"})

        score = min(95, 60 + len(matched) * 3)

        return {
            "ats_score": score,
            "summary": "Basic keyword-based analysis (AI service unavailable)",
            "keyword_analysis": {
                "matched_keywords": matched,
                "missing_critical": missing[:5],
                "missing_nice_to_have": [],
            },
            "experience_analysis": {"relevant_roles": []},
            "skill_gaps": {
                "critical": [m["keyword"] for m in missing[:5]],
                "important": [],
                "nice_to_have": [],
            },
            "strengths": ["Relevant experience detected"],
            "recommendations": ["Enable AI service for detailed analysis"],
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text with comprehensive categories."""
        # Expanded patterns for diverse skill categories
        patterns = [
            # Programming Languages
            r"\b(python|java|javascript|typescript|rust|go|golang|c\+\+|c#|php|ruby|swift|kotlin|scala|perl|bash|powershell)\b",
            
            # Cloud & DevOps
            r"\b(aws|gcp|azure|docker|kubernetes|terraform|ansible|jenkins|gitlab|ci/cd|devops)\b",
            
            # Web Frameworks & Frontend
            r"\b(fastapi|django|flask|react|vue|angular|node\.js|express|spring|laravel|rails|next\.js|nuxt\.js)\b",
            
            # Databases & Storage
            r"\b(postgresql|mongodb|redis|elasticsearch|mysql|sqlite|cassandra|dynamodb|firebase|supabase)\b",
            
            # AI & Machine Learning
            r"\b(ai|machine learning|ml|llm|nlp|deep learning|tensorflow|pytorch|keras|scikit-learn|huggingface|opencv)\b",
            
            # Data Science & Analytics
            r"\b(pandas|numpy|matplotlib|seaborn|jupyter|tableau|power bi|excel|sql|data analysis|statistics)\b",
            
            # Testing & Quality
            r"\b(jest|pytest|cypress|selenium|testing|unit test|integration test|e2e|tdd|bdd)\b",
            
            # Project Management & Methodologies
            r"\b(agile|scrum|kanban|jira|confluence|slack|teams|project management|leadership)\b",
            
            # Security & Compliance
            r"\b(security|authentication|authorization|oauth|jwt|ssl|tls|gdpr|hipaa|compliance)\b",
            
            # Mobile Development
            r"\b(react native|flutter|swift|kotlin|ios|android|mobile|xamarin|cordova)\b",
            
            # Business & Soft Skills
            r"\b(communication|teamwork|problem solving|critical thinking|project management|leadership|mentoring)\b",
            
            # Tools & Platforms
            r"\b(github|git|vscode|intellij|vim|emacs|linux|windows|macos|ubuntu|centos)\b",
        ]

        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(
                [m for m in matches if m.lower() not in [k.lower() for k in keywords]]
            )

        return keywords[:50]  # Increased limit for more comprehensive extraction
