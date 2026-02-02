"""Enrichment Interrogator - AI-powered Resume Enhancement.

This module implements the "Interview Mode" from Resume Matcher, turning
the AI into an interviewer to gather metrics and quantifiable achievements.

Based on Resume Matcher pattern: apps/backend/app/services/improver.py
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WeakPoint:
    """Represents a weak resume bullet point."""

    original_text: str
    issue: str
    question: str
    section: str
    priority: str  # "high", "medium", "low"


class EnrichmentInterrogator:
    """AI-powered resume enrichment through guided questioning.

    Instead of silently rewriting, this interrogator:
    1. Scans for weak/vague bullet points
    2. Generates specific questions to gather metrics
    3. Takes user answers and enhances bullets with real data

    This prevents hallucination by gathering facts from the user.
    """

    # Patterns that indicate weak/vague content
    WEAK_PATTERNS = [
        (r"\bresponsible for\b", "Passive language - use action verbs"),
        (r"\bhelped\b", "Vague contribution - specify impact"),
        (r"\bworked on\b", "Passive language - describe your specific role"),
        (r"\bparticipated in\b", "Passive language - specify your contribution"),
        (r"\bassisted\b", "Vague - quantify your contribution"),
        (r"\bsupported\b", "Vague - specify how you helped"),
        (r"\bimproved\b", "No metrics - by how much?"),
        (r"\benhanced\b", "No metrics - by what percentage?"),
        (r"\boptimized\b", "No metrics - quantify the improvement"),
        (r"\bmanaged\b", "Scope unclear - team size? budget?"),
        (r"\blead\b", "Leadership scope unclear - team size?"),
        (r"\bdeveloped\b", "Scale unclear - users? requests?"),
        (r"\bcreated\b", "Impact unclear - who used it?"),
        (r"\bimplemented\b", "Complexity unclear - what challenges?"),
        (r"\b[dD]uties included\b", "Generic - give specific examples"),
        (r"\bvarious\b", "Vague - name specific items"),
        (r"\bseveral\b", "Vague - give exact number"),
        (r"\bmany\b", "Vague - quantify"),
    ]

    def __init__(self, llm_client=None):
        """Initialize the interrogator.

        Args:
            llm_client: Optional LLM client for advanced analysis
        """
        self.llm = llm_client

    def analyze_weak_points(self, resume_data: Dict) -> List[WeakPoint]:
        """Scan resume for weak/vague bullet points.

        Args:
            resume_data: Structured resume data

        Returns:
            List of identified weak points with questions
        """
        weak_points = []

        # Check experience bullets
        if "experiences" in resume_data:
            for i, exp in enumerate(resume_data.get("experiences", [])):
                if isinstance(exp, dict):
                    section = f"Experience: {exp.get('company', 'Unknown')} - {exp.get('role', '')}"

                    # Check description bullets
                    description = exp.get("description", "")
                    if description:
                        # Handle string description
                        if isinstance(description, str):
                            bullets = description.split("\n")
                        else:
                            bullets = [str(description)]

                        for j, bullet in enumerate(bullets):
                            for pattern, issue in self.WEAK_PATTERNS:
                                if re.search(pattern, bullet, re.IGNORECASE):
                                    question = self._generate_question(bullet, issue)
                                    weak_points.append(
                                        WeakPoint(
                                            original_text=bullet.strip(),
                                            issue=issue,
                                            question=question,
                                            section=section,
                                            priority=self._assess_priority(
                                                bullet, issue
                                            ),
                                        )
                                    )

        # Check skills section
        if "skills" in resume_data:
            skills_data = resume_data["skills"]
            if isinstance(skills_data, dict):
                for category, skills in skills_data.items():
                    if isinstance(skills, list) and len(skills) > 10:
                        weak_points.append(
                            WeakPoint(
                                original_text=f"Skills: {', '.join(skills[:5])}... ({len(skills)} total)",
                                issue="Too many skills listed without context",
                                question=f"For {category} skills, which 3-5 are you most proficient in for this role?",
                                section="Skills Section",
                                priority="low",
                            )
                        )

        return weak_points

    def _generate_question(self, text: str, issue: str) -> str:
        """Generate a specific question to gather missing information.

        Args:
            text: The weak bullet point
            issue: Identified issue

        Returns:
            Specific question to help improve the bullet
        """
        # Check for common patterns and generate targeted questions
        if "metrics" in issue.lower() or "how much" in issue.lower():
            if "improved" in text.lower() or "enhanced" in text.lower():
                return "By what percentage or amount did this improvement occur?"
            if "reduced" in text.lower() or "decreased" in text.lower():
                return "By what percentage or amount did this reduction occur?"
            if "increased" in text.lower() or "grew" in text.lower():
                return "By what percentage or amount did this increase occur?"

        if "team" in issue.lower() or "managed" in text.lower():
            return "How big was the team? How many people did you manage or coordinate?"

        if "scale" in text.lower() or "users" in text.lower():
            return "How many users/requests/transactions did this handle?"

        if "time" in text.lower() or "faster" in text.lower():
            return "How much time was saved? What was the before/after?"

        if "budget" in text.lower() or "cost" in text.lower():
            return "What was the budget size? How much did you save?"

        # Generic questions based on issue
        generic_questions = {
            "Passive language": "What specific action did YOU take? Start with an action verb.",
            "Vague contribution": "What was your specific contribution? Give a concrete example.",
            "No metrics": "Can you quantify this? Use numbers (%, $, users, time, etc.)?",
            "Scope unclear": "What was the scope? Team size? Budget? Timeline?",
            "Generic": "Can you add a specific example or metric to make this concrete?",
        }

        for pattern, q in generic_questions.items():
            if pattern.lower() in issue.lower():
                return q

        return (
            "Can you add more specific details, metrics, or examples to this statement?"
        )

    def _assess_priority(self, text: str, issue: str) -> str:
        """Assess the priority of fixing a weak point."""
        # High priority patterns (most impactful for ATS and recruiters)
        high_priority = ["metrics", "improved", "enhanced", "increased", "reduced"]

        # Check if issue mentions high priority items
        issue_lower = issue.lower()
        for pattern in high_priority:
            if pattern in issue_lower:
                return "high"

        # Check text for common achievements
        if re.search(r"\$[0-9]", text):
            return "medium"  # Already has some metrics

        return "medium"

    def enhance_bullet(
        self,
        original_bullet: str,
        user_answer: str,
        context: Dict = None,
    ) -> str:
        """Enhance a bullet point using user's answer.

        Args:
            original_bullet: Original weak bullet
            user_answer: User's answer to the interrogation question
            context: Additional context (role, company, etc.)

        Returns:
            Enhanced bullet point with user's input incorporated
        """
        if not user_answer or not user_answer.strip():
            return original_bullet

        # Simple enhancement by appending context if user provided it
        # In a full implementation, this would use the LLM
        enhanced = original_bullet.strip()

        # Clean up the answer
        answer = user_answer.strip().rstrip(".")

        # If bullet ends with verb, append the answer as completion
        if enhanced.endswith(("ed", "ing")):
            enhanced = f"{enhanced}, {answer}"
        else:
            # Try to find a natural integration point
            enhanced = f"{enhanced}: {answer}"

        # Ensure proper ending
        if not enhanced.endswith("."):
            enhanced = enhanced.rstrip(",") + "."

        return enhanced

    async def interrogate_async(
        self,
        resume_data: Dict,
        target_role: str,
    ) -> Dict[str, Any]:
        """Async version of interrogation using LLM for advanced analysis.

        Args:
            resume_data: Full resume data
            target_role: Target job role

        Returns:
            Interrogation results with questions and enhancement suggestions
        """
        if self.llm is None:
            # Fall back to pattern-based analysis
            weak_points = self.analyze_weak_points(resume_data)
            return {
                "questions": [
                    {
                        "original_text": wp.original_text,
                        "question": wp.question,
                        "section": wp.section,
                        "priority": wp.priority,
                    }
                    for wp in weak_points
                ],
                "enhancement_suggestions": [],
                "analysis_mode": "pattern-based",
            }

        try:
            # Use LLM for deeper analysis
            prompt = self._get_interrogation_prompt(resume_data, target_role)
            result = await self.llm.agenerate([prompt])

            return {
                "questions": result.get("questions", []),
                "enhancement_suggestions": result.get("suggestions", []),
                "analysis_mode": "llm-based",
            }

        except Exception as e:
            logger.error(f"LLM interrogation failed: {e}")
            # Fall back to pattern-based
            return self.interrogate(resume_data, target_role)

    def interrogate(
        self,
        resume_data: Dict,
        target_role: str,
    ) -> Dict[str, Any]:
        """Synchronous interrogation using pattern matching.

        Args:
            resume_data: Full resume data
            target_role: Target job role

        Returns:
            Interrogation results with questions
        """
        weak_points = self.analyze_weak_points(resume_data)

        # Group by priority
        high_priority = [wp for wp in weak_points if wp.priority == "high"]
        medium_priority = [wp for wp in weak_points if wp.priority == "medium"]
        low_priority = [wp for wp in weak_points if wp.priority == "low"]

        return {
            "high_priority": [
                {
                    "original_text": wp.original_text,
                    "question": wp.question,
                    "section": wp.section,
                }
                for wp in high_priority
            ],
            "medium_priority": [
                {
                    "original_text": wp.original_text,
                    "question": wp.question,
                    "section": wp.section,
                }
                for wp in medium_priority
            ],
            "low_priority": [
                {
                    "original_text": wp.original_text,
                    "question": wp.question,
                    "section": wp.section,
                }
                for wp in low_priority
            ],
            "total_weak_points": len(weak_points),
            "target_role": target_role,
        }

    def _get_interrogation_prompt(
        self,
        resume_data: Dict,
        target_role: str,
    ) -> str:
        """Generate LLM prompt for deep interrogation."""
        return f"""You are an expert interviewer helping improve a resume for a {target_role} role.

Analyze the resume and identify 5-10 specific questions to help gather metrics and achievements.

For each weak bullet point, generate a question that:
1. Asks for specific metrics (%, $, users, time saved, etc.)
2. Clarifies scope (team size, budget, timeline)
3. Requests concrete examples

Return as JSON:
{{
    "questions": [
        {{
            "original_text": "weak bullet here",
            "question": "specific question to ask",
            "section": "which resume section",
            "priority": "high/medium/low"
        }}
    ],
    "suggestions": ["specific enhancement ideas"]
}}

Resume data: {str(resume_data)[:2000]}"""


import re  # Ensure re is imported for pattern matching
