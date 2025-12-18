"""Cerebras AI API client wrapper."""
import os
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class CerebrasClient:
    """Wrapper for Cerebras AI API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize Cerebras client.
        
        Args:
            api_key: Cerebras API key (defaults to env variable)
            api_base: API base URL (defaults to env variable)
            model: Model name (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        self.api_base = api_base or os.getenv("CEREBRAS_API_BASE", "https://api.cerebras.ai/v1")
        self.model = model or os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")
        
        if not self.api_key:
            raise ValueError(
                "CEREBRAS_API_KEY not found. "
                "Set it in .env file or pass as parameter."
            )
        
        logger.info(f"Initialized Cerebras client with model: {self.model}")
    
    def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 60
    ) -> str:
        """Send chat completion request to Cerebras.
        
        Args:
            system_prompt: System instructions for the model
            user_message: User's input message
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            str: Model's response text
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            logger.debug(f"Sending request to Cerebras API: {url}")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            logger.debug(f"Received response ({len(content)} chars)")
            return content
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {timeout}s")
            raise Exception(f"Cerebras API request timed out after {timeout}s")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cerebras API error: {str(e)}")
            raise Exception(f"Cerebras API error: {str(e)}")
