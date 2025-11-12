# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Open Job Description tools for validating and working with OpenJD templates.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict

try:
    from openjd.model import (
        DecodeValidationError,
        TemplateSpecificationVersion,
        decode_job_template,
        decode_environment_template,
    )

    OPENJD_AVAILABLE = True
except ImportError:
    OPENJD_AVAILABLE = False


def _read_template(path: str) -> Dict[str, Any]:
    """Read a template file (JSON or YAML) and return as a dictionary."""
    file_path = Path(path)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try JSON first, then YAML
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise RuntimeError(f"Failed to parse template file: {e}")


def check_template(
    path: str,
) -> Dict[str, Any]:
    """
    Validates an Open Job Description template file.

    This tool validates Job or Environment template files using the openjd.model
    library and reports any syntax errors in the schema.

    Args:
        path: Path to a Job or Environment template file (JSON or YAML)

    Returns:
        Dictionary containing validation results with status and any errors found

    Raises:
        ValueError: If the path doesn't exist
        RuntimeError: If openjd.model is not installed or template parsing fails
    """
    if not OPENJD_AVAILABLE:
        raise RuntimeError(
            "openjd.model is not installed. Install it with: pip install openjd-model"
        )

    # Validate inputs
    if not os.path.exists(path):
        raise ValueError(f"Template file does not exist: {path}")

    if not os.path.isfile(path):
        raise ValueError(f"Path is not a file: {path}")

    try:
        # Read and parse the template file
        template_object = _read_template(path)

        # Check for specificationVersion
        if "specificationVersion" not in template_object:
            return {
                "status": "invalid",
                "path": path,
                "message": "Template validation failed",
                "error": "Missing field 'specificationVersion'",
            }

        document_version = template_object["specificationVersion"]

        # Validate the version
        try:
            template_version = TemplateSpecificationVersion(document_version)
        except ValueError:
            return {
                "status": "invalid",
                "path": path,
                "message": "Template validation failed",
                "error": f"Unknown template 'specificationVersion' ({document_version})",
            }

        # Decode and validate based on template type
        if TemplateSpecificationVersion.is_job_template(template_version):
            decode_job_template(template=template_object)
        elif TemplateSpecificationVersion.is_environment_template(template_version):
            decode_environment_template(template=template_object)
        else:
            return {
                "status": "invalid",
                "path": path,
                "message": "Template validation failed",
                "error": f"Unknown template 'specificationVersion' ({document_version})",
            }

        # Validation successful
        return {
            "status": "valid",
            "path": path,
            "message": f"Template at '{path}' passes validation checks",
            "specification_version": document_version,
        }

    except DecodeValidationError as e:
        return {
            "status": "invalid",
            "path": path,
            "message": "Template validation failed",
            "error": str(e),
        }
    except RuntimeError as e:
        return {
            "status": "error",
            "path": path,
            "message": "Error reading template",
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "path": path,
            "message": "Unexpected error during validation",
            "error": str(e),
        }
