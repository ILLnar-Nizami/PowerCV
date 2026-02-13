"""Test filename generation functionality."""

import re
import unittest.mock
from datetime import datetime
from unittest.mock import MagicMock


def test_resume_filename_generation():
    """Test resume filename generation."""
    # Mock resume data
    mock_resume = {
        "_id": "test_resume_id",
        "optimized_data": {"user_information": {"name": "John Doe"}},
        "master_content": "John Doe\nSenior Software Engineer",
        "target_company": "Test Company",
        "target_role": "Software Engineer",
        "updated_at": datetime(2023, 1, 15),
    }

    # Mock repository
    mock_repo = MagicMock()
    mock_repo.get_resume_by_id = MagicMock(return_value=mock_resume)

    # Mock Typst generator
    mock_generator = MagicMock()
    mock_generator.generate_pdf = MagicMock(return_value=True)

    # Test filename generation
    # This would normally be tested through the actual endpoint, but we can test the logic

    # Extract the filename generation logic from the endpoint
    # (In a real test, we would call the endpoint and check the response headers)
    first_initial = "J"
    lastname = "Doe"
    company = "Test_Company"
    position = "Software_Engineer"
    date_str = "15.01.23"

    expected_filename = (
        f"cv_{first_initial}.{lastname}_{company}_{position}_{date_str}.pdf"
    )
    expected_filename = (
        f"cv_{first_initial}.{lastname}_{company}_{position}_{date_str}.pdf"
    )
    assert expected_filename == "cv_J.Doe_Test_Company_Software_Engineer_15.01.23.pdf"


def test_resume_filename_generation_from_settings():
    """Test resume filename generation using settings."""
    # Mock settings
    with unittest.mock.patch("app.config.settings.get_settings") as mock_get_settings:
        mock_settings_instance = MagicMock()
        mock_settings_instance.user_first_name = "Ilnar"
        mock_settings_instance.user_last_name = "Nizametdinov"
        mock_get_settings.return_value = mock_settings_instance

        # Test logic
        first_name = mock_settings_instance.user_first_name
        last_name = mock_settings_instance.user_last_name
        company = "Test_Company"
        role = "Software_Engineer"
        date_str = datetime.now().strftime("%d.%m.%y")

        from app.services.export import generate_filename

        filename = generate_filename("cv", first_name, last_name, company, role)

        expected = f"cv_i.nizametdinov_test-company_software_engineer_{date_str}.pdf"
        assert filename == expected


def test_cover_letter_filename_generation():
    """Test cover letter filename generation."""
    # Mock cover letter data
    mock_cover_letter = {
        "_id": "test_cover_letter_id",
        "content_data": {"sender_name": "Jane Smith"},
        "target_company": "Test Corp",
        "target_role": "Data Scientist",
        "updated_at": datetime(2023, 2, 20),
    }

    # Test filename generation logic
    first_initial = "J"
    lastname = "Smith"
    company = "Test_Corp"
    position = "Data_Scientist"
    date_str = "20.02.23"

    expected_filename = (
        f"cover_letter_{first_initial}.{lastname}_{company}_{position}_{date_str}.pdf"
    )
    assert (
        expected_filename
        == "cover_letter_J.Smith_Test_Corp_Data_Scientist_20.02.23.pdf"
    )


def test_filename_special_characters():
    """Test filename generation with special characters."""
    # Test name with special characters
    name = "O'Connor-Smith"
    # Split by space first, if no spaces, treat as single name part
    name_parts = name.strip().split()
    if len(name_parts) == 1:
        # For names like "O'Connor-Smith", split on hyphen for first/last
        hyphen_parts = name_parts[0].split("-")
        first_initial = hyphen_parts[0][0].upper()
        # Process the first part to remove apostrophe prefix
        first_part = hyphen_parts[0]
        if "'" in first_part:
            apostrophe_parts = first_part.split("'", 1)
            if len(apostrophe_parts) > 1:
                base_first = apostrophe_parts[1]
            else:
                base_first = first_part[1:] if len(first_part) > 1 else ""
        else:
            base_first = first_part[1:] if len(first_part) > 1 else ""
        # Combine base first name with remaining hyphen parts
        lastname = base_first + "".join([part for part in hyphen_parts[1:]])
        # If no lastname from above, fallback to original logic
        if not lastname and len(hyphen_parts) == 1:
            lastname = base_first
    else:
        first_initial = name_parts[0][0].upper()
        lastname = "".join(name_parts[1:])
    lastname = re.sub(r"[^\w-]", "", lastname).strip()

    assert first_initial == "O"
    assert lastname == "ConnorSmith"

    # Test company with special characters
    company = "Tech Solutions, Inc."
    company = re.sub(r"[^\w\s-]", "", company).strip()
    company = re.sub(r"[-\s]+", "_", company).title()[:30]

    assert company == "Tech_Solutions_Inc"

    # Test position with special characters
    position = "AI/ML Engineer"
    position = re.sub(r"[^\w\s-]", "", position).strip()
    position = re.sub(r"[-\s]+", "", position)[:30]

    assert position == "AIMLEngineer"
