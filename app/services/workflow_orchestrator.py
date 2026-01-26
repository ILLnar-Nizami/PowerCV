"""Orchestrate complete CV optimization workflow."""

import logging
import re
from typing import Dict, List, Optional

from ..utils.shared_utils import TextProcessor
from .cover_letter_gen import CoverLetterGenerator
from .cv_analyzer import CVAnalyzer
from .cv_optimizer import CVOptimizer

logger = logging.getLogger(__name__)


class CVWorkflowOrchestrator:
    """Orchestrate the complete CV optimization workflow."""

    def __init__(self):
        """Initialize all services."""
        self.analyzer = CVAnalyzer()
        self.optimizer = CVOptimizer()
        self.cover_letter_gen = CoverLetterGenerator()
        logger.info("WorkflowOrchestrator initialized")

    async def optimize_cv_for_job(
        self,
        cv_text: str,
        jd_text: str,
        generate_cover_letter: bool = True,
        email: Optional[str] = None,
    ) -> Dict:
        """Complete workflow: analyze → optimize → generate cover letter.

        Args:
            cv_text: Full CV text
            jd_text: Job description text
            generate_cover_letter: Whether to generate cover letter

        Returns:
            dict: Complete results including analysis, optimized CV, cover letter
        """
        logger.info("Starting complete optimization workflow")

        # Step 1: Analyze
        logger.info("Step 1/3: Analyzing CV against job description...")
        analysis = await self.analyzer.analyze(cv_text, jd_text)

        # Step 2: Comprehensive Optimization (One-shot)
        logger.info("Step 2/3: Performing comprehensive optimization...")
        optimized_data = await self.optimizer.optimize_comprehensive(
            cv_text, jd_text, analysis, email
        )

        # Step 3: Cover letter (optional)
        cover_letter = None
        if generate_cover_letter:
            logger.info("Step 3/3: Generating cover letter...")
            cover_letter = await self._generate_cover_letter(analysis, jd_text)

        # Extract skills for the dashboard/API
        matching_skills = analysis.get("keyword_analysis", {}).get(
            "matched_keywords", []
        )
        missing_skills = analysis.get("keyword_analysis", {}).get(
            "missing_critical", []
        )

        # Re-analyze optimized CV to get updated ATS score
        optimized_text = self._dict_to_text(optimized_data)
        logger.info(
            f"Re-analyzing optimized CV for ATS score calculation. Optimized text length: {len(optimized_text)}"
        )

        # Try to get updated ATS score, but fall back to original if rate limited
        try:
            optimized_analysis = await self.analyzer.analyze(optimized_text, jd_text)
            optimized_ats_score = optimized_analysis.get(
                "ats_score", analysis.get("ats_score", 0)
            )
            logger.info(
                f"ATS score before optimization: {analysis.get('ats_score', 'N/A')}"
            )
            logger.info(f"ATS score after optimization: {optimized_ats_score}")
            logger.info(
                f"ATS score improvement: {optimized_ats_score - analysis.get('ats_score', 0)}"
            )
        except Exception as e:
            error_msg = str(e).lower()
            if (
                "429" in error_msg
                or "too many requests" in error_msg
                or "rate limit" in error_msg
            ):
                logger.warning(
                    "Rate limit exceeded on ATS re-analysis, using original score"
                )
                optimized_ats_score = analysis.get("ats_score", 0)
                optimized_analysis = analysis
            else:
                logger.error(f"Error during ATS re-analysis: {str(e)}")
                optimized_ats_score = analysis.get("ats_score", 0)
                optimized_analysis = analysis

        # Update skills from optimized analysis
        optimized_matching_skills = optimized_analysis.get("keyword_analysis", {}).get(
            "matched_keywords", matching_skills
        )
        optimized_missing_skills = optimized_analysis.get("keyword_analysis", {}).get(
            "missing_critical", missing_skills
        )

        result = {
            "analysis": analysis,
            "optimized_cv": optimized_data,  # Now returns the full dict structure
            "cover_letter": cover_letter,
            "ats_score": optimized_ats_score,  # Updated score after optimization
            # Original score
            "original_ats_score": analysis.get("ats_score", 0),
            "matching_skills": [
                k.get("keyword") for k in optimized_matching_skills if k.get("keyword")
            ],
            "missing_skills": [
                k.get("keyword") for k in optimized_missing_skills if k.get("keyword")
            ],
            "recommendation": optimized_analysis.get(
                "summary", analysis.get("summary", "")
            ),
        }

        logger.info(f"Workflow completed. ATS Score: {result['ats_score']}")
        return result

    def _optimize_cv_sections(self, cv_text: str, jd_text: str, analysis: Dict) -> Dict:
        """Optimize individual CV sections based on analysis.

        Args:
            cv_text: Original CV text
            jd_text: Job description
            analysis: Analysis results from analyzer

        Returns:
            dict: Optimized CV sections
        """
        # Extract keywords from analysis
        keywords = []
        if "keyword_analysis" in analysis:
            matched = analysis["keyword_analysis"].get("matched_keywords", [])
            missing = analysis["keyword_analysis"].get("missing_critical", [])

            # Get top keywords for optimization
            keywords = [k["keyword"] for k in matched[:10]]
            if missing:
                keywords += [k["keyword"] for k in missing[:5]]

        # Parse CV into sections and optimize each
        optimized_sections = {}

        # Extract and optimize professional summary first
        summary_section = TextProcessor.extract_section(
            cv_text, ["PROFESSIONAL SUMMARY", "SUMMARY", "PROFILE"]
        )
        if summary_section:
            optimized_summary = self.optimizer.optimize_professional_summary(
                summary_section, jd_text, keywords
            )
            optimized_sections["summary"] = optimized_summary.get(
                "optimized_content", summary_section
            )

        # Extract and optimize experience section
        experience_section = TextProcessor.extract_section(
            cv_text, ["EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE"]
        )
        if experience_section:
            optimized_experience = self.optimizer.optimize_section(
                experience_section, jd_text, keywords, "experience"
            )
            optimized_sections["experience"] = optimized_experience.get(
                "optimized_content", experience_section
            )

        # Extract and optimize skills section
        skills_section = TextProcessor.extract_section(
            cv_text, ["SKILLS", "TECHNICAL SKILLS", "SKILLS & EXPERTISE"]
        )
        if skills_section:
            optimized_skills = self.optimizer.optimize_section(
                skills_section, jd_text, keywords, "skills"
            )
            optimized_sections["skills"] = optimized_skills.get(
                "optimized_content", skills_section
            )

        # Extract education section (preserve as-is, no optimization)
        education_section = TextProcessor.extract_section(
            cv_text, ["EDUCATION", "ACADEMIC", "EDUCATION & CERTIFICATIONS"]
        )
        if education_section:
            optimized_sections["education"] = education_section

        # Preserve contact info (extract and keep as-is)
        contact_info = TextProcessor.extract_contact_info(cv_text)
        if contact_info:
            optimized_sections["contact"] = contact_info

        # Preserve any other sections without optimization
        other_sections = self._extract_other_sections(
            cv_text,
            [
                "PROFESSIONAL SUMMARY",
                "SUMMARY",
                "PROFILE",
                "EXPERIENCE",
                "WORK EXPERIENCE",
                "PROFESSIONAL EXPERIENCE",
                "SKILLS",
                "TECHNICAL SKILLS",
                "SKILLS & EXPERTISE",
                "EDUCATION",
                "ACADEMIC",
                "EDUCATION & CERTIFICATIONS",
            ],
        )
        for section_name, section_content in other_sections.items():
            if section_content.strip():  # Only add non-empty sections
                optimized_sections[section_name.lower().replace(" ", "_")] = (
                    section_content
                )

        logger.info(f"Optimized {len(optimized_sections)} CV sections")
        return optimized_sections

    async def _generate_cover_letter(
        self, analysis: Dict, jd_text: str
    ) -> Optional[Dict]:
        """Generate cover letter based on analysis.

        Args:
            analysis: CV analysis results
            jd_text: Job description

        Returns:
            dict: Cover letter and metadata
        """
        # Extract candidate info from analysis
        candidate_data = {
            "name": self._extract_name_from_analysis(analysis),
            "current_title": self._extract_current_title_from_analysis(analysis),
            "location": self._extract_location_from_analysis(analysis),
            "years_exp": self._extract_experience_from_analysis(analysis),
            "top_skills": self._extract_skills_from_analysis(analysis),
            "achievements": self._extract_achievements_from_analysis(analysis),
        }

        # Extract job info from JD
        job_data = {
            "company": "Target Company",  # This could be extracted from JD
            "position": self._extract_position_from_jd(jd_text),
            "location": self._extract_location_from_jd(jd_text),
            "requirements": self._extract_requirements_from_jd(jd_text),
        }

        return await self.cover_letter_gen.generate(candidate_data, job_data)

    def _extract_other_sections(
        self, cv_text: str, exclude_headers: List[str]
    ) -> Dict[str, str]:
        """Extract all CV sections except specified ones.

        Args:
            cv_text: Full CV text
            exclude_headers: Headers to exclude from extraction

        Returns:
            dict: Mapping of section names to content
        """
        sections = {}
        lines = cv_text.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()

            # Check if this is a section header
            if (
                line
                and len(line) < 50
                and line.isupper()
                and not any(char.isdigit() for char in line)
            ):
                # This looks like a section header
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content)

                # Check if this should be excluded
                should_exclude = any(
                    header in line.upper() for header in exclude_headers
                )
                if not should_exclude:
                    current_section = line
                    current_content = []
                else:
                    current_section = None
                    current_content = []
            elif current_section:
                # Add content to current section
                current_content.append(line)

        # Don't forget the last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _extract_name_from_analysis(self, analysis: Dict) -> str:
        """Extract candidate name from analysis."""
        # Try to find name in experience analysis or other sections
        if "experience_analysis" in analysis:
            relevant_roles = analysis["experience_analysis"].get("relevant_roles", [])
            if relevant_roles:
                return relevant_roles[0].get("title", "").split(" - ")[0] or "Candidate"
        return "Candidate"

    def _extract_current_title_from_analysis(self, analysis: Dict) -> str:
        """Extract current job title from analysis."""
        if "experience_analysis" in analysis:
            relevant_roles = analysis["experience_analysis"].get("relevant_roles", [])
            if relevant_roles:
                return relevant_roles[0].get("title", "Professional")
        return "Professional"

    def _extract_location_from_analysis(self, analysis: Dict) -> str:
        """Extract location from analysis."""
        # Location might not be in analysis, return default
        return "Netherlands"

    def _extract_experience_from_analysis(self, analysis: Dict) -> str:
        """Extract years of experience from analysis."""
        # This is a rough estimate based on roles
        if "experience_analysis" in analysis:
            relevant_roles = analysis["experience_analysis"].get("relevant_roles", [])
            if len(relevant_roles) >= 2:
                return "3+ years"
            elif len(relevant_roles) >= 1:
                return "2+ years"
        return "Experienced"

    def _extract_skills_from_analysis(self, analysis: Dict) -> List[str]:
        """Extract top skills from analysis."""
        skills = []
        if "keyword_analysis" in analysis:
            matched = analysis["keyword_analysis"].get("matched_keywords", [])
            skills = [k.get("keyword", "") for k in matched[:8] if k.get("keyword")]
        return skills

    def _extract_achievements_from_analysis(self, analysis: Dict) -> List[str]:
        """Extract achievements from analysis."""
        achievements = []
        if "experience_analysis" in analysis:
            relevant_roles = analysis["experience_analysis"].get("relevant_roles", [])
            for role in relevant_roles:
                role_achievements = role.get("key_achievements", [])
                if isinstance(role_achievements, str):
                    role_achievements = [role_achievements]
                achievements.extend(role_achievements[:3])
        return achievements[:10]

    def _extract_position_from_jd(self, jd_text: str) -> str:
        """Extract position from job description with improved patterns."""
        lines = jd_text.split("\n")
        patterns = [
            r"(?:position|role|job title|title)\s*:\s*(.*)",
            r"^([^:\n]{5,50}(?:developer|engineer|manager|lead|specialist|architect)[^:\n]*)",
        ]

        for line in lines[:15]:
            line_stripped = line.strip()
            for pattern in patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return "Professional"

    def _extract_location_from_jd(self, jd_text: str) -> str:
        """Extract location from job description with improved detection."""
        # Check for specific Netherlands cities first
        cities = [
            "Amsterdam",
            "Rotterdam",
            "Utrecht",
            "Eindhoven",
            "Purmerend",
            "The Hague",
            "Den Haag",
        ]
        for city in cities:
            if re.search(rf"\b{city}\b", jd_text, re.IGNORECASE):
                return f"{city}, Netherlands"

        if "netherlands" in jd_text.lower():
            return "Netherlands"

        # Look for "Location: ..."
        match = re.search(r"location\s*:\s*(.*)", jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return "Remote/Hybrid"

    def _extract_requirements_from_jd(self, jd_text: str) -> List[str]:
        """Extract key requirements from job description dynamically."""
        requirements = []
        # Common tech keywords
        tech_keywords = [
            "python",
            "docker",
            "kubernetes",
            "flask",
            "fastapi",
            "postgresql",
            "mongodb",
            "aws",
            "gcp",
            "azure",
            "ci/cd",
            "git",
            "rest api",
            "microservices",
            "redis",
            "elasticsearch",
            "kafka",
            "terraform",
            "ansible",
            "jenkins",
            "pytest",
        ]

        # Dynamic extraction of bullet points from a "Requirements" section
        req_match = re.search(
            r"(?:requirements|qualifications|what we are looking for)\s*:?\s*\n(.*?)(?:\n\n|\n[A-Z]|$)",
            jd_text,
            re.IGNORECASE | re.DOTALL,
        )
        if req_match:
            req_text = req_match.group(1)
            bullets = re.findall(r"(?:^|\n)\s*[•\-\*]\s*(.*?)(?=\n|$)", req_text)
            if bullets:
                requirements.extend([b.strip() for b in bullets[:5]])

        # Fallback/Supplemental: Check for tech keywords
        found_tech = []
        for keyword in tech_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", jd_text, re.IGNORECASE):
                found_tech.append(
                    keyword.title() if len(keyword) > 3 else keyword.upper()
                )

        # Combine and deduplicate
        combined = list(dict.fromkeys(requirements + found_tech))
        return combined[:10]

    def _dict_to_text(self, cv_dict: Dict) -> str:
        """Convert optimized CV dict back to text for re-analysis.

        Args:
            cv_dict: Optimized CV data dict

        Returns:
            str: Text representation of the CV
        """
        lines = []

        # User information
        ui = cv_dict.get("user_information", {})
        if ui:
            name = ui.get("name", "Candidate")
            lines.append(name.upper())
            lines.append(ui.get("email", ""))
            lines.append(ui.get("phone", ""))
            lines.append(ui.get("address", ""))
            lines.append("")

            profile = ui.get("profile_description") or ui.get("summary")
            if profile:
                lines.append("PROFESSIONAL SUMMARY")
                lines.append(profile)
                lines.append("")

        # Skills
        skills_data = ui.get("skills", {})
        if skills_data:
            lines.append("SKILLS")
            if isinstance(skills_data, dict):
                hard_skills = skills_data.get("hard_skills", [])
                soft_skills = skills_data.get("soft_skills", [])
                all_skills = hard_skills + soft_skills
                if all_skills:
                    lines.append(", ".join(all_skills))
            elif isinstance(skills_data, list):
                lines.append(", ".join(skills_data))
            lines.append("")

        # Experience
        experiences = ui.get("experiences", [])
        if experiences:
            lines.append("EXPERIENCE")
            for exp in experiences:
                title = exp.get("job_title", "")
                company = exp.get("company", "")
                location = exp.get("location", "")
                start = exp.get("start_date", "")
                end = exp.get("end_date", "")

                header = f"{title}"
                if company:
                    header += f" | {company}"
                if location:
                    header += f" | {location}"
                lines.append(header)

                if start or end:
                    lines.append(f"{start} - {end}")

                tasks = (
                    exp.get("four_tasks", [])
                    or exp.get("tasks", [])
                    or exp.get("achievements", [])
                )
                if isinstance(tasks, list):
                    for task in tasks:
                        if task:
                            lines.append(f"- {task}")
                elif isinstance(tasks, str):
                    lines.append(tasks)
                lines.append("")

        # Projects
        projects = ui.get("projects", [])
        if projects:
            lines.append("PROJECTS")
            for proj in projects:
                name = proj.get("name", "")
                description = proj.get("description", "")
                tech = proj.get("technologies", [])

                lines.append(name)
                if description:
                    lines.append(description)
                if tech:
                    lines.append(f"Technologies: {', '.join(tech)}")
                lines.append("")

        # Education
        education = ui.get("education", [])
        if education:
            lines.append("EDUCATION")
            for edu in education:
                institution = edu.get("institution", "")
                degree = edu.get("degree", "")
                location = edu.get("location", "")
                start = edu.get("start_date", "")
                end = edu.get("end_date", "")

                header = f"{degree}"
                if institution:
                    header += f" | {institution}"
                lines.append(header)
                if location:
                    lines.append(location)
                if start or end:
                    lines.append(f"{start} - {end}")
                lines.append("")

        # Certifications
        certs = ui.get("certifications", [])
        if certs:
            lines.append("CERTIFICATIONS")
            for cert in certs:
                if isinstance(cert, dict):
                    name = cert.get("name", "")
                    issuer = cert.get("issuer", "")
                    date = cert.get("date", "")
                    lines.append(f"{name} - {issuer} ({date})")
                else:
                    lines.append(str(cert))
            lines.append("")

        # Languages
        langs = ui.get("languages", [])
        if langs:
            lines.append("LANGUAGES")
            if isinstance(langs, list):
                lang_strings = []
                for lang in langs:
                    if isinstance(lang, dict):
                        name = lang.get("language", lang.get("name", ""))
                        level = lang.get("proficiency", lang.get("level", ""))
                        lang_strings.append(f"{name} ({level})" if level else name)
                    else:
                        lang_strings.append(str(lang))
                lines.append(", ".join(lang_strings))
            lines.append("")

        return "\n".join(lines)
