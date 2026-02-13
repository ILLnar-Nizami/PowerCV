"""AI "De-Botting" and Anti-Hallucination Safety Layer.

This module provides:
1. remove_ai_phrases(): Sanitizes text by removing common AI buzzwords
2. validate_master_alignment(): Ensures AI doesn't invent skills/experiences

Based on Resume Matcher pattern: apps/backend/app/services/refiner.py
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Blacklist of AI-generated buzzwords that make resumes sound robotic
AI_BUZZWORDS = [
    # Overused corporate speak
    "synergized",
    "spearheaded",
    "leveraged",
    "utilized",
    "streamlined",
    "optimized",
    "revolutionized",
    "transformed",
    "innovated",
    "orchestrated",
    "championed",
    "spearhead",
    "synergy",
    "leverage",
    "utilization",
    # AI-specific patterns
    "leveraging AI",
    "harnessing the power",
    "cutting-edge",
    "state-of-the-art",
    "best-in-class",
    "world-class",
    "next-generation",
    "end-to-end",
    "mission-critical",
    "value-added",
    # Empty fillers
    "dynamic",
    "proactive",
    "results-driven",
    "goal-oriented",
    "team player",
    "think outside the box",
    "moving forward",
    "at the end of the day",
    # Vague achievements
    "improved efficiency",
    "enhanced performance",
    "increased productivity",
    "reduced costs",
    "maximized output",
    # Overly formal
    "hereby",
    "pursuant to",
    "in accordance with",
    "as per",
    "kindly",
    "please find below",
]

# Regex patterns for phrase detection (word boundary matching)
BUZZWORD_PATTERNS = [
    re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE) for word in AI_BUZZWORDS
]


def remove_ai_phrases(
    text: str, replacement_map: Dict[str, str] = None
) -> Tuple[str, List[str]]:
    """Remove AI buzzwords and replace with human-sounding alternatives.

    This is a fast, cheap post-processing pass that sanitizes AI output
    without requiring additional API calls.

    Args:
        text: Input text to sanitize
        replacement_map: Optional custom replacements (phrase -> human alternative)

    Returns:
        Tuple of (sanitized text, list of removed phrases)
    """
    if not text:
        return text, []

    sanitized = text
    removed = []

    # Apply blacklist patterns
    for pattern in BUZZWORD_PATTERNS:
        matches = pattern.findall(sanitized)
        for match in matches:
            if match.lower() not in removed:
                removed.append(match.lower())
            sanitized = pattern.sub("", sanitized)

    # Apply custom replacements if provided
    if replacement_map:
        for buzzword, replacement in replacement_map.items():
            pattern = re.compile(r"\b" + re.escape(buzzword) + r"\b", re.IGNORECASE)
            sanitized = pattern.sub(replacement, sanitized)

    # Clean up extra whitespace
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = re.sub(r"\s,\s", ", ", sanitized)
    sanitized = sanitized.strip()

    return sanitized, removed


def validate_master_alignment(
    master_data: Dict,
    tailored_data: Dict,
    tolerance: float = 0.15,
) -> Dict[str, any]:
    """Validate that tailored resume doesn't hallucinate content.

    Compares the tailored resume against the "Master Resume" (source of truth)
    to ensure the AI hasn't invented skills, experiences, or qualifications.

    Args:
        master_data: Original master resume as structured dict
        tailored_data: AI-tailored resume to validate
        tolerance: Similarity threshold for fuzzy matching (0.0-1.0)

    Returns:
        Dict with validation results:
        - is_valid: bool
        - hallucinations: List of identified fabrications
        - warnings: List of suspicious content
        - score: Alignment score (0-100)
    """
    hallucinations = []
    warnings = []

    # Extract key fields for comparison
    master_skills = _extract_skills(master_data)
    tailored_skills = _extract_skills(tailored_data)

    master_experiences = _extract_experiences(master_data)
    tailored_experiences = _extract_experiences(tailored_data)

    # Check for skills not in master
    for skill in tailored_skills:
        if not _fuzzy_match(skill, master_skills, tolerance):
            # Distinguish between slight variations vs complete fabrication
            if not _similar_exists(skill, master_skills, tolerance * 1.5):
                hallucinations.append(f"Skill '{skill}' not found in master resume")
            else:
                warnings.append(f"Skill '{skill}' may be a variation of existing skill")

    # Check for experiences not in master
    for exp in tailored_experiences:
        if not _fuzzy_match(exp, master_experiences, tolerance):
            if not _similar_exists(exp, master_experiences, tolerance * 1.5):
                hallucinations.append(f"Experience '{exp}' not found in master resume")

    # Calculate alignment score
    total_elements = len(tailored_skills) + len(tailored_experiences)
    valid_elements = total_elements - len(hallucinations)

    if total_elements > 0:
        score = (valid_elements / total_elements) * 100
    else:
        score = 100

    is_valid = len(hallucinations) == 0

    return {
        "is_valid": is_valid,
        "hallucinations": hallucinations,
        "warnings": warnings,
        "score": round(score, 2),
        "master_skills_count": len(master_skills),
        "tailored_skills_count": len(tailored_skills),
        "elements_validated": total_elements,
    }


def _extract_skills(data: Dict) -> Set[str]:
    """Extract all skills from resume data."""
    skills = set()

    # Handle various skill formats
    if "skills" in data:
        skills_data = data["skills"]
        if isinstance(skills_data, dict):
            for category, skill_list in skills_data.items():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        skills.add(str(skill).lower())
        elif isinstance(skills_data, list):
            for skill in skills_data:
                skills.add(str(skill).lower())

    # Also check hard_skills/soft_skills
    for key in ["hard_skills", "soft_skills", "technical_skills"]:
        if key in data:
            skill_list = data[key]
            if isinstance(skill_list, list):
                for skill in skill_list:
                    skills.add(str(skill).lower())

    return skills


def _extract_experiences(data: Dict) -> Set[str]:
    """Extract company/role names from experience data."""
    experiences = set()

    if "experiences" in data:
        exp_list = data["experiences"]
        if isinstance(exp_list, list):
            for exp in exp_list:
                if isinstance(exp, dict):
                    # Extract company and role
                    if "company" in exp:
                        experiences.add(str(exp["company"]).lower())
                    if "role" in exp or "title" in exp:
                        role = exp.get("role") or exp.get("title")
                        experiences.add(str(role).lower())

    return experiences


def _fuzzy_match(text: str, reference_set: Set[str], threshold: float) -> bool:
    """Check if text fuzzy matches any item in reference set."""
    text_lower = text.lower().strip()

    # Exact match
    if text_lower in reference_set:
        return True

    # Substring match (e.g., "Python" matches "Python Developer")
    for ref in reference_set:
        if text_lower in ref or ref in text_lower:
            return True

    # SequenceMatcher for fuzzy matching
    for ref in reference_set:
        ratio = SequenceMatcher(None, text_lower, ref).ratio()
        if ratio >= threshold:
            return True

    return False


def _similar_exists(text: str, reference_set: Set[str], threshold: float) -> bool:
    """Check if similar text exists in reference set (looser threshold)."""
    return _fuzzy_match(text, reference_set, threshold)


# Human-sounding alternatives for common AI buzzwords
HUMAN_ALTERNATIVES = {
    "synergized": "collaborated",
    "spearheaded": "led",
    "leveraged": "used",
    "utilized": "used",
    "streamlined": "simplified",
    "optimized": "improved",
    "revolutionized": "changed",
    "transformed": "changed",
    "innovated": "created new",
    "orchestrated": "organized",
    "championed": "supported",
    "cutting-edge": "modern",
    "state-of-the-art": "modern",
    "best-in-class": "excellent",
    "world-class": "excellent",
    "next-generation": "new",
    "end-to-end": "complete",
    "mission-critical": "important",
    "value-added": "valuable",
    "dynamic": "active",
    "proactive": "forward-thinking",
    "results-driven": "focused on results",
    "goal-oriented": "focused on goals",
    "team player": "collaborative",
}


def replace_with_human_alternatives(text: str) -> str:
    """Replace AI buzzwords with human-sounding alternatives.

    Args:
        text: Input text with potential AI buzzwords

    Returns:
        Text with buzzwords replaced by human alternatives
    """
    sanitized, _ = remove_ai_phrases(text, HUMAN_ALTERNATIVES)
    return sanitized
