"""Test rate limit handling functionality."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_providers import AIClient
from app.services.workflow_orchestrator import CVWorkflowOrchestrator
from app.services.cover_letter_gen import CoverLetterGenerator
import requests.exceptions

@patch('app.services.ai_providers.get_settings')
def test_ai_client_rate_limit(mock_get_settings):
    """Test AI client handles rate limit errors properly."""
    # Mock settings with API key
    mock_settings = MagicMock()
    mock_settings.cerebras_api_key = "test_key"
    mock_get_settings.return_value = mock_settings

    # Create AI client
    client = AIClient("cerebras")

    # Mock requests.post to return 429 status
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        # Test that rate limit error is properly handled
        with pytest.raises(requests.exceptions.RequestException) as exc_info:
            client.chat_completion(
                system_prompt="Test system",
                user_message="Test user message"
            )

        assert "rate limit exceeded" in str(exc_info.value).lower()

def test_workflow_orchestrator_rate_limit_fallback():
    """Test workflow orchestrator falls back gracefully on rate limit."""
    # Create orchestrator
    orchestrator = CVWorkflowOrchestrator()

    # Mock analyzer to raise rate limit error on second call
    mock_analyzer = MagicMock()
    first_analysis = {
        "ats_score": 32,
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "Python"}],
            "missing_critical": [{"keyword": "Kubernetes"}]
        }
    }
    mock_analyzer.analyze = MagicMock(side_effect=[
        first_analysis,  # First call succeeds
        requests.exceptions.RequestException("rate limit exceeded")  # Second call fails
    ])
    orchestrator.analyzer = mock_analyzer

    # Mock optimizer
    mock_optimizer = MagicMock()
    mock_optimizer.optimize_comprehensive = MagicMock(return_value={
        "user_information": {
            "name": "Test Candidate",
            "email": "test@example.com"
        }
    })
    orchestrator.optimizer = mock_optimizer

    # Test that workflow completes despite rate limit
    result = orchestrator.optimize_cv_for_job(
        cv_text="Original CV content",
        jd_text="Job description text",
        generate_cover_letter=False
    )

    # Should use original score when rate limited
    assert result["ats_score"] == 32

def test_cover_letter_rate_limit_fallback():
    """Test cover letter generation falls back gracefully on rate limit."""
    # Create cover letter generator
    generator = CoverLetterGenerator()

    # Mock client to raise rate limit error
    mock_client = MagicMock()
    mock_client.chat_completion = MagicMock(side_effect=
        requests.exceptions.RequestException("rate limit exceeded")
    )
    generator._client = mock_client

    # Test that fallback cover letter is generated
    result = generator.generate(
        candidate_data={
            "name": "Test Candidate",
            "current_title": "Test Title",
            "location": "Test Location",
            "years_exp": "5",
            "top_skills": ["Python", "JavaScript"],
            "achievements": ["Achievement 1"]
        },
        job_data={
            "company": "Test Company",
            "position": "Test Position",
            "location": "Test Location",
            "requirements": ["Requirement 1"]
        }
    )

    # Should return fallback cover letter
    assert "cover_letter" in result
    assert len(result["cover_letter"]) > 0
    assert "Test Candidate" in result["cover_letter"]
    assert "Test Company" in result["cover_letter"]
