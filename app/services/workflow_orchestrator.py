"""Orchestrate complete CV optimization workflow."""
from typing import Dict, List, Optional
import logging
from .cv_analyzer import CVAnalyzer
from .cv_optimizer import CVOptimizer
from .cover_letter_gen import CoverLetterGenerator

logger = logging.getLogger(__name__)


class CVWorkflowOrchestrator:
    """Orchestrate the complete CV optimization workflow."""
    
    def __init__(self):
        """Initialize all services."""
        self.analyzer = CVAnalyzer()
        self.optimizer = CVOptimizer()
        self.cover_letter_gen = CoverLetterGenerator()
        logger.info("WorkflowOrchestrator initialized")
    
    def optimize_cv_for_job(
        self,
        cv_text: str,
        jd_text: str,
        generate_cover_letter: bool = True
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
        analysis = self.analyzer.analyze(cv_text, jd_text)
        
        # Step 2: Optimize
        logger.info("Step 2/3: Optimizing CV sections...")
        optimized_cv = self._optimize_cv_sections(cv_text, jd_text, analysis)
        
        # Step 3: Cover letter (optional)
        cover_letter = None
        if generate_cover_letter:
            logger.info("Step 3/3: Generating cover letter...")
            cover_letter = self._generate_cover_letter(analysis, jd_text)
        
        result = {
            'analysis': analysis,
            'optimized_cv': optimized_cv,
            'cover_letter': cover_letter,
            'ats_score': analysis.get('ats_score', 0)
        }
        
        logger.info(f"Workflow completed. ATS Score: {result['ats_score']}")
        return result
    
    def _optimize_cv_sections(
        self,
        cv_text: str,
        jd_text: str,
        analysis: Dict
    ) -> Dict:
        """Optimize individual CV sections based on analysis.
        
        Args:
            cv_text: Original CV text
            jd_text: Job description
            analysis: Analysis results from analyzer
            
        Returns:
            dict: Optimized sections
        """
        # Extract top keywords from analysis
        keywords = []
        if 'keyword_analysis' in analysis:
            matched = analysis['keyword_analysis'].get('matched_keywords', [])
            missing = analysis['keyword_analysis'].get('missing_critical', [])
            
            # Get top 5 matched + top 5 missing
            keywords = [k['keyword'] for k in matched[:5]]
            keywords += [k['keyword'] for k in missing[:5]]
        
        optimized = {}
        
        # TODO: Parse CV sections and optimize each
        # For now, return placeholder
        # You should implement actual section extraction from cv_text
        
        logger.info(f"Optimization completed with {len(keywords)} keywords")
        return optimized
    
    def _generate_cover_letter(
        self,
        analysis: Dict,
        jd_text: str
    ) -> Optional[Dict]:
        """Generate cover letter based on analysis.
        
        Args:
            analysis: CV analysis results
            jd_text: Job description
            
        Returns:
            dict: Cover letter and metadata
        """
        # Extract relevant info from analysis
        # TODO: Implement proper data extraction
        # For now, use placeholder data
        
        candidate_data = {
            'name': 'Ilnar Nizametdinov',
            'current_title': 'Python Backend Developer',
            'location': 'Purmerend, Netherlands',
            'years_exp': '2+',
            'top_skills': ['Python', 'Flask/FastAPI', 'Docker'],
            'achievements': [
                'Automated ETL pipelines with 100% deployment success',
                'Designed Dockerized microservices architecture',
                'Mentored junior developers'
            ]
        }
        
        job_data = {
            'company': 'Target Company',
            'position': 'Backend Developer',
            'location': 'Netherlands',
            'requirements': ['Python', 'Flask', 'Docker', 'PostgreSQL']
        }
        
        return self.cover_letter_gen.generate(candidate_data, job_data)
