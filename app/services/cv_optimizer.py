"""CV optimization service using Cerebras AI."""
import json
import re
from typing import Dict, List
import logging
from .cerebras_client import CerebrasClient
from ..prompts.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class CVOptimizer:
    """Optimize CV sections based on job description using Cerebras AI."""
    
    def __init__(self):
        """Initialize optimizer with Cerebras client and prompt."""
        self.client = CerebrasClient()
        self.loader = PromptLoader()
        self.system_prompt = self.loader.load_prompt('cv_optimizer')
        logger.info("CVOptimizer initialized")
    
    def optimize_section(
        self,
        original_section: str,
        jd_text: str,
        keywords: List[str],
        optimization_focus: str
    ) -> Dict:
        """Optimize a specific CV section.
        
        Args:
            original_section: Original CV section text
            jd_text: Job description text
            keywords: List of target keywords to include
            optimization_focus: Specific optimization instructions
            
        Returns:
            dict: Optimization results with optimized content and metadata
            
        Raises:
            ValueError: If response parsing fails
        """
        logger.info(f"Optimizing CV section with {len(keywords)} keywords")
        
        user_message = f"""
**ORIGINAL CV SECTION:**
{original_section}

**JOB DESCRIPTION:**
{jd_text}

**TARGET KEYWORDS:**
{', '.join(keywords)}

**OPTIMIZATION FOCUS:**
{optimization_focus}
"""
        
        # Call Cerebras API
        response = self.client.chat_completion(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.6,  # Moderate temp for creative optimization
            max_tokens=2000
        )
        
        # Parse JSON response
        try:
            cleaned = self._clean_json_response(response)
            result = json.loads(cleaned)
            
            logger.info(f"Section optimization completed. Keywords used: {len(result.get('keywords_used', []))}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimizer response: {str(e)}")
            logger.debug(f"Raw response: {response[:500]}")
            raise ValueError(f"Failed to parse optimizer response: {str(e)}")
    
    def optimize_professional_summary(
        self,
        cv_data: str,
        jd_text: str,
        keywords: List[str]
    ) -> Dict:
        """Optimize professional summary section.
        
        Args:
            cv_data: CV data (string or dict containing professional summary)
            jd_text: Job description text
            keywords: List of target keywords to include
            
        Returns:
            dict: Optimized professional summary
        """
        # Handle string input (current summary text)
        current_summary = ""
        if isinstance(cv_data, str):
            current_summary = cv_data
        elif isinstance(cv_data, dict):
            current_summary = cv_data.get('professional_summary', '')
            if not current_summary:
                current_summary = cv_data.get('summary', '')
        
        if not current_summary or current_summary.strip() == "":
            # Create a basic summary
            current_summary = "Experienced professional with technical expertise and proven track record."
        
        optimization_focus = (
            "Create a compelling 3-4 line professional summary that highlights "
            "key qualifications, emphasizes target keywords, and targets the "
            "specific role requirements. Focus on achievements and unique value proposition."
        )
        
        return self.optimize_section(
            original_section=f"PROFESSIONAL SUMMARY\n\n{current_summary}",
            jd_text=jd_text,
            keywords=keywords,
            optimization_focus=optimization_focus
        )
    
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
    
    def _extract_optimized_section(self, response: Dict) -> str:
        """Extract just the optimized content from response.
        
        Args:
            response: Full optimization response
            
        Returns:
            str: Optimized section content only
        """
        return response.get('optimized_content', '')
    
    def _parse_optimizer_response(self, response: str) -> Dict:
        """Parse and validate optimizer response.
        
        Args:
            response: Raw response from API
            
        Returns:
            dict: Parsed and validated response
        """
        try:
            cleaned = self._clean_json_response(response)
            result = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ['optimized_content', 'changes_made', 'keywords_used']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing required field in optimizer response: {field}")
                    result[field] = ''
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimizer response: {str(e)}")
            raise ValueError(f"Failed to parse optimizer response: {str(e)}")
