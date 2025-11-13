# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Open Job Description tools for validating and working with OpenJD templates.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from openjd.model import (
        DecodeValidationError,
        TemplateSpecificationVersion,
        decode_job_template,
        decode_environment_template,
        create_job,
        preprocess_job_parameters,
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


def summarize_job_template(
    path: str,
    job_parameters: str = "{}",
    step: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Summarizes a Job Template, displaying information about Steps and Tasks.

    This tool generates a Job from the template and parameters, then provides
    summary information about the job structure.

    Args:
        path: Path to a Job template file (JSON or YAML)
        job_parameters: JSON string of job parameters as a dict (e.g., '{"MyParam": "value"}')
        step: Optional step name to get detailed information about a specific step

    Returns:
        Dictionary containing job summary with steps, tasks, and parameters

    Raises:
        ValueError: If the path doesn't exist or parameters are invalid
        RuntimeError: If openjd.model is not installed or job creation fails
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

    # Parse job parameters
    try:
        job_param_values = json.loads(job_parameters) if job_parameters else {}
        if not isinstance(job_param_values, dict):
            raise ValueError("job_parameters must be a JSON object/dict")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in job_parameters: {e}")

    try:
        # Read and parse the template file
        template_object = _read_template(path)

        # Decode the job template
        job_template = decode_job_template(template=template_object)

        # Preprocess and validate job parameters
        processed_params = preprocess_job_parameters(
            job_template=job_template,
            job_parameter_values=job_param_values,
        )

        # Create the job
        job = create_job(
            job_template=job_template,
            job_parameter_values=processed_params,
        )

        # Build summary information
        job_name = job.get("name", "Unknown")
        parameters = job.get("parameters", {})
        steps = job.get("steps", [])

        # Count total tasks across all steps
        total_tasks = 0
        step_summaries = []

        for step_obj in steps:
            step_name = step_obj.get("name", "Unknown")
            step_params = step_obj.get("parameterSpace", {})

            # Calculate task count for this step
            task_count = 1
            if step_params:
                # Each parameter combination creates a task
                for param_def in step_params.get("taskParameterDefinitions", []):
                    param_range = param_def.get("range", [])
                    if isinstance(param_range, list):
                        task_count *= len(param_range)

            total_tasks += task_count

            step_summary = {
                "name": step_name,
                "task_count": task_count,
                "parameter_count": len(step_params.get("taskParameterDefinitions", [])),
            }

            # Add dependencies if present
            if "dependencies" in step_obj:
                step_summary["dependencies"] = step_obj["dependencies"]

            step_summaries.append(step_summary)

        result = {
            "status": "success",
            "path": path,
            "job_name": job_name,
            "parameters": parameters,
            "total_steps": len(steps),
            "total_tasks": total_tasks,
            "steps": step_summaries,
        }

        # If a specific step was requested, add detailed info
        if step:
            matching_step = next((s for s in step_summaries if s["name"] == step), None)
            if matching_step:
                result["requested_step"] = matching_step
            else:
                result["warning"] = f"Step '{step}' not found in job"

        return result

    except DecodeValidationError as e:
        return {
            "status": "error",
            "path": path,
            "message": "Template validation failed",
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "path": path,
            "message": "Error generating job summary",
            "error": str(e),
        }
