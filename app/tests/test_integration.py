"""Integration tests for CV optimization workflow."""
import pytest
from app.services.workflow_orchestrator import CVWorkflowOrchestrator
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """Get test data directory path."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_cv(test_data_dir):
    """Load sample CV."""
    with open(test_data_dir / "sample_cv.txt", 'r') as f:
        return f.read()


@pytest.fixture
def sample_jd(test_data_dir):
    """Load sample job description."""
    with open(test_data_dir / "sample_jd.txt", 'r') as f:
        return f.read()


def test_cv_analysis(sample_cv, sample_jd):
    """Test CV analysis functionality."""
    from app.services.cv_analyzer import CVAnalyzer
    
    analyzer = CVAnalyzer()
    result = analyzer.analyze(sample_cv, sample_jd)
    
    # Assertions
    assert 'ats_score' in result
    assert 0 <= result['ats_score'] <= 100
    assert 'keyword_analysis' in result
    assert 'matched_keywords' in result['keyword_analysis']
    
    print(f" Analysis test passed. ATS Score: {result['ats_score']}")


def test_full_workflow(sample_cv, sample_jd):
    """Test complete optimization workflow."""
    orchestrator = CVWorkflowOrchestrator()
    
    result = orchestrator.optimize_cv_for_job(
        cv_text=sample_cv,
        jd_text=sample_jd,
        generate_cover_letter=False  # Skip for faster testing
    )
    
    # Assertions
    assert 'analysis' in result
    assert 'optimized_cv' in result
    assert result['ats_score'] > 0
    
    print(f" Workflow test passed. ATS Score: {result['ats_score']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
