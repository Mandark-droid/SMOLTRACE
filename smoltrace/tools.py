# smoltrace/tools.py
"""Tool definitions for smoltrace agent evaluations."""

from datetime import datetime
from typing import List, Optional

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


def get_smolagents_optional_tools(
    enabled_tools: List[str],
    search_provider: str = "duckduckgo",
    additional_imports: Optional[List[str]] = None,
) -> List[Tool]:
    """Get optional tools from smolagents.default_tools based on enabled_tools list.

    Available optional tools:
    - google_search: GoogleSearchTool (requires SERPER_API_KEY, BRAVE_API_KEY, or provider=duckduckgo)
    - duckduckgo_search: DuckDuckGoSearchTool
    - visit_webpage: VisitWebpageTool
    - python_interpreter: PythonInterpreterTool
    - wikipedia_search: WikipediaSearchTool
    - user_input: UserInputTool

    Args:
        enabled_tools: List of tool names to enable (e.g., ["google_search", "visit_webpage"])
        search_provider: Provider for GoogleSearchTool ("serper", "brave", "duckduckgo")
        additional_imports: Additional Python modules to authorize for PythonInterpreterTool

    Returns:
        List of enabled Tool instances from smolagents.default_tools
    """
    import os

    from smolagents.default_tools import (
        DuckDuckGoSearchTool,
        GoogleSearchTool,
        PythonInterpreterTool,
        UserInputTool,
        VisitWebpageTool,
        WikipediaSearchTool,
    )

    # Base authorized imports for PythonInterpreterTool
    base_imports = ["numpy", "sympy", "math", "statistics", "datetime"]
    if additional_imports:
        base_imports.extend(additional_imports)

    tools = []

    # GoogleSearchTool - requires API key based on provider
    if "google_search" in enabled_tools:
        try:
            api_key_map = {
                "serper": "SERPER_API_KEY",
                "brave": "BRAVE_API_KEY",
                "duckduckgo": None,  # DuckDuckGo provider doesn't need API key
            }
            required_key = api_key_map.get(search_provider)
            if required_key is None or os.getenv(required_key):
                tools.append(GoogleSearchTool(provider=search_provider))
                print(f"[TOOLS] Enabled GoogleSearchTool with provider: {search_provider}")
            else:
                print(
                    f"[WARNING] GoogleSearchTool requires {required_key} environment variable. Skipping."
                )
        except Exception as e:
            print(f"[WARNING] Failed to initialize GoogleSearchTool: {e}")

    # DuckDuckGoSearchTool
    if "duckduckgo_search" in enabled_tools:
        tools.append(DuckDuckGoSearchTool())
        print("[TOOLS] Enabled DuckDuckGoSearchTool")

    # VisitWebpageTool
    if "visit_webpage" in enabled_tools:
        tools.append(VisitWebpageTool())
        print("[TOOLS] Enabled VisitWebpageTool")

    # PythonInterpreterTool
    if "python_interpreter" in enabled_tools:
        tools.append(PythonInterpreterTool(authorized_imports=base_imports))
        print(f"[TOOLS] Enabled PythonInterpreterTool with imports: {base_imports}")

    # WikipediaSearchTool
    if "wikipedia_search" in enabled_tools:
        try:
            tools.append(WikipediaSearchTool())
            print("[TOOLS] Enabled WikipediaSearchTool")
        except ImportError as e:
            print(f"[WARNING] WikipediaSearchTool requires additional dependencies: {e}")

    # UserInputTool
    if "user_input" in enabled_tools:
        try:
            tools.append(UserInputTool())
            print("[TOOLS] Enabled UserInputTool")
        except Exception as e:
            print(f"[WARNING] Failed to initialize UserInputTool: {e}")

    return tools


def get_all_tools(
    search_provider: str = "duckduckgo",
    additional_imports: Optional[List[str]] = None,
    enabled_smolagents_tools: Optional[List[str]] = None,
) -> List[Tool]:
    """Get all available tools: default tools + optional smolagents tools.

    By default, returns 5 default tools required for kshitijthakkar/smoltrace-tasks:
    - WeatherTool (custom)
    - CalculatorTool (custom)
    - TimeTool (custom)
    - DuckDuckGoSearchTool (from smolagents) - Required for web search tasks
    - PythonInterpreterTool (from smolagents) - Required for code execution tasks

    Optionally enable additional smolagents.default_tools via enabled_smolagents_tools parameter.

    Args:
        search_provider: Provider for GoogleSearchTool ("serper", "brave", "duckduckgo")
        additional_imports: Additional Python modules for PythonInterpreterTool
        enabled_smolagents_tools: List of additional smolagents tool names to enable
            Options: ["google_search", "visit_webpage", "wikipedia_search", "user_input"]
            Note: "duckduckgo_search" and "python_interpreter" are already enabled by default

    Returns:
        List of all available Tool instances
    """
    # Start with our 3 custom tools
    tools = [
        WeatherTool(),
        CalculatorTool(),
        TimeTool(),
    ]

    # Add default smolagents tools required for smoltrace-tasks dataset
    # These are always enabled to ensure tasks can run
    from smolagents.default_tools import DuckDuckGoSearchTool, PythonInterpreterTool

    # Base imports for PythonInterpreterTool
    base_imports = ["numpy", "sympy", "math", "statistics", "datetime"]
    if additional_imports:
        base_imports.extend(additional_imports)

    try:
        tools.append(DuckDuckGoSearchTool())
        print("[TOOLS] Enabled DuckDuckGoSearchTool (default for web search tasks)")
    except Exception as e:
        print(f"[WARNING] Failed to initialize DuckDuckGoSearchTool: {e}")

    try:
        tools.append(PythonInterpreterTool(authorized_imports=base_imports))
        print(
            f"[TOOLS] Enabled PythonInterpreterTool (default for code tasks) with imports: {base_imports}"
        )
    except Exception as e:
        print(f"[WARNING] Failed to initialize PythonInterpreterTool: {e}")

    # Add optional smolagents tools if requested
    if enabled_smolagents_tools:
        smolagents_tools = get_smolagents_optional_tools(
            enabled_smolagents_tools, search_provider, additional_imports
        )
        tools.extend(smolagents_tools)

    return tools


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
