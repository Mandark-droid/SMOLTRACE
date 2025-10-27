"""Tests for smoltrace.tools module."""

import pytest

from smoltrace.tools import CalculatorTool, TimeTool, WeatherTool, initialize_mcp_tools


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


def test_initialize_mcp_tools(capsys):
    """Test initialize_mcp_tools function."""
    test_url = "http://localhost:8080"

    result = initialize_mcp_tools(test_url)

    # Should return empty list (not yet implemented)
    assert result == []

    # Should print message
    captured = capsys.readouterr()
    assert test_url in captured.out
    assert "not yet implemented" in captured.out


def test_tools_module_imports():
    """Test that all tool classes can be imported."""
    # This ensures the module structure is correct
    assert WeatherTool is not None
    assert CalculatorTool is not None
    assert TimeTool is not None
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
