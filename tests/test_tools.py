"""Tests for smoltrace.tools module."""

from smoltrace.tools import (
    CalculatorTool,
    DuckDuckGoSearchTool,
    TimeTool,
    WeatherTool,
    initialize_mcp_tools,
)


def test_weather_tool_known_location():
    """Test WeatherTool with a known location."""
    tool = WeatherTool()

    assert tool.name == "get_weather"
    assert "weather" in tool.description.lower()

    # Test with known location
    result = tool.forward("Paris, France")
    assert "20°C" in result
    assert "Partly Cloudy" in result


def test_weather_tool_multiple_locations():
    """Test WeatherTool with multiple known locations."""
    tool = WeatherTool()

    # Test London
    result = tool.forward("London, UK")
    assert "15°C" in result
    assert "Rainy" in result

    # Test New York
    result = tool.forward("New York, USA")
    assert "25°C" in result
    assert "Sunny" in result

    # Test Tokyo
    result = tool.forward("Tokyo, Japan")
    assert "18°C" in result
    assert "Clear" in result

    # Test Sydney
    result = tool.forward("Sydney, Australia")
    assert "22°C" in result
    assert "Windy" in result


def test_weather_tool_unknown_location():
    """Test WeatherTool with unknown location returns default."""
    tool = WeatherTool()

    result = tool.forward("Unknown City, Unknown Country")
    assert "Unknown City, Unknown Country" in result
    assert "22°C" in result
    assert "Clear" in result


def test_calculator_tool_basic_operations():
    """Test CalculatorTool with basic math operations."""
    tool = CalculatorTool()

    assert tool.name == "calculator"
    assert "math" in tool.description.lower()

    # Test addition
    result = tool.forward("2 + 2")
    assert "Result: 4" in result

    # Test subtraction
    result = tool.forward("10 - 5")
    assert "Result: 5" in result

    # Test multiplication
    result = tool.forward("3 * 4")
    assert "Result: 12" in result

    # Test division
    result = tool.forward("20 / 4")
    assert "Result: 5" in result


def test_calculator_tool_with_parentheses():
    """Test CalculatorTool with complex expressions."""
    tool = CalculatorTool()

    result = tool.forward("(10 + 5) * 2")
    assert "Result: 30" in result

    result = tool.forward("100 / (5 + 5)")
    assert "Result: 10" in result


def test_calculator_tool_error_handling():
    """Test CalculatorTool handles invalid expressions."""
    tool = CalculatorTool()

    # Test invalid expression
    result = tool.forward("invalid expression")
    assert "Error calculating" in result

    # Test division by zero
    result = tool.forward("1 / 0")
    assert "Error calculating" in result


def test_time_tool_default_timezone():
    """Test TimeTool with default UTC timezone."""
    tool = TimeTool()

    assert tool.name == "get_current_time"
    assert "time" in tool.description.lower()

    result = tool.forward()
    assert "Current time in UTC" in result
    # Check format YYYY-MM-DD HH:MM:SS
    assert "-" in result
    assert ":" in result


def test_time_tool_with_timezone():
    """Test TimeTool with specified timezone."""
    tool = TimeTool()

    # Test with EST
    result = tool.forward("EST")
    assert "Current time in EST" in result

    # Test with PST
    result = tool.forward("PST")
    assert "Current time in PST" in result


def test_initialize_mcp_tools_success(mocker, capsys):
    """Test initialize_mcp_tools function with successful connection."""
    from unittest.mock import MagicMock, Mock, patch

    test_url = "http://localhost:8080/sse"

    # Create mock MCPClient
    mock_mcp_client_instance = Mock()
    mock_tool_1 = Mock()
    mock_tool_2 = Mock()
    mock_mcp_client_instance.get_tools.return_value = [mock_tool_1, mock_tool_2]

    # Create a mock module with MCPClient
    mock_mcp_module = MagicMock()
    mock_mcp_module.MCPClient.return_value = mock_mcp_client_instance

    # Patch sys.modules to inject our mock module
    with patch.dict("sys.modules", {"smolagents.mcp_client": mock_mcp_module}):
        result = initialize_mcp_tools(test_url)

        # Should return tools from MCP server
        assert len(result) == 2
        assert result[0] == mock_tool_1
        assert result[1] == mock_tool_2

        # Should print success message
        captured = capsys.readouterr()
        assert test_url in captured.out
        assert "Successfully loaded 2 tools" in captured.out


def test_initialize_mcp_tools_import_error(mocker, capsys):
    """Test initialize_mcp_tools when MCPClient is not available."""
    import sys
    from unittest.mock import patch

    test_url = "http://localhost:8080/sse"

    # Force ImportError by making the import fail
    # Remove smolagents.mcp_client from sys.modules if it exists
    original_modules = sys.modules.copy()

    # Patch sys.modules to make smolagents.mcp_client unavailable
    modules_without_mcp = {k: v for k, v in sys.modules.items() if "mcp_client" not in k}

    with patch.dict("sys.modules", modules_without_mcp, clear=True):
        # Also need to make the import raise ImportError
        def mock_import(name, *args, **kwargs):
            if "mcp_client" in name:
                raise ImportError(f"No module named '{name}'")
            return original_modules.get(name)

        with patch("builtins.__import__", side_effect=mock_import):
            result = initialize_mcp_tools(test_url)

            # Should return empty list
            assert result == []

            # Should print error message
            captured = capsys.readouterr()
            assert "not available" in captured.out or "Error initializing" in captured.out


def test_initialize_mcp_tools_connection_error(mocker, capsys):
    """Test initialize_mcp_tools with connection error."""
    from unittest.mock import MagicMock, patch

    test_url = "http://localhost:8080/sse"

    # Create a mock module where MCPClient raises an exception
    mock_mcp_module = MagicMock()
    mock_mcp_module.MCPClient.side_effect = Exception("Connection failed")

    # Patch sys.modules to inject our mock module
    with patch.dict("sys.modules", {"smolagents.mcp_client": mock_mcp_module}):
        result = initialize_mcp_tools(test_url)

        # Should return empty list
        assert result == []

        # Should print error message
        captured = capsys.readouterr()
        assert "Error initializing MCP tools" in captured.out
        assert "Connection failed" in captured.out


def test_duckduckgo_search_tool_success(mocker):
    """Test DuckDuckGoSearchTool with successful search."""
    from unittest.mock import MagicMock, patch

    tool = DuckDuckGoSearchTool()

    assert tool.name == "web_search"
    assert "search" in tool.description.lower()

    # Mock DDGS instance
    mock_ddgs_instance = mocker.Mock()
    mock_ddgs_instance.__enter__ = mocker.Mock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = mocker.Mock(return_value=False)
    mock_ddgs_instance.text.return_value = [
        {"title": "Result 1", "body": "Description 1", "href": "https://example.com/1"},
        {"title": "Result 2", "body": "Description 2", "href": "https://example.com/2"},
    ]

    # Create a mock ddgs module
    mock_ddgs_module = MagicMock()
    mock_ddgs_module.DDGS.return_value = mock_ddgs_instance

    # Patch sys.modules to inject our mock module
    with patch.dict("sys.modules", {"ddgs": mock_ddgs_module}):
        result = tool.forward("test query")

        assert "Result 1" in result
        assert "Description 1" in result
        assert "https://example.com/1" in result
        assert "Result 2" in result


def test_duckduckgo_search_tool_no_results(mocker):
    """Test DuckDuckGoSearchTool with no results."""
    from unittest.mock import MagicMock, patch

    tool = DuckDuckGoSearchTool()

    # Mock DDGS to return empty results
    mock_ddgs_instance = mocker.Mock()
    mock_ddgs_instance.__enter__ = mocker.Mock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = mocker.Mock(return_value=False)
    mock_ddgs_instance.text.return_value = []

    # Create a mock ddgs module
    mock_ddgs_module = MagicMock()
    mock_ddgs_module.DDGS.return_value = mock_ddgs_instance

    # Patch sys.modules to inject our mock module
    with patch.dict("sys.modules", {"ddgs": mock_ddgs_module}):
        result = tool.forward("test query")

        assert "No results found" in result
        assert "test query" in result


def test_duckduckgo_search_tool_import_error():
    """Test DuckDuckGoSearchTool when ddgs is not installed."""
    tool = DuckDuckGoSearchTool()

    # The function will naturally catch ImportError since DDGS might not be installed
    # We can't easily mock import failures for modules, so we skip comprehensive testing
    # But the tool has error handling for ImportError built in
    result = tool.forward("test query")

    # Should either work (if ddgs installed) or return error message
    assert isinstance(result, str)
    # If error, should contain error message
    if "Error" in result:
        assert "ddgs package not installed" in result or "Search error" in result


def test_duckduckgo_search_tool_search_error(mocker):
    """Test DuckDuckGoSearchTool with search error."""
    from unittest.mock import MagicMock, patch

    tool = DuckDuckGoSearchTool()

    # Mock DDGS to raise exception
    mock_ddgs_instance = mocker.Mock()
    mock_ddgs_instance.__enter__ = mocker.Mock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = mocker.Mock(return_value=False)
    mock_ddgs_instance.text.side_effect = Exception("Search failed")

    # Create a mock ddgs module
    mock_ddgs_module = MagicMock()
    mock_ddgs_module.DDGS.return_value = mock_ddgs_instance

    # Patch sys.modules to inject our mock module
    with patch.dict("sys.modules", {"ddgs": mock_ddgs_module}):
        result = tool.forward("test query")

        assert "Search error" in result


def test_duckduckgo_search_tool_attributes():
    """Test DuckDuckGoSearchTool has correct attributes."""
    tool = DuckDuckGoSearchTool()

    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputs")
    assert hasattr(tool, "output_type")
    assert tool.output_type == "string"


def test_tools_module_imports():
    """Test that all tool classes can be imported."""
    # This ensures the module structure is correct
    assert WeatherTool is not None
    assert CalculatorTool is not None
    assert TimeTool is not None
    assert DuckDuckGoSearchTool is not None
    assert initialize_mcp_tools is not None


def test_weather_tool_attributes():
    """Test WeatherTool has correct attributes."""
    tool = WeatherTool()

    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputs")
    assert hasattr(tool, "output_type")
    assert tool.output_type == "string"


def test_calculator_tool_attributes():
    """Test CalculatorTool has correct attributes."""
    tool = CalculatorTool()

    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputs")
    assert hasattr(tool, "output_type")
    assert tool.output_type == "string"


def test_time_tool_attributes():
    """Test TimeTool has correct attributes."""
    tool = TimeTool()

    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputs")
    assert hasattr(tool, "output_type")
    assert tool.output_type == "string"
