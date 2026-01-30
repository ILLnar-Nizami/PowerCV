"""Test ATS score calculation functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workflow_orchestrator import CVWorkflowOrchestrator


@pytest.mark.asyncio
async def test_ats_score_calculation():
    """Test ATS score calculation in workflow orchestrator."""
    # Mock Redis to avoid event loop issues
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.setex = AsyncMock()

    # Create mock analyzer
    mock_analyzer = MagicMock()

    # First analysis (before optimization) - low score
    first_analysis = {
        "ats_score": 32,
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "Python"}, {"keyword": "Teamwork"}],
            "missing_critical": [
                {"keyword": "Kubernetes"},
                {"keyword": "Docker"},
                {"keyword": "AWS"},
            ],
        },
    }

    # Second analysis (after optimization) - higher score
    optimized_analysis = {
        "ats_score": 85,
        "keyword_analysis": {
            "matched_keywords": [
                {"keyword": "Python"},
                {"keyword": "Teamwork"},
                {"keyword": "Docker"},
                {"keyword": "AWS"},
                {"keyword": "Microservices"},
            ],
            "missing_critical": [{"keyword": "Kubernetes"}],
        },
    }

    # Mock the analyzer to return different results (async)
    mock_analyzer.analyze = AsyncMock(side_effect=[first_analysis, optimized_analysis])

    # Create orchestrator with mocked dependencies
    with (
        patch("app.services.workflow_orchestrator.get_redis", return_value=mock_redis),
        patch("app.services.ai_providers.get_redis", return_value=mock_redis),
    ):
        orchestrator = CVWorkflowOrchestrator()
        orchestrator.analyzer = mock_analyzer

        # Mock optimizer to return simple optimized data (async)
        mock_optimizer = MagicMock()
        mock_optimizer.optimize_comprehensive = AsyncMock(
            return_value={
                "user_information": {
                    "name": "Test Candidate",
                    "email": "test@example.com",
                    "profile_description": "Experienced developer",
                    "experiences": [
                        {
                            "job_title": "Developer",
                            "company": "Test Company",
                            "start_date": "2020-01-01",
                            "end_date": "Present",
                            "four_tasks": ["Task 1", "Task 2", "Task 3", "Task 4"],
                        }
                    ],
                    "education": [
                        {
                            "degree": "Bachelor's",
                            "institution": "Test University",
                            "start_date": "2015-09-01",
                            "end_date": "2019-06-01",
                        }
                    ],
                    "skills": {
                        "hard_skills": ["Python", "Docker", "AWS"],
                        "soft_skills": ["Teamwork", "Communication"],
                    },
                }
            }
        )
        orchestrator.optimizer = mock_optimizer

        # Test the optimization workflow
        result = await orchestrator.optimize_cv_for_job(
            cv_text="Original CV content",
            jd_text="Job description text",
            generate_cover_letter=False,
        )

        # Verify ATS score was updated
        assert "ats_score" in result
        assert result["ats_score"] == 85  # Should use the optimized score

        # Verify matching skills were updated
        assert "matching_skills" in result
        assert len(result["matching_skills"]) == 5  # Should have 5 matched skills

        # Verify missing skills were updated
        assert "missing_skills" in result
        assert len(result["missing_skills"]) == 1  # Should have 1 missing skill


@pytest.mark.asyncio
async def test_ats_score_fallback():
    """Test ATS score fallback when optimized analysis fails."""
    # Create mock analyzer
    mock_analyzer = MagicMock()

    # First analysis (before optimization) - low score
    first_analysis = {
        "ats_score": 32,
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "Python"}, {"keyword": "Teamwork"}],
            "missing_critical": [
                {"keyword": "Kubernetes"},
                {"keyword": "Docker"},
                {"keyword": "AWS"},
            ],
        },
    }

    # Mock the analyzer to return first analysis for both calls (async)
    mock_analyzer.analyze = AsyncMock(return_value=first_analysis)

    # Mock Redis to simulate unavailability
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    # Create orchestrator with mocked dependencies - use correct patch path
    with (
        patch("app.services.workflow_orchestrator.get_redis", return_value=mock_redis),
        patch("app.services.ai_providers.get_redis", return_value=mock_redis),
    ):
        orchestrator = CVWorkflowOrchestrator()
        orchestrator.analyzer = mock_analyzer

        # Mock optimizer to raise exception (simulating failure)
        mock_optimizer = MagicMock()
        mock_optimizer.optimize_comprehensive = AsyncMock(
            side_effect=Exception("Optimization failed")
        )
        orchestrator.optimizer = mock_optimizer

        # Test the optimization workflow
        result = await orchestrator.optimize_cv_for_job(
            cv_text="Original CV content",
            jd_text="Job description text",
            generate_cover_letter=False,
        )

        # Should fall back to original score when optimized analysis fails
        assert result["ats_score"] == 32  # Should use the original score as fallback
