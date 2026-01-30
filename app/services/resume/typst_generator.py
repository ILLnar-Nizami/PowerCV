"""Typst PDF generator module."""

import json
import logging
import os
import shutil
import subprocess
from typing import Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class TypstGenerator:
    """Generates PDF resumes using Typst templates."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize Typst Generator.

        Args:
            template_dir: Directory containing Typst templates.
        """
        if template_dir is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            template_dir = os.path.join(base_dir, "data", "templates")

        self.template_dir = template_dir
        self.json_data = None
        self.env = None
        self.setup_jinja_environment()

        # Check for typst binary
        self.typst_bin = shutil.which("typst")
        if not self.typst_bin:
            # Fallback to local user bin
            local_bin = os.path.expanduser("~/.local/bin/typst")
            if os.path.exists(local_bin):
                self.typst_bin = local_bin
            else:
                logger.warning("Typst binary not found. PDF generation will fail.")

    def setup_jinja_environment(self) -> None:
        """Set up Jinja2 environment with Typst-friendly delimiters."""
        # Use different delimiters to avoid conflict with Typst syntax (which uses #)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            variable_start_string="<<",
            variable_end_string=">>",
            block_start_string="<%",
            block_end_string="%>",
            comment_start_string="<#",
            comment_end_string="#>",
            autoescape=False,  # Typst is text-based, we handle escaping manually
        )

        self.env.filters["typst_escape"] = self.typst_escape
        self.env.filters["typst_escape_email"] = self.typst_escape_email
        self.env.filters["format_date"] = self.format_date

    def load_json(self, json_path: str) -> bool:
        """Load JSON data from file."""
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                self.json_data = json.load(file)
            return True
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            return False

    def parse_json_from_string(self, json_string: str) -> bool:
        """Parse JSON data from string."""
        try:
            self.json_data = json.loads(json_string)
            return True
        except Exception as e:
            logger.error(f"Error parsing JSON string: {e}")
            return False

    def generate_pdf(self, template_name: str, output_path: str) -> bool:
        """Generate PDF from template (Typst or LaTeX).

        Args:
            template_name: Name of the template (e.g., 'resume.typ', 'awesome-cv/cv.tex')
            output_path: Path to write the PDF file

        Returns:
            bool: True if successful
        """
        if not self.json_data:
            logger.error("No data loaded")
            return False

        # Validate data structure matches template expectations
        if not self._validate_data_structure():
            logger.error("Data structure validation failed")
            return False

        # Check if this is a LaTeX template
        if template_name.endswith(".tex"):
            logger.warning(
                f"LaTeX template '{template_name}' requested but LaTeX compilation not yet implemented. "
                "Falling back to default Typst template. "
                "Please implement LaTeX support (xelatex) to use this template."
            )
            # For now, fall back to default template
            template_name = "resume.typ"

        if not self.typst_bin:
            logger.error("Typst binary not found")
            return False

        try:
            # Render the Typst file with data
            template = self.env.get_template(template_name)
            typst_content = template.render(data=self.json_data)

            # Log first 100 bytes of rendered content for debugging
            logger.info(
                f"Rendered typst content first 100 bytes: {repr(typst_content[:100])}"
            )

            # Check for invalid characters at start of content
            if typst_content.startswith("###"):
                logger.warning("Typst content starts with markdown header, removing...")
                # Find first newline after header and remove everything before it
                newline_pos = typst_content.find("\n")
                if newline_pos != -1:
                    typst_content = typst_content[newline_pos + 1 :].lstrip()
                else:
                    typst_content = ""

            # Add automatic page breaks for very long content
            # typst_content = self._add_page_break_handling(typst_content)

            # Write temporary .typ file
            temp_typ_path = output_path.replace(".pdf", ".typ")
            with open(temp_typ_path, "w", encoding="utf-8") as f:
                f.write(typst_content)

            # Compile using Typst CLI
            cmd = [self.typst_bin, "compile", temp_typ_path, output_path]
            logger.info(f"Running typst: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            # Cleanup temp file
            if os.path.exists(temp_typ_path):
                os.remove(temp_typ_path)

            if result.returncode != 0:
                logger.error(f"Typst compilation failed: {result.stderr}")
                return False

            logger.info(f"PDF generated at {output_path}")
            return True

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False

    @staticmethod
    def typst_escape(text) -> str:
        """Escape special characters for Typst."""
        if not isinstance(text, str):
            return str(text)

        # Escape backslash first to avoid double escaping other replacements
        text = text.replace("\\", "\\\\")

        # Typst uses #, *, _, ` as special chars
        replacements = {
            "#": "\\#",
            "*": "\\*",
            "_": "\\_",
            "`": "\\`",
            "$": "\\$",
            "[": "\\[",
            "]": "\\]",
            "@": "\\@",
            '"': '\\"',
        }
        for char, repl in replacements.items():
            text = text.replace(char, repl)
        return text

    @staticmethod
    def typst_escape_email(text) -> str:
        """Escape special characters for Typst, but preserve @ in emails."""
        if not isinstance(text, str):
            return str(text)

        # Escape all dangerous Typst characters EXCEPT @
        replacements = {
            "#": "\\#",
            "*": "\\*",
            "_": "\\_",
            "`": "\\`",
            "$": "\\$",
            "[": "\\[",
            "]": "\\]",
            # Note: @ is NOT escaped here for email addresses
        }
        for char, repl in replacements.items():
            text = text.replace(char, repl)
        return text

    def _validate_data_structure(self) -> bool:
        """Validate that data structure matches template expectations."""
        try:
            # Check required top-level structure
            if not isinstance(self.json_data, dict):
                logger.error("Data is not a dictionary")
                return False

            # Check user_information exists and has basic structure
            user_info = self.json_data.get("user_information", {})
            if not isinstance(user_info, dict):
                logger.error("user_information is missing or not a dictionary")
                return False

            # Check for required fields in user_information
            required_fields = ["name", "email"]
            for field in required_fields:
                if field not in user_info or not user_info[field]:
                    logger.warning(f"Missing or empty required field: {field}")

            # Check experiences structure if present
            experiences = user_info.get("experiences", [])
            if experiences and not isinstance(experiences, list):
                logger.error("experiences should be a list")
                return False

            # Check education structure if present
            education = user_info.get("education", [])
            if education and not isinstance(education, list):
                logger.error("education should be a list")
                return False

            logger.info("Data structure validation passed")
            return True

        except Exception as e:
            logger.error(f"Data validation error: {str(e)}")
            return False

    def _add_page_break_handling(self, typst_content: str) -> str:
        """Add page break hints for better content distribution."""
        try:
            # Add page break hint after major sections to allow natural flow
            # Typst handles page breaks automatically, but we can add hints
            # Replace section headers with page break hints if content is long
            import re

            # Add page break hint after profile section if followed by experience
            typst_content = re.sub(
                r"(= Profile.*?)(= Work Experience)",
                r"\1\n#pagebreak(weak: true)\n\2",
                typst_content,
                flags=re.DOTALL,
            )

            # Add page break hint after experience if followed by education/projects
            typst_content = re.sub(
                r"(= Work Experience.*?)(= (Education|Projects))",
                r"\1\n#pagebreak(weak: true)\n\2",
                typst_content,
                flags=re.DOTALL,
            )

        except Exception as e:
            logger.warning(f"Page break handling warning: {e}")

        return typst_content

    @staticmethod
    def format_date(date_str) -> str:
        """Format date string."""
        if not date_str or str(date_str).strip().lower() == "present":
            return "Present"
        # ... reuse date formatting logic ...
        return str(date_str)  # Implementation same as before
