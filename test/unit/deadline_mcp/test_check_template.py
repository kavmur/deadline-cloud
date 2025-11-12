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
                    "script": {
                        "actions": {
                            "onRun": {"command": "echo", "args": ["Hello World"]}
                        }
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_template_yaml)
            temp_path = f.name

        try:
            result = check_template(temp_path)
            assert result["status"] == "valid"
            assert result["specification_version"] == "jobtemplate-2023-09"
        finally:
            Path(temp_path).unlink()
