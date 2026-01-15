"""Test cover letter generation functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.cover_letter.ai_generator import AICoverLetterGenerator
from app.services.cover_letter_gen import CoverLetterGenerator

@pytest.mark.asyncio
@patch('app.services.cover_letter.ai_generator.OpenAI')
async def test_ai_cover_letter_generation(mock_openai):
    """Test AI cover letter generation."""
    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Generated cover letter content"))]
    ))
    mock_openai.return_value = mock_client

    # Create generator with mocked client
    generator = AICoverLetterGenerator()

    # Test cover letter generation
    result = await generator.generate_cover_letter(
        resume_text="Test resume content",
        job_description="Test job description",
        company_name="Test Company",
        job_title="Test Position"
    )

    assert result == "Generated cover letter content"
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_cover_letter_generator():
    """Test cover letter generator."""
    # Mock the AI client
    mock_client = MagicMock()
    mock_client.chat_completion = MagicMock(return_value='{"cover_letter": "Test cover letter"}')

    # Create generator with mocked client
    generator = CoverLetterGenerator()
    generator._client = mock_client

    # Test cover letter generation
    result = generator.generate(
        candidate_data={
            "name": "Test Candidate",
            "current_title": "Test Title",
            "location": "Test Location",
            "years_exp": "5",
            "top_skills": ["Python", "JavaScript"],
            "achievements": ["Achievement 1", "Achievement 2"]
        },
        job_data={
            "company": "Test Company",
            "position": "Test Position",
            "location": "Test Location",
            "requirements": ["Requirement 1", "Requirement 2"]
        }
    )

    assert "cover_letter" in result
    assert result["cover_letter"] == "Test cover letter"

@pytest.mark.asyncio
async def test_workflow_cover_letter_generation():
    """Test cover letter generation in workflow orchestrator."""
    from app.services.workflow_orchestrator import CVWorkflowOrchestrator

    # Mock the cover letter generator
    mock_cover_letter_gen = MagicMock()
    mock_cover_letter_gen.generate = MagicMock(return_value={
        "cover_letter": "Generated cover letter",
        "word_count": 250,
        "tone": "professional"
    })

    # Create orchestrator with mocked generator
    orchestrator = CVWorkflowOrchestrator()
    orchestrator.cover_letter_gen = mock_cover_letter_gen

    # Mock analysis data
    mock_analysis = {
        "ats_score": 75,
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "Python"}],
            "missing_critical": [{"keyword": "Kubernetes"}]
        }
    }

    # Test cover letter generation
    result = orchestrator._generate_cover_letter(mock_analysis, "Job description text")

    assert result is not None
    assert "cover_letter" in result
    assert result["cover_letter"] == "Generated cover letter"
    mock_cover_letter_gen.generate.assert_called_once()
