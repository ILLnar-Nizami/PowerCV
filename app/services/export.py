"""Export utilities for CV and cover letter generation."""

import re
from datetime import datetime


def parse_name_from_cv_text(cv_text: str) -> tuple[str, str]:
    """Parse first and last name from CV text.

    Assumes the name is on the first non-empty line.
    Takes first part as first_name, last part as last_name.

    Args:
        cv_text: The CV text content

    Returns:
        tuple: (first_name, last_name)
    """
    lines = cv_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line:
            # Split by whitespace
            parts = line.split()
            if len(parts) >= 2:
                return parts[0], parts[-1]
            elif len(parts) == 1:
                return parts[0], ""
    return "John", "Doe"  # fallback


def generate_filename(
    doc_type: str,  # "cv" or "cl"
    first_name: str,
    last_name: str,
    company: str,
    role: str,
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
    company_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    role_slug = re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_")
    date = datetime.now().strftime("%d.%m.%y")

    return f"{doc_type}_{initial}.{surname}_{company_slug}_{role_slug}_{date}.pdf"
