"""Tests for app.sh shell script."""

import os
import subprocess

import pytest


class TestAppShellScript:
    """Test app.sh shell script functionality."""

    @pytest.fixture
    def script_path(self):
        """Return path to app.sh script."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.sh")

    def test_script_exists(self, script_path):
        """Test that app.sh exists."""
        assert os.path.exists(script_path), f"Script not found at {script_path}"

    def test_script_is_executable(self, script_path):
        """Test that app.sh is executable."""
        assert os.access(script_path, os.X_OK), "Script is not executable"

    def test_help_command(self, script_path):
        """Test help command outputs usage information."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "logs" in result.stdout

    def test_unknown_command(self, script_path):
        """Test unknown command shows error."""
        result = subprocess.run(
            [script_path, "invalid_command"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Unknown" in result.stdout or "Unknown" in result.stderr

    def test_banner_displays_power_cv(self, script_path):
        """Test banner contains POWER CV."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )
        # Banner should appear in output
        assert "POWER CV" in result.stdout or "PowerCV" in result.stdout

    def test_help_shows_all_commands(self, script_path):
        """Test all commands are documented in help."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )

        expected_commands = [
            "start",
            "stop",
            "restart",
            "status",
            "logs",
            "rebuild",
            "help",
        ]

        for cmd in expected_commands:
            assert cmd in result.stdout, f"Command {cmd} not in help output"

    def test_help_shows_environment_variables(self, script_path):
        """Test environment variables are documented."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )

        expected_vars = [
            "FRONTEND_PORT",
            "BACKEND_PORT",
            "POSTGRES_PORT",
            "REDIS_PORT",
            "MONGODB_PORT",
        ]

        for var in expected_vars:
            assert var in result.stdout, f"Variable {var} not in help output"

    def test_logs_rt_command_exists(self, script_path):
        """Test logs rt command is available."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )
        assert "logs rt" in result.stdout or "logs" in result.stdout

    def test_rebuild_command_options(self, script_path):
        """Test rebuild command has --no_cache option."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )
        assert "rebuild" in result.stdout
        assert "--no_cache" in result.stdout or "no-cache" in result.stdout


class TestAppShellExamples:
    """Test app.sh example commands."""

    @pytest.fixture
    def script_path(self):
        """Return path to app.sh script."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.sh")

    def test_example_commands_present(self, script_path):
        """Test example commands are shown in help."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )

        assert "Examples:" in result.stdout
        assert "./app.sh start" in result.stdout or "app.sh start" in result.stdout

    def test_logs_rt_example(self, script_path):
        """Test logs rt example is shown."""
        result = subprocess.run(
            [script_path, "help"],
            capture_output=True,
            text=True,
        )

        assert "logs rt" in result.stdout
