"""AI Service - FastAPI microservice for CV optimization.

This service handles all AI-powered operations:
- CV analysis against job descriptions
- Resume optimization
- Cover letter generation
- ATS scoring
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    cv_text: str
    jd_text: str


class AnalysisResponse(BaseModel):
    ats_score: int
    keyword_analysis: dict
    experience_analysis: dict
    skill_gaps: dict
    strengths: list
    recommendations: list
    summary: str


class OptimizationRequest(BaseModel):
    cv_text: str
    jd_text: str
    analysis: Optional[dict] = None
    email: Optional[str] = None


class OptimizationResponse(BaseModel):
    optimized_cv: dict
    ats_score: int
    original_ats_score: int
    improvement: int


class CoverLetterRequest(BaseModel):
    candidate_data: dict
    job_data: dict
    tone: str = "Professional"


class CoverLetterResponse(BaseModel):
    cover_letter: str
    word_count: int
    tone: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Service starting up...")
    yield
    logger.info("AI Service shutting down...")


app = FastAPI(
    title="PowerCV AI Service",
    description="AI-powered CV analysis and optimization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        # Add your production domains here when deployed
        # "https://yourdomain.com",
        # "https://app.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "powercv-ai"}


@app.post("/api/v2/analyze", response_model=AnalysisResponse)
async def analyze_cv(request: AnalysisRequest):
    """Analyze CV against job description."""
    try:
        from .analyzers.cv import CVAnalyzer

        analyzer = CVAnalyzer()
        result = await analyzer.analyze(request.cv_text, request.jd_text)

        return AnalysisResponse(
            ats_score=result.get("ats_score", 0),
            keyword_analysis=result.get("keyword_analysis", {}),
            experience_analysis=result.get("experience_analysis", {}),
            skill_gaps=result.get("skill_gaps", {}),
            strengths=result.get("strengths", []),
            recommendations=result.get("recommendations", []),
            summary=result.get("summary", ""),
        )
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/optimize", response_model=OptimizationResponse)
async def optimize_cv(request: OptimizationRequest):
    """Optimize CV for a job description."""
    try:
        from .analyzers.cv import CVAnalyzer
        from .optimizers.cv import CVOptimizer

        optimizer = CVOptimizer()
        analyzer = CVAnalyzer()

        analysis = request.analysis
        if not analysis:
            analysis = await analyzer.analyze(request.cv_text, request.jd_text)

        optimized = await optimizer.optimize_comprehensive(
            request.cv_text, request.jd_text, analysis, request.email
        )

        original_score = analysis.get("ats_score", 0)

        optimized_text = _dict_to_text(optimized)
        re_analysis = await analyzer.analyze(optimized_text, request.jd_text)
        new_score = re_analysis.get("ats_score", original_score)

        return OptimizationResponse(
            optimized_cv=optimized,
            ats_score=new_score,
            original_ats_score=original_score,
            improvement=new_score - original_score,
        )
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(request: CoverLetterRequest):
    """Generate a cover letter."""
    try:
        from .generators.cover_letter import CoverLetterGenerator

        generator = CoverLetterGenerator()
        result = await generator.generate(
            request.candidate_data,
            request.job_data,
            request.tone,
        )

        return CoverLetterResponse(
            cover_letter=result.get("cover_letter", ""),
            word_count=result.get("word_count", 0),
            tone=request.tone,
        )
    except Exception as e:
        logger.error(f"Cover letter generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _dict_to_text(cv_dict: dict) -> str:
    """Convert optimized CV dict back to text with comprehensive field handling."""
    lines = []

    ui = cv_dict.get("user_information", {})
    if ui:
        name = ui.get("name", "Candidate")
        lines.append(name.upper())
        lines.append(ui.get("email", ""))
        lines.append(ui.get("phone", ""))
        lines.append("")

        profile = ui.get("profile_description") or ui.get("summary")
        if profile:
            lines.append("PROFESSIONAL SUMMARY")
            lines.append(profile)
            lines.append("")

    skills_data = ui.get("skills", {})
    if skills_data:
        lines.append("SKILLS")
        if isinstance(skills_data, dict):
            hard_skills = skills_data.get("hard_skills", [])
            soft_skills = skills_data.get("soft_skills", [])
            technical_skills = skills_data.get("technical_skills", [])
            all_skills = hard_skills + soft_skills + technical_skills
            if all_skills:
                lines.append(", ".join(all_skills))
        elif isinstance(skills_data, list):
            lines.append(", ".join(skills_data))
        lines.append("")

    experiences = ui.get("experiences", [])
    if experiences:
        lines.append("EXPERIENCE")
        for exp in experiences:
            title = exp.get("job_title", "")
            company = exp.get("company", "")
            dates = ""
            if exp.get("start_date") and exp.get("end_date"):
                dates = f" | {exp.get('start_date')} - {exp.get('end_date')}"
            elif exp.get("start_date"):
                dates = f" | {exp.get('start_date')} - Present"
            lines.append(f"{title} | {company}{dates}")
            
            # Add location if available
            if exp.get("location"):
                lines.append(f"Location: {exp.get('location')}")
                
            tasks = exp.get("four_tasks", []) or exp.get("tasks", []) or exp.get("achievements", [])
            if isinstance(tasks, list):
                for task in tasks:
                    if task:
                        lines.append(f"- {task}")
            lines.append("")

    education = ui.get("education", [])
    if education:
        lines.append("EDUCATION")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            dates = ""
            if edu.get("start_date") and edu.get("end_date"):
                dates = f" | {edu.get('start_date')} - {edu.get('end_date')}"
            elif edu.get("start_date"):
                dates = f" | {edu.get('start_date')} - Present"
            lines.append(f"{degree} | {institution}{dates}")
            
            # Add location if available
            if edu.get("location"):
                lines.append(f"Location: {edu.get('location')}")
        lines.append("")

    # Handle projects section
    projects = cv_dict.get("projects", [])
    if projects:
        lines.append("PROJECTS")
        for project in projects:
            name = project.get("name", "")
            description = project.get("description", "")
            tech_stack = project.get("technologies", []) or project.get("tech_stack", [])
            lines.append(f"{name}")
            if description:
                lines.append(f"Description: {description}")
            if tech_stack:
                lines.append(f"Technologies: {', '.join(tech_stack)}")
            lines.append("")

    # Handle certifications section
    certifications = cv_dict.get("certifications", [])
    if certifications:
        lines.append("CERTIFICATIONS")
        for cert in certifications:
            name = cert.get("name", "")
            issuer = cert.get("issuer", "")
            date = cert.get("date", "")
            lines.append(f"{name} | {issuer}")
            if date:
                lines.append(f"Date: {date}")
            lines.append("")

    # Handle languages section
    languages = ui.get("languages", [])
    if languages:
        lines.append("LANGUAGES")
        if isinstance(languages, list):
            for lang in languages:
                if isinstance(lang, dict):
                    name = lang.get("name", "")
                    proficiency = lang.get("proficiency", "")
                    lines.append(f"{name} - {proficiency}")
                else:
                    lines.append(str(lang))
        elif isinstance(languages, str):
            lines.append(languages)
        lines.append("")

    # Handle additional sections
    for section_name, section_data in cv_dict.items():
        if section_name not in ["user_information", "projects", "certifications"] and section_data:
            lines.append(section_name.upper())
            if isinstance(section_data, list):
                for item in section_data:
                    if isinstance(item, dict):
                        # Handle dict items
                        for key, value in item.items():
                            if value:
                                lines.append(f"{key.replace('_', ' ').title()}: {value}")
                    else:
                        lines.append(str(item))
            elif isinstance(section_data, str):
                lines.append(section_data)
            lines.append("")

    return "\n".join(lines)
