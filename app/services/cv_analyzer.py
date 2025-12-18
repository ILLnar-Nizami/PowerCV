"""CV analysis service using Cerebras AI."""
import json
import re
from typing import Dict
import logging
from .cerebras_client import CerebrasClient
from ..prompts.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class CVAnalyzer:
    """Analyze CV against job description using Cerebras AI."""
    
    def __init__(self):
        """Initialize analyzer with Cerebras client and prompt."""
        self.client = CerebrasClient()
        self.loader = PromptLoader()
        self.system_prompt = self.loader.load_prompt('cv_analyzer')
        logger.info("CVAnalyzer initialized")
    
    def analyze(self, cv_text: str, jd_text: str) -> Dict:
        """Analyze CV against job description.
        
        Args:
            cv_text: Full CV text
            jd_text: Job description text
            
        Returns:
            dict: Analysis results with ATS score, keywords, gaps, etc.
            
        Raises:
            ValueError: If response parsing fails
        """
        logger.info("Starting CV analysis")
        
        user_message = f"""
**JOB DESCRIPTION:**
{jd_text}

**CANDIDATE CV:**
{cv_text}
"""
        
        # Call Cerebras API
        response = self.client.chat_completion(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.5,  # Lower temp for structured output
            max_tokens=2500
        )
        
        # Parse JSON response
        try:
            cleaned = self._clean_json_response(response)
            analysis = json.loads(cleaned)
            
            logger.info(f"Analysis completed. ATS Score: {analysis.get('ats_score', 'N/A')}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analyzer response: {str(e)}")
            logger.debug(f"Raw response: {response[:500]}")
            raise ValueError(f"Failed to parse analyzer response: {str(e)}")
    
    def _clean_json_response(self, response: str) -> str:
        """Remove markdown code fences and cleanup JSON.
        
        Args:
            response: Raw response from API
            
        Returns:
            str: Cleaned JSON string
        """
        response = response.strip()
        
        # Remove ```json and ``` markers
        if response.startswith('```'):
            lines = response.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response = '\n'.join(lines)
        
        # Find JSON object boundaries
        json_start = response.find('{')
        json_end = response.rfind('}')
        
        if json_start >= 0 and json_end > json_start:
            response = response[json_start:json_end+1]
        
        return response.strip()
