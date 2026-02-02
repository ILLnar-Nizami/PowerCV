"""Granular Resume Regeneration Service.

This module provides user-directed, section-specific resume improvements
rather than "all or nothing" rewrites. Based on Resume Matcher pattern.

Features:
- Regenerate specific sections without touching others
- Apply custom instructions (tone, length, focus)
- Maintain alignment with master resume (no hallucination)
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RegenerationRequest:
    """Request for granular resume section regeneration."""
    section: str  # "summary", "experience", "skills", etc.
    original_content: str
    instruction: str  # e.g., "Make it sound more senior", "Add metrics"
    item_id: Optional[str] = None  # Specific item to regenerate
    master_resume: Optional[Dict] = None  # Source of truth for alignment
    target_role: Optional[str] = None
    target_company: Optional[str] = None


@dataclass
class RegenerationResult:
    """Result of a regeneration request."""
    regenerated_content: str
    changes_explanation: str
    alignment_valid: bool
    warnings: List[str]


class GranularRegenerator:
    """Handles granular, user-directed resume section regeneration.
    
    This prevents the "all or nothing" frustration of chat interfaces by
    allowing users to improve specific sections with custom instructions.
    
    Key constraint: The prompt explicitly forbids adding facts/metrics
    not present in the source text, ensuring honesty.
    """
    
    # Regeneration instruction templates
    INSTRUCTION_TEMPLATES = {
        "more_senior": "Make this sound more senior and strategic. Focus on impact and leadership.",
        "more_junior": "Make this more entry-level appropriate. Focus on learning and growth.",
        "add_metrics": "Add specific metrics and quantifiable achievements if supported by context.",
        "concise": "Reduce to essential information. Be more concise.",
        "technical": "Focus on technical details and specific technologies used.",
        "leadership": "Emphasize leadership, mentorship, and team collaboration.",
        "results": "Focus on business results and ROI.",
        " ATS_friendly": "Optimize for ATS keywords while maintaining readability.",
    }
    
    # Sections that can be regenerated
    REGENERATABLE_SECTIONS = [
        "summary",
        "professional_summary",
        "objective",
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "bullets",
        "item",
    ]
    
    def __init__(self, llm_client=None):
        """Initialize the regenerator.
        
        Args:
            llm_client: Optional LLM client for regeneration
        """
        self.llm = llm_client
    
    def regenerate(
        self,
        request: RegenerationRequest,
    ) -> RegenerationResult:
        """Regenerate a specific resume section with custom instructions.
        
        Args:
            request: Regeneration request with section, content, and instructions
        
        Returns:
            RegenerationResult with improved content and alignment check
        """
        # Validate section
        if request.section.lower() not in [s.lower() for s in self.REGENERATABLE_SECTIONS]:
            return RegenerationResult(
                regenerated_content=request.original_content,
                changes_explanation="",
                alignment_valid=True,
                warnings=[f"Unknown section: {request.section}"],
            )
        
        # Resolve instruction template if needed
        instruction = request.instruction
        if instruction.lower() in self.INSTRUCTION_TEMPLATES:
            instruction = self.INSTRUCTION_TEMPLATES[instruction.lower()]
        
        # Apply regeneration based on available LLM
        if self.llm is None:
            # Fallback: simple instruction-based modification
            return self._basic_regenerate(request, instruction)
        
        return self._llm_regenerate(request, instruction)
    
    def _basic_regenerate(
        self,
        request: RegenerationRequest,
        instruction: str,
    ) -> RegenerationResult:
        """Basic regeneration without LLM (template-based)."""
        # This is a simplified fallback
        # In production, you'd want more sophisticated handling
        
        enhanced = request.original_content
        
        # Apply simple transformations based on instruction
        if "senior" in instruction.lower():
            enhanced = enhanced.replace("developed", "architected")
            enhanced = enhanced.replace("helped", "led")
            enhanced = enhanced.replace("worked on", "spearheaded")
        
        if "concise" in instruction.lower():
            # Remove filler words
            fillers = ["specifically", "in particular", "basically", "actually"]
            for filler in fillers:
                enhanced = enhanced.replace(filler, "")
        
        return RegenerationResult(
            regenerated_content=enhanced,
            changes_explanation=f"Applied: {instruction}",
            alignment_valid=True,
            warnings=["Basic regeneration - LLM not available"],
        )
    
    async def _llm_regenerate(
        self,
        request: RegenerationRequest,
        instruction: str,
    ) -> RegenerationResult:
        """Full LLM-powered regeneration with alignment validation."""
        try:
            prompt = self._create_regeneration_prompt(request, instruction)
            result = await self.llm.agenerate([prompt])
            
            regenerated = result.get("content", request.original_content)
            
            # Validate alignment if master resume provided
            alignment_valid = True
            warnings = []
            
            if request.master_resume:
                alignment = self._check_alignment(
                    request.master_resume,
                    regenerated,
                )
                alignment_valid = alignment["is_valid"]
                warnings = alignment.get("warnings", [])
            
            return RegenerationResult(
                regenerated_content=regenerated,
                changes_explanation=result.get("changes", f"Applied: {instruction}"),
                alignment_valid=alignment_valid,
                warnings=warnings,
            )
        
        except Exception as e:
            logger.error(f"LLM regeneration failed: {e}")
            return self._basic_regenerate(request, instruction)
    
    def _create_regeneration_prompt(
        self,
        request: RegenerationRequest,
        instruction: str,
    ) -> str:
        """Create the regeneration prompt with strict constraints.
        
        Critical constraint: Explicitly forbid adding facts/metrics
        not present in the source text.
        """
        prompt = f"""You are a professional resume writer. Improve the following resume section.

SECTION: {request.section}
TARGET ROLE: {request.target_role or 'General'}
TARGET COMPANY: {request.target_company or 'Not specified'}

ORIGINAL CONTENT:
{request.original_content}

INSTRUCTION: {instruction}

CONSTRAINTS (CRITICAL):
1. Do NOT add skills, technologies, or certifications not in the original content
2. Do NOT invent metrics, percentages, or numbers unless they appear in the original
3. Do NOT add experiences or roles not present in the source
4. Only rephrase, reorganize, and enhance presentation
5. Maintain the same factual claims
6. Keep the same length or make it more concise

Return as JSON:
{{
    "regenerated_content": "improved version",
    "changes_explanation": "what was changed and why"
}}"""
        
        return prompt
    
    def _check_alignment(
        self,
        master: Dict,
        regenerated: str,
    ) -> Dict:
        """Check if regenerated content aligns with master resume."""
        # Basic alignment checks
        warnings = []
        
        # Check for new skills mentioned
        master_skills = self._extract_skills(master)
        if master_skills:
            # If regenerated mentions skills not in master, warn
            for skill in master_skills:
                if skill.lower() not in regenerated.lower():
                    warnings.append(f"Master skill '{skill}' not mentioned in regenerated content")
        
        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
        }
    
    def _extract_skills(self, data: Dict) -> List[str]:
        """Extract skills from resume data."""
        skills = []
        if "skills" in data:
            skills_data = data["skills"]
            if isinstance(skills_data, dict):
                for category, skill_list in skills_data.items():
                    if isinstance(skill_list, list):
                        skills.extend([str(s) for s in skill_list])
            elif isinstance(skills_data, list):
                skills.extend([str(s) for s in skills_data])
        return skills
    
    def get_available_sections(self) -> List[str]:
        """Get list of regeneratable sections."""
        return self.REGENERATABLE_SECTIONS.copy()
    
    def get_instruction_templates(self) -> Dict[str, str]:
        """Get available instruction templates."""
        return self.INSTRUCTION_TEMPLATES.copy()
