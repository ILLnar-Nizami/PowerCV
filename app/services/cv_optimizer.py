"""CV optimization service using Cerebras AI."""
import json
import re
from typing import Dict, List, Optional
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
        self.comprehensive_prompt = self.loader.load_prompt(
            'comprehensive_optimizer')
        logger.info("CVOptimizer initialized with comprehensive support")

    def optimize_comprehensive(
        self,
        cv_text: str,
        jd_text: str,
        analysis: Optional[Dict] = None
    ) -> Dict:
        """Perform one-shot comprehensive CV optimization.

        Args:
            cv_text: Original CV text
            jd_text: Job description text
            analysis: Preliminary analysis from analyzer

        Returns:
            dict: Fully structured ResumeData JSON
        """
        logger.info("Starting comprehensive one-shot optimization")

        user_message = f"""
**JOB DESCRIPTION:**
{jd_text}

**CANDIDATE CV:**
{cv_text}

**PRELIMINARY ANALYSIS:**
{json.dumps(analysis, indent=2) if analysis else "Not provided"}
"""

        # Call Cerebras API with low temp for structure
        response = self.client.chat_completion(
            system_prompt=self.comprehensive_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=4000
        )

        try:
            cleaned = self._clean_json_response(response)
            result = json.loads(cleaned)
            logger.info("Comprehensive optimization JSON parsed successfully")
            return result
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse comprehensive optimizer response: {str(e)}")
            # If JSON fails, the legacy sanitize logic in the router will handle the fallback
            # but we return the raw string so it can be attempted to be parsed there
            return {"error": "JSON Parse Error", "raw_response": response}

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

            logger.info(
                f"Section optimization completed. Keywords used: {len(result.get('keywords_used', []))}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimizer response: {str(e)}")
            logger.debug(f"Raw response (first 500 chars): {response[:500]}")

            # Try to extract basic info with regex fallback
            try:
                fallback_result = self._fallback_parse(response)
                logger.info("Using fallback parsing method for optimizer")
                return fallback_result
            except Exception as fallback_error:
                logger.error(
                    f"Fallback parsing also failed: {str(fallback_error)}")
                raise ValueError(
                    f"Failed to parse optimizer response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in optimizer: {str(e)}")
            raise ValueError(f"Optimizer error: {str(e)}")

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
        """Remove markdown code fences and cleanup JSON with enhanced error handling.

        Args:
            response: Raw response from API

        Returns:
            str: Cleaned JSON string

        Raises:
            ValueError: If response cannot be cleaned to valid JSON
        """
        if not response or not response.strip():
            raise ValueError("Empty response received from API")

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

        if json_start == -1 or json_end == -1 or json_end <= json_start:
            raise ValueError("No valid JSON object found in response")

        response = response[json_start:json_end+1]

        # Fix common JSON issues with enhanced patterns
        response = response.strip()

        # Fix trailing commas before closing braces/brackets
        response = re.sub(r',\s*}', '}', response)
        response = re.sub(r',\s*\]', ']', response)

        # Fix missing commas between array elements
        response = re.sub(r'}\s*{', '},{', response)
        response = re.sub(r'"\s*"', '","', response)

        # Fix quotes around keys and values
        # Add quotes to unquoted keys
        response = re.sub(r'(\w+):', r'"\1":', response)
        # Add quotes to unquoted values
        response = re.sub(
            r':\s*([^",\[\]\{\}][^",\[\]\{\}]*?)\s*([,\]\}])', r': "\1"\2', response)

        # Remove any remaining markdown
        response = response.replace('```json', '').replace('```', '')

        # Validate basic JSON structure
        if not response.startswith('{') or not response.endswith('}'):
            raise ValueError("Invalid JSON structure after cleaning")

        return response

    def _fallback_parse(self, response: str) -> Dict:
        """Fallback parsing method for malformed JSON responses.

        Args:
            response: Raw response from API

        Returns:
            dict: Basic optimization structure
        """
        import re

        # Initialize basic structure
        optimization_result = {
            "optimized_content": response.strip(),
            "changes_made": "Content extracted with fallback parsing due to JSON errors",
            "keywords_used": [],
            "ats_score_impact": "Unable to determine due to parsing issues",
            "recommendations": ["Review and manually optimize the content"]
        }

        # Try to extract keywords
        keyword_matches = re.findall(
            r'"?keyword"?\s*:\s*"([^"]+)"', response, re.IGNORECASE)
        if keyword_matches:
            optimization_result["keywords_used"] = keyword_matches[:10]

        # Try to extract optimized content
        content_match = re.search(
            r'"?optimized_content"?\s*:\s*"([^"]+)"', response, re.IGNORECASE)
        if content_match:
            optimization_result["optimized_content"] = content_match.group(1)

        return optimization_result

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
            required_fields = ['optimized_content',
                               'changes_made', 'keywords_used']
            for field in required_fields:
                if field not in result:
                    logger.warning(
                        f"Missing required field in optimizer response: {field}")
                    result[field] = ''

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimizer response: {str(e)}")
            raise ValueError(f"Failed to parse optimizer response: {str(e)}")
