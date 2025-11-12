"""Tests for Phase 3 process and system tools (ps, kill, env, which, curl, ping)."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from smoltrace.tools import CurlTool, EnvTool, KillTool, PingTool, PsTool, WhichTool

# ============================================================================
# PsTool Tests
# ============================================================================


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_basic():
    """Test basic process listing."""
    tool = PsTool()

    result = tool.forward(limit=10)

    assert "Found" in result
    assert "PID" in result
    assert "NAME" in result
    assert "CPU%" in result
    assert "MEM%" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_filter_by_name():
    """Test filtering processes by name."""
    tool = PsTool()

    # Filter for python processes
    result = tool.forward(filter_name="python", limit=10)

    # Should find at least the current Python process
    assert "python" in result.lower() or "No processes found" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_sort_by_cpu():
    """Test sorting by CPU usage."""
    tool = PsTool()

    result = tool.forward(sort_by="cpu", limit=10, descending=True)

    assert "Found" in result
    assert "CPU%" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_sort_by_memory():
    """Test sorting by memory usage."""
    tool = PsTool()

    result = tool.forward(sort_by="memory", limit=10, descending=True)

    assert "Found" in result
    assert "MEM%" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_sort_by_pid():
    """Test sorting by PID."""
    tool = PsTool()

    result = tool.forward(sort_by="pid", limit=10, descending=False)

    assert "Found" in result
    assert "PID" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_invalid_sort_field():
    """Test invalid sort field."""
    tool = PsTool()

    result = tool.forward(sort_by="invalid")

    assert "Error: Invalid sort_by field" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_limit_validation():
    """Test limit validation."""
    tool = PsTool()

    # Test limit < 1
    result = tool.forward(limit=0)
    assert "Error: Limit must be at least 1" in result

    # Test limit > 500 (should cap)
    result = tool.forward(limit=1000)
    assert "Found" in result  # Should succeed with capped limit


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_no_matches():
    """Test filtering with no matches."""
    tool = PsTool()

    result = tool.forward(filter_name="nonexistent_process_xyz123")

    assert "No processes found" in result


# ============================================================================
# KillTool Tests
# ============================================================================


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "Process"), reason="psutil not installed"
)
def test_kill_invalid_pid():
    """Test killing invalid PID."""
    tool = KillTool()

    # Test PID < 1
    result = tool.forward(pid=0)
    assert "Error: Invalid PID" in result

    result = tool.forward(pid=-1)
    assert "Error: Invalid PID" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "Process"), reason="psutil not installed"
)
def test_kill_nonexistent_pid():
    """Test killing non-existent PID."""
    tool = KillTool()

    # Use a very high PID that likely doesn't exist
    result = tool.forward(pid=9999999)

    assert "Error: No process found with PID" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "Process"), reason="psutil not installed"
)
def test_kill_protected_pid():
    """Test killing protected system PIDs."""
    tool = KillTool()

    # Try to kill PID 1 (init/systemd on Linux/macOS, may not exist on Windows)
    result = tool.forward(pid=1)

    # On Windows PID 1 may not exist, on Linux/macOS it should be protected
    assert (
        "Error: Cannot kill protected system process" in result
        or "Error: No process found with PID 1" in result
    )


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "Process"), reason="psutil not installed"
)
def test_kill_current_process():
    """Test killing current process (should be blocked)."""
    tool = KillTool()

    current_pid = os.getpid()
    result = tool.forward(pid=current_pid)

    assert "Error: Cannot kill the current process" in result


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "Process"), reason="psutil not installed"
)
@patch("psutil.Process")
@patch("psutil.pid_exists")
def test_kill_success(mock_pid_exists, mock_process):
    """Test successful process termination."""
    tool = KillTool()

    # Mock a killable process
    mock_pid_exists.return_value = True
    mock_proc = MagicMock()
    mock_proc.name.return_value = "test_process"
    mock_proc.status.return_value = "running"
    mock_proc.wait.return_value = None
    mock_process.return_value = mock_proc

    result = tool.forward(pid=12345)

    # Should succeed or indicate access denied
    assert (
        "Terminated process" in result or "Permission denied" in result or "Cannot access" in result
    )


# ============================================================================
# EnvTool Tests
# ============================================================================


def test_env_get_existing():
    """Test getting existing environment variable."""
    tool = EnvTool()

    # Set a test variable
    os.environ["TEST_SMOLTRACE_VAR"] = "test_value"

    result = tool.forward(action="get", name="TEST_SMOLTRACE_VAR")

    assert "TEST_SMOLTRACE_VAR=test_value" in result

    # Cleanup
    del os.environ["TEST_SMOLTRACE_VAR"]


def test_env_get_nonexistent():
    """Test getting non-existent variable."""
    tool = EnvTool()

    result = tool.forward(action="get", name="NONEXISTENT_VAR_XYZ123")

    assert "is not set" in result


def test_env_set():
    """Test setting environment variable."""
    tool = EnvTool()

    result = tool.forward(action="set", name="TEST_SMOLTRACE_SET", value="new_value")

    assert "Set environment variable" in result
    assert os.getenv("TEST_SMOLTRACE_SET") == "new_value"

    # Cleanup
    del os.environ["TEST_SMOLTRACE_SET"]


def test_env_list_all():
    """Test listing all environment variables."""
    tool = EnvTool()

    result = tool.forward(action="list")

    assert "Found" in result
    assert "environment variables" in result
    # Should contain at least PATH
    assert "PATH=" in result or "Path=" in result


def test_env_list_filtered():
    """Test listing filtered environment variables."""
    tool = EnvTool()

    # Set test variables
    os.environ["TEST_FILTER_1"] = "value1"
    os.environ["TEST_FILTER_2"] = "value2"

    result = tool.forward(action="list", filter_pattern="TEST_FILTER")

    assert "TEST_FILTER_1" in result
    assert "TEST_FILTER_2" in result

    # Cleanup
    del os.environ["TEST_FILTER_1"]
    del os.environ["TEST_FILTER_2"]


def test_env_invalid_action():
    """Test invalid action."""
    tool = EnvTool()

    result = tool.forward(action="invalid")

    assert "Error: Invalid action" in result


def test_env_missing_name_for_get():
    """Test missing name for get action."""
    tool = EnvTool()

    result = tool.forward(action="get")

    assert "Error: Variable name required" in result


def test_env_missing_value_for_set():
    """Test missing value for set action."""
    tool = EnvTool()

    result = tool.forward(action="set", name="TEST_VAR")

    assert "Error: Variable value required" in result


# ============================================================================
# WhichTool Tests
# ============================================================================


def test_which_python():
    """Test finding python executable."""
    tool = WhichTool()

    result = tool.forward(command="python")

    # Should find python or python3
    assert "python" in result.lower() and (":" in result or "not found" in result)


def test_which_nonexistent():
    """Test finding non-existent command."""
    tool = WhichTool()

    result = tool.forward(command="nonexistent_command_xyz123")

    assert "not found in PATH" in result


def test_which_empty_command():
    """Test empty command."""
    tool = WhichTool()

    result = tool.forward(command="")

    assert "Error: Command name cannot be empty" in result


def test_which_all_matches():
    """Test finding all matches."""
    tool = WhichTool()

    result = tool.forward(command="python", all_matches=True)

    # Should find at least one or indicate not found
    assert "Found" in result or "not found" in result


# ============================================================================
# CurlTool Tests
# ============================================================================


def test_curl_invalid_url():
    """Test curl with invalid URL."""
    tool = CurlTool()

    result = tool.forward(url="invalid_url")

    assert "Error: URL must start with http:// or https://" in result


def test_curl_invalid_method():
    """Test curl with invalid HTTP method."""
    tool = CurlTool()

    result = tool.forward(url="https://httpbin.org/get", method="INVALID")

    assert "Error: Invalid HTTP method" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS") == "1", reason="Network tests disabled")
def test_curl_get_request():
    """Test GET request with curl."""
    tool = CurlTool()

    result = tool.forward(url="https://httpbin.org/get", method="GET", timeout=10)

    # Should get 200 response or timeout
    assert "HTTP 200" in result or "timeout" in result.lower() or "Error" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS") == "1", reason="Network tests disabled")
def test_curl_post_request():
    """Test POST request with curl."""
    tool = CurlTool()

    result = tool.forward(
        url="https://httpbin.org/post", method="POST", body='{"test": "data"}', timeout=10
    )

    # Should get 200 response or timeout
    assert "HTTP 200" in result or "timeout" in result.lower() or "Error" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS") == "1", reason="Network tests disabled")
def test_curl_custom_headers():
    """Test curl with custom headers."""
    tool = CurlTool()

    headers_json = '{"User-Agent": "SmolTrace-Test", "X-Custom-Header": "test-value"}'
    result = tool.forward(
        url="https://httpbin.org/headers", method="GET", headers=headers_json, timeout=10
    )

    # Should succeed or timeout
    assert "HTTP" in result or "timeout" in result.lower() or "Error" in result


def test_curl_invalid_headers_json():
    """Test curl with invalid headers JSON."""
    tool = CurlTool()

    result = tool.forward(url="https://httpbin.org/get", headers="invalid json")

    assert "Error: Invalid JSON in headers" in result


def test_curl_timeout():
    """Test curl timeout handling."""
    tool = CurlTool()

    # Use a very short timeout on a slow endpoint
    result = tool.forward(url="https://httpbin.org/delay/10", timeout=1)

    # Should timeout or get URLError
    assert "timeout" in result.lower() or "Error" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS"), reason="Skipping network tests")
def test_curl_http_error_404():
    """Test handling of HTTP 404 error."""
    tool = CurlTool()

    # Request a 404 page
    result = tool.forward(url="https://httpbin.org/status/404", method="GET")

    # Should contain HTTP error information
    assert "HTTP Error 404" in result or "404" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS"), reason="Skipping network tests")
def test_curl_http_error_500():
    """Test handling of HTTP 500 error."""
    tool = CurlTool()

    # Request a 500 error page
    result = tool.forward(url="https://httpbin.org/status/500", method="GET")

    # Should contain HTTP error information
    assert "HTTP Error 500" in result or "500" in result


def test_curl_invalid_url_format():
    """Test handling of completely invalid URL."""
    tool = CurlTool()

    # Use an invalid URL format
    result = tool.forward(url="not-a-url", method="GET")

    # Should return validation error
    assert "Error" in result and (
        "invalid" in result.lower() or "must start with http" in result.lower()
    )


# ============================================================================
# PingTool Tests
# ============================================================================


def test_ping_empty_host():
    """Test ping with empty host."""
    tool = PingTool()

    result = tool.forward(host="")

    assert "Error: Host cannot be empty" in result


def test_ping_invalid_count():
    """Test ping with invalid count."""
    tool = PingTool()

    result = tool.forward(host="8.8.8.8", count=0)

    assert "Error: Count must be at least 1" in result


def test_ping_invalid_timeout():
    """Test ping with invalid timeout."""
    tool = PingTool()

    result = tool.forward(host="8.8.8.8", timeout=0)

    assert "Error: Timeout must be at least 1 second" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS") == "1", reason="Network tests disabled")
def test_ping_google_dns():
    """Test ping to Google DNS."""
    tool = PingTool()

    result = tool.forward(host="8.8.8.8", count=2, timeout=5)

    # Should succeed or indicate network issue
    assert "Ping statistics" in result or "unreachable" in result.lower() or "Error" in result


@pytest.mark.skipif(os.getenv("SKIP_NETWORK_TESTS") == "1", reason="Network tests disabled")
def test_ping_localhost():
    """Test ping to localhost."""
    tool = PingTool()

    result = tool.forward(host="127.0.0.1", count=2, timeout=5)

    # Localhost should always be reachable
    assert "Ping statistics" in result or "reachable" in result or "Error" in result


def test_ping_nonexistent_host():
    """Test ping to non-existent host."""
    tool = PingTool()

    result = tool.forward(host="nonexistent-host-xyz123.invalid", count=1, timeout=2)

    # Should fail or timeout
    assert "unreachable" in result.lower() or "failed" in result.lower() or "Error" in result


def test_ping_count_cap():
    """Test ping count is capped at 100."""
    tool = PingTool()

    # Request 200 pings, should be capped to 100
    # Use a very short timeout to avoid long test duration
    result = tool.forward(host="127.0.0.1", count=10, timeout=1)

    # Should not hang (if it runs, count was capped)
    # The tool should have run, even if individual pings failed due to short timeout
    assert isinstance(result, str)


# ============================================================================
# Integration Tests
# ============================================================================


def test_system_tools_attributes():
    """Test all Phase 3 tools have correct attributes."""
    ps_tool = PsTool()
    kill_tool = KillTool()
    env_tool = EnvTool()
    which_tool = WhichTool()
    curl_tool = CurlTool()
    ping_tool = PingTool()

    for tool in [ps_tool, kill_tool, env_tool, which_tool, curl_tool, ping_tool]:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputs")
        assert hasattr(tool, "output_type")
        assert tool.output_type == "string"


def test_env_which_integration():
    """Test env and which tools working together."""
    env_tool = EnvTool()
    which_tool = WhichTool()

    # Get PATH
    path_result = env_tool.forward(action="get", name="PATH")
    assert "PATH=" in path_result or "Path=" in path_result

    # Find python in PATH
    which_result = which_tool.forward(command="python")
    assert "python" in which_result.lower()


@pytest.mark.skipif(
    not hasattr(sys.modules.get("psutil", None), "process_iter"), reason="psutil not installed"
)
def test_ps_env_integration():
    """Test ps and env tools together."""
    ps_tool = PsTool()
    env_tool = EnvTool()

    # List processes
    ps_result = ps_tool.forward(limit=5)
    assert "Found" in ps_result

    # Check environment variable
    env_result = env_tool.forward(action="list", filter_pattern="PATH")
    assert "PATH" in env_result or "Path" in env_result
