"""Export utilities for CV and cover letter generation."""

from datetime import datetime
import re


def generate_filename(
    doc_type: str,  # "cv" or "cl"
    first_name: str,
    last_name: str,
    company: str,
    role: str
) -> str:
    """Generate filename according to the naming convention.

    Format: {type}_{initial}.{surname}_{company}_{role}_{date}.pdf

    Args:
        doc_type: "cv" or "cl"
        first_name: First name
        last_name: Last name
        company: Company name
        role: Position title

    Returns:
        str: Generated filename
    """
    initial = first_name[0].lower()
    surname = last_name.lower()
    company_slug = re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')
    role_slug = re.sub(r'[^a-z0-9]+', '-', role.lower()).strip('-')
    date = datetime.now().strftime('%d.%m.%y')

    return f"{doc_type}_{initial}.{surname}_{company_slug}_{role_slug}_{date}.pdf"