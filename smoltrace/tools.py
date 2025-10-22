# smoltrace/tools.py
"""Tool definitions for smoltrace agent evaluations."""

from smolagents import Tool, DuckDuckGoSearchTool
from datetime import datetime


class WeatherTool(Tool):
    """Simple weather tool for testing"""
    name = "get_weather"
    description = "Gets the current weather for a given location. Returns temperature and conditions."
    inputs = {
        "location": {
            "type": "string",
            "description": "The city and country, e.g. 'Paris, France'"
        }
    }
    output_type = "string"

    def forward(self, location: str) -> str:
        weather_data = {
            "Paris, France": "20°C, Partly Cloudy",
            "London, UK": "15°C, Rainy",
            "New York, USA": "25°C, Sunny",
            "Tokyo, Japan": "18°C, Clear",
            "Sydney, Australia": "22°C, Windy",
        }
        return weather_data.get(location, f"Weather data for {location}: 22°C, Clear")


class CalculatorTool(Tool):
    """Simple calculator tool for testing"""
    name = "calculator"
    description = "Performs basic math calculations. Supports +, -, *, /, and parentheses."
    inputs = {
        "expression": {
            "type": "string",
            "description": "The mathematical expression to evaluate"
        }
    }
    output_type = "string"

    def forward(self, expression: str) -> str:
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            return f"Error calculating: {str(e)}"


class TimeTool(Tool):
    """Simple time tool for testing"""
    name = "get_current_time"
    description = "Gets the current time in a specific timezone or UTC."
    inputs = {
        "timezone": {
            "type": "string",
            "description": "The timezone, e.g. 'UTC', 'EST', 'PST'. Defaults to UTC.",
            "nullable": True
        }
    }
    output_type = "string"

    def forward(self, timezone: str = "UTC") -> str:
        return f"Current time in {timezone}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# class DuckDuckGoSearchTool(Tool):
#     """Tool for web search using DuckDuckGo."""
#
#     name = "web_search"
#     description = "Search the web for information. Args: query (str)"
#     inputs = {"query": {"type": "string", "description": "Search query"}}
#     output_type = "string"
#
#     def forward(self, query: str) -> str:
#         """Mock search results."""
#         return f"Search results for '{query}': Mock result 1, Mock result 2"


def initialize_mcp_tools(mcp_server_url: str):
    """Initialize MCP tools from a server URL (placeholder for future implementation)."""
    print(f"MCP server URL provided: {mcp_server_url} (not yet implemented)")
    return []
