"""Test cover letter generation functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.cover_letter_gen import CoverLetterGenerator


@pytest.mark.asyncio
async def test_cover_letter_generator():
    """Test cover letter generator instantiation."""
    # Create generator
    generator = CoverLetterGenerator()
    assert generator is not None


@pytest.mark.asyncio
async def test_workflow_cover_letter_generation():
    """Test cover letter generation in workflow orchestrator."""
    from app.services.workflow_orchestrator import CVWorkflowOrchestrator

    # Mock the cover letter generator
    mock_cover_letter_gen = MagicMock()
    mock_cover_letter_gen.generate = AsyncMock(
        return_value={
            "cover_letter": "Generated cover letter",
            "word_count": 250,
            "tone": "professional",
        }
    )

    # Create orchestrator with mocked generator
    orchestrator = CVWorkflowOrchestrator()
    orchestrator.cover_letter_gen = mock_cover_letter_gen

    # Mock analysis data
    mock_analysis = {
        "ats_score": 75,
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "Python"}],
            "missing_critical": [{"keyword": "Kubernetes"}],
        },
    }

    # Test cover letter generation
    result = await orchestrator._generate_cover_letter(
        mock_analysis, "Job description text"
    )

    assert result is not None
    assert "cover_letter" in result
    assert result["cover_letter"] == "Generated cover letter"
    mock_cover_letter_gen.generate.assert_called_once()
