"""Test CV optimization quality and data preservation."""

from app.services.cv_validator import CVValidator


def test_preserve_contact_info():
    """Test that contact information is preserved."""
    original = """
    Name: John Doe
    Email: john.doe@example.com
    Phone: +1 555-123-4567
    Address: 123 Main Street, City, Country
    """

    optimized = """
    John Doe
    Email: different@email.com
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert not validation["valid"]
    assert any("phone" in err.lower() for err in validation["errors"])
    assert any("john.doe@example.com" in err for err in validation["errors"])


def test_no_language_hallucinations():
    """Test that no languages are invented."""
    original = """
    Languages: English (Proficient), Russian (Native), Tatar (Native)
    """

    optimized = """
    Languages: English (Proficient), Russian (Native), French (Fluent)
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert any("french" in warn.lower() for warn in validation["warnings"])


def test_preserve_education():
    """Test education section is preserved."""
    original = """
    EDUCATION
    Master's Degree, Mechanical Engineering - 2005-2010
    Moscow Politechnic University
    
    Bachelor's Degree, Economics - 2010-2013
    NIMB University
    """

    optimized = """
    EDUCATION
    Bachelor's Degree, Computer Science
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert any("master" in err.lower() for err in validation["errors"])


def test_preserve_github_linkedin():
    """Test that GitHub and LinkedIn URLs are preserved."""
    original = """
    Name: John Doe
    LinkedIn: https://linkedin.com/in/johndoe
    GitHub: https://github.com/johndoe
    """

    optimized = """
    John Doe
    LinkedIn: https://linkedin.com/in/johndoe
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert any("github" in err.lower() for err in validation["errors"])


def test_no_skill_hallucinations():
    """Test that skills are not invented."""
    original = """
    Skills:
    - Python, Go, TypeScript
    - Flask, FastAPI
    - Docker, Kubernetes
    """

    optimized = """
    Skills:
    - Python, Go, TypeScript
    - Flask, FastAPI
    - Docker, Kubernetes, Forklift Certified
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert any("forklift" in warn.lower() for warn in validation["warnings"])


def test_certifications_preserved():
    """Test that certifications section is not removed."""
    original = """
    CERTIFICATIONS
    - Python Programming
    - Go Development
    - DevOps Tools
    - Data Science & ML
    """

    optimized = """
    SKILLS
    Python, Go, Docker
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert any("certification" in warn.lower() for warn in validation["warnings"])


def test_valid_optimization_passes():
    """Test that a properly optimized CV passes validation."""
    original = """
    Name: John Doe
    Email: john.doe@example.com
    Phone: +1 555-123-4567
    LinkedIn: https://linkedin.com/in/johndoe
    GitHub: https://github.com/johndoe
    
    EDUCATION
    Master's Degree, Mechanical Engineering
    """

    optimized = """
    John Doe
    john.doe@example.com | +1 555-123-4567
    LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
    
    PROFILE
    Tech professional with expertise in backend development...
    
    EDUCATION
    Master's Degree, Mechanical Engineering
    """

    validation = CVValidator.validate_optimization(original, optimized)

    assert validation["valid"]
    assert len(validation["errors"]) == 0
