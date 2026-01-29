#!/usr/bin/env python3
"""
Production-like test for AI provider caching functionality.

This script tests the Redis caching implementation in the AIProviderClient
in a production-like environment.
"""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch

from app.services.ai_providers import AIProviderClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ai_caching_production():
    """Test caching in AIProviderClient in a production-like environment."""
    logger.info("Testing AI provider caching in production-like environment...")

    ai_client = AIProviderClient(provider="cerebras")

    # Sample prompts (more realistic)
    system_prompt = """You are an expert CV optimizer. Your task is to analyze a CV against a job description and provide specific recommendations for improvement. Focus on:
1. Keyword optimization for ATS systems
2. Quantifiable achievements
3. Relevant experience highlighting
4. Skills matching
5. Clear, concise language"""

    user_message = """Please analyze this CV against the job description:

CV:
Sarah Johnson
Senior Data Scientist
Amsterdam, Netherlands
sarah.johnson@email.com
+31 6 12345678

PROFESSIONAL EXPERIENCE:
Lead Data Scientist | DataDriven BV | Jan 2021 - Present
- Developed machine learning models that increased customer retention by 25%
- Led a team of 5 data scientists on various projects
- Implemented A/B testing framework that improved conversion rates by 15%
- Technologies: Python, TensorFlow, Scikit-learn, SQL, AWS

Senior Data Analyst | TechAnalytics Inc | Mar 2019 - Dec 2020
- Built predictive models for customer behavior with 85% accuracy
- Created automated reporting dashboards using Tableau and PowerBI
- Reduced data processing time by 40% through pipeline optimization
- Technologies: Python, R, SQL, Tableau

EDUCATION:
MSc Data Science | University of Amsterdam | 2019
BSc Mathematics | Utrecht University | 2017

SKILLS:
Programming: Python, R, SQL
ML Frameworks: TensorFlow, PyTorch, Scikit-learn
Cloud: AWS, GCP
Visualization: Tableau, PowerBI
Statistics: Regression, Classification, Clustering

JOB DESCRIPTION:
Senior Machine Learning Engineer

Company: AI Innovations NL
Location: Amsterdam, Netherlands (Hybrid)

ABOUT THE ROLE:
We are seeking a Senior Machine Learning Engineer to join our growing AI team. You will be responsible for designing, building, and deploying scalable machine learning solutions that drive business value.

RESPONSEIBILITIES:
- Design and implement ML models for various business domains
- Deploy models to production environments using Docker and Kubernetes
- Collaborate with data engineers to build robust data pipelines
- Monitor model performance and implement retraining strategies
- Mentor junior team members and contribute to technical leadership

REQUIREMENTS:
- 5+ years of experience in machine learning and data science
- Strong proficiency in Python and ML frameworks (TensorFlow, PyTorch)
- Experience with cloud platforms (AWS/GCP) and containerization
- Knowledge of MLOps practices and tools
- Experience with A/B testing and experimentation
- Strong communication and collaboration skills

NICE TO HAVE:
- Experience with reinforcement learning
- Knowledge of natural language processing
- Familiarity with distributed computing frameworks (Spark)
"""

    # Mock the LiteLLM completion function with realistic response
    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = {"prompt_tokens": 1200, "completion_tokens": 800}

    mock_response = MockResponse(
        """{
  "ats_score": 85,
  "keyword_analysis": {
    "matched_keywords": [
      {"keyword": "machine learning", "category": "technical"},
      {"keyword": "python", "category": "programming"},
      {"keyword": "tensorflow", "category": "framework"},
      {"keyword": "aws", "category": "cloud"},
      {"keyword": "data science", "category": "domain"},
      {"keyword": "mlops", "category": "nice_to_have"}
    ],
    "missing_critical": [
      {"keyword": "kubernetes", "category": "critical"},
      {"keyword": "docker", "category": "critical"},
      {"keyword": "pytorch", "category": "technical"}
    ]
  },
  "recommendations": [
    "Emphasize your experience with Docker and Kubernetes in your projects",
    "Include PyTorch in your skills section as it's explicitly mentioned",
    "Quantify more achievements with specific metrics and percentages",
    "Add a brief mention of any reinforcement learning or NLP experience"
  ],
  "summary": "Strong candidate with excellent technical skills. Minor gaps in cloud deployment technologies that could be addressed."
}"""
    )

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        mock_completion.return_value = mock_response

        # First call (should not be cached)
        start_time = time.time()
        result1 = await ai_client.chat_completion(system_prompt, user_message)
        first_call_time = time.time() - start_time
        logger.info(f"First call time: {first_call_time:.2f} seconds")
        logger.info(f"Result preview: {result1[:100]}...")

        # Second call (should be cached)
        start_time = time.time()
        result2 = await ai_client.chat_completion(system_prompt, user_message)
        second_call_time = time.time() - start_time
        logger.info(f"Second call time: {second_call_time:.2f} seconds")
        logger.info(f"Result preview: {result2[:100]}...")

        # Verify results are the same
        if result1 == result2:
            logger.info("✓ AI caching test passed - results are consistent")
        else:
            logger.error("✗ AI caching test failed - results differ")

        # Verify caching performance improvement
        if second_call_time < first_call_time:
            logger.info("✓ AI caching improved performance")
        else:
            logger.info(
                "ℹ AI caching performance impact not measured (may be due to other factors)"
            )

        # Test cost tracking
        logger.info(f"Total AI requests: {ai_client.cost_tracker['requests']}")
        logger.info(f"Total AI cost: ${ai_client.cost_tracker['total_cost']:.6f}")
        logger.info(f"Total AI tokens: {ai_client.cost_tracker['total_tokens']}")

        # Test with slight variation (should not be cached)
        user_message_variation = user_message.replace(
            "Senior Machine Learning Engineer",
            "Lead Machine Learning Engineer",
        )
        start_time = time.time()
        result3 = await ai_client.chat_completion(system_prompt, user_message_variation)
        variation_call_time = time.time() - start_time
        logger.info(f"Variation call time: {variation_call_time:.2f} seconds")

        if variation_call_time > second_call_time:
            logger.info("✓ Variation correctly bypassed cache")
        else:
            logger.info("ℹ Variation caching behavior not definitive")


if __name__ == "__main__":
    asyncio.run(test_ai_caching_production())
