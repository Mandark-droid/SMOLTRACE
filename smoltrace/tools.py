# smoltrace/tools.py
"""Tool definitions for smoltrace agent evaluations."""

from datetime import datetime

from smolagents import Tool


class WeatherTool(Tool):
    """Simple weather tool for testing"""

    name = "get_weather"
    description = (
        "Gets the current weather for a given location. Returns temperature and conditions."
    )
    inputs = {
        "location": {"type": "string", "description": "The city and country, e.g. 'Paris, France'"}
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
        "expression": {"type": "string", "description": "The mathematical expression to evaluate"}
    }
    output_type = "string"

    def forward(self, expression: str) -> str:
        try:
            # Using eval with restricted builtins for safe math evaluation
            result = eval(expression, {"__builtins__": {}}, {})  # nosec B307
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
            "nullable": True,
        }
    }
    output_type = "string"

    def forward(self, timezone: str = "UTC") -> str:
        return f"Current time in {timezone}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


class DuckDuckGoSearchTool(Tool):
    """Tool for web search using DuckDuckGo."""

    name = "web_search"
    description = "Search the web for information using DuckDuckGo. Returns search results."
    inputs = {"query": {"type": "string", "description": "Search query"}}
    output_type = "string"

    def forward(self, query: str) -> str:
        """Perform web search using DuckDuckGo."""
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    return f"No results found for '{query}'"

                formatted_results = []
                for i, result in enumerate(results, 1):
                    title = result.get("title", "No title")
                    snippet = result.get("body", "No description")
                    url = result.get("href", "")
                    formatted_results.append(f"{i}. {title}\n   {snippet}\n   URL: {url}")

                return "\n\n".join(formatted_results)
        except ImportError:
            return "Error: ddgs package not installed. Install with: pip install ddgs"
        except Exception as e:
            return f"Search error: {str(e)}"


def initialize_mcp_tools(mcp_server_url: str):
    """Initialize MCP tools from a server URL.

    Args:
        mcp_server_url: URL of the MCP server (e.g., "http://localhost:8000/sse")

    Returns:
        List of tools retrieved from the MCP server
    """
    try:
        from smolagents.mcp_client import MCPClient

        print(f"[MCP] Connecting to MCP server: {mcp_server_url}")
        mcp_client = MCPClient({"url": mcp_server_url})
        tools = mcp_client.get_tools()
        print(f"[MCP] Successfully loaded {len(tools)} tools from MCP server")
        return tools
    except ImportError:
        print("[MCP] Error: smolagents.mcp_client not available. MCP tools not loaded.")
        return []
    except Exception as e:
        print(f"[MCP] Error initializing MCP tools: {str(e)}")
        return []
