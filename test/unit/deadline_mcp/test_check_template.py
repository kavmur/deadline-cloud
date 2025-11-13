# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for check_template MCP tool"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

if sys.version_info >= (3, 10):
    from deadline._mcp.tools.openjd import check_template, OPENJD_AVAILABLE
else:
    pytest.skip("MCP dependencies not available on Python before 3.10", allow_module_level=True)


@pytest.mark.skipif(not OPENJD_AVAILABLE, reason="openjd.model not installed")
class TestCheckTemplate:
    """Test the check_template tool."""

    def test_valid_job_template(self):
        """Test validation of a valid job template."""
        valid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "steps": [
                {
                    "name": "TestStep",
                    "script": {"actions": {"onRun": {"command": "echo", "args": ["Hello World"]}}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_template, f)
            temp_path = f.name

        try:
            result = check_template(temp_path)
            assert result["status"] == "valid"
            assert result["path"] == temp_path
            assert "passes validation checks" in result["message"]
            assert result["specification_version"] == "jobtemplate-2023-09"
        finally:
            Path(temp_path).unlink()

    def test_invalid_template_missing_spec_version(self):
        """Test validation of template missing specificationVersion."""
        invalid_template = {
            "name": "TestJob",
            "steps": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_template, f)
            temp_path = f.name

        try:
            result = check_template(temp_path)
            assert result["status"] == "invalid"
            assert "specificationVersion" in result["error"]
        finally:
            Path(temp_path).unlink()

    def test_invalid_template_bad_structure(self):
        """Test validation of template with invalid structure."""
        invalid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            # Missing required 'steps' field
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_template, f)
            temp_path = f.name

        try:
            result = check_template(temp_path)
            assert result["status"] == "invalid"
            assert "error" in result
        finally:
            Path(temp_path).unlink()

    def test_nonexistent_file(self):
        """Test validation with nonexistent file."""
        with pytest.raises(ValueError, match="does not exist"):
            check_template("/nonexistent/path/to/template.json")

    def test_directory_instead_of_file(self):
        """Test validation with directory instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="not a file"):
                check_template(temp_dir)

    def test_yaml_template(self):
        """Test validation of YAML template."""
        valid_template_yaml = """
specificationVersion: jobtemplate-2023-09
name: TestJob
steps:
  - name: TestStep
    script:
      actions:
        onRun:
          command: echo
          args:
            - Hello World
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(valid_template_yaml)
            temp_path = f.name

        try:
            result = check_template(temp_path)
            assert result["status"] == "valid"
            assert result["specification_version"] == "jobtemplate-2023-09"
        finally:
            Path(temp_path).unlink()


@pytest.mark.skipif(not OPENJD_AVAILABLE, reason="openjd.model not installed")
class TestSummarizeJobTemplate:
    """Test the summarize_job_template tool."""

    def test_summarize_basic_job(self):
        """Test summarize of a basic job template."""
        from deadline._mcp.tools.openjd import summarize_job_template

        valid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameters": [
                {
                    "name": "JobParam",
                    "type": "STRING",
                    "default": "default_value",
                }
            ],
            "steps": [
                {
                    "name": "TestStep",
                    "script": {"actions": {"onRun": {"command": "echo", "args": ["Hello World"]}}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_template, f)
            temp_path = f.name

        try:
            result = summarize_job_template(temp_path)
            assert result["status"] == "success"
            assert result["job_name"] == "TestJob"
            assert result["total_steps"] == 1
            assert len(result["steps"]) == 1
            assert result["steps"][0]["name"] == "TestStep"
        finally:
            Path(temp_path).unlink()

    def test_summarize_with_parameters(self):
        """Test summarize with job parameters."""
        from deadline._mcp.tools.openjd import summarize_job_template

        valid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "ParameterizedJob",
            "parameters": [
                {
                    "name": "FrameRange",
                    "type": "STRING",
                }
            ],
            "steps": [
                {
                    "name": "RenderStep",
                    "script": {
                        "actions": {
                            "onRun": {
                                "command": "echo",
                                "args": ["Rendering {{Param.FrameRange}}"],
                            }
                        }
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_template, f)
            temp_path = f.name

        try:
            result = summarize_job_template(temp_path, job_parameters='{"FrameRange": "1-10"}')
            assert result["status"] == "success"
            assert result["job_name"] == "ParameterizedJob"
            assert "FrameRange" in result["parameters"]
        finally:
            Path(temp_path).unlink()

    def test_summarize_specific_step(self):
        """Test summarize for a specific step."""
        from deadline._mcp.tools.openjd import summarize_job_template

        valid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "MultiStepJob",
            "steps": [
                {
                    "name": "Step1",
                    "script": {"actions": {"onRun": {"command": "echo", "args": ["Step 1"]}}},
                },
                {
                    "name": "Step2",
                    "script": {"actions": {"onRun": {"command": "echo", "args": ["Step 2"]}}},
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_template, f)
            temp_path = f.name

        try:
            result = summarize_job_template(temp_path, step="Step1")
            assert result["status"] == "success"
            assert "requested_step" in result
            assert result["requested_step"]["name"] == "Step1"
        finally:
            Path(temp_path).unlink()

    def test_summarize_nonexistent_file(self):
        """Test summarize with nonexistent file."""
        from deadline._mcp.tools.openjd import summarize_job_template

        with pytest.raises(ValueError, match="does not exist"):
            summarize_job_template("/nonexistent/path/to/template.json")

    def test_summarize_invalid_parameters(self):
        """Test summarize with invalid job parameters."""
        from deadline._mcp.tools.openjd import summarize_job_template

        valid_template = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "steps": [
                {
                    "name": "TestStep",
                    "script": {"actions": {"onRun": {"command": "echo", "args": ["Hello"]}}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_template, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                summarize_job_template(temp_path, job_parameters="not valid json")
        finally:
            Path(temp_path).unlink()
