# smoltrace/tools.py
"""Tool definitions for smoltrace agent evaluations."""

import os
from datetime import datetime
from pathlib import Path
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


# ============================================================================
# File System Tools (Phase 1) - For GAIA and SWE/DevOps/SRE Benchmarks
# ============================================================================


class ReadFileTool(Tool):
    """Read file contents with safety checks.

    Essential for GAIA benchmarks and SWE tasks that require reading source code,
    configuration files, data files, logs, etc.
    """

    name = "read_file"
    description = (
        "Read the contents of a file from the filesystem. "
        "Supports text files with various encodings. "
        "Returns the file contents as a string."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to read (relative to working directory or absolute)",
        },
        "encoding": {
            "type": "string",
            "description": "File encoding (default: utf-8). Common: utf-8, latin-1, ascii",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        """Initialize ReadFileTool with optional working directory."""
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, file_path: str) -> Path:
        """Validate and resolve file path with security checks."""
        # Convert to Path object
        path = Path(file_path)

        # If relative, make it relative to working_dir
        if not path.is_absolute():
            path = self.working_dir / path

        # Resolve to absolute path (handles symlinks and ..)
        try:
            path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {e}")

        # Security check: Ensure path is within working_dir (prevent path traversal)
        if self.working_dir:
            try:
                path.relative_to(self.working_dir.resolve())
            except ValueError:
                raise ValueError(
                    f"Access denied: Path {path} is outside working directory {self.working_dir}"
                )

        return path

    def forward(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read file with safety checks."""
        try:
            # Validate path
            path = self._validate_path(file_path)

            # Check if file exists
            if not path.exists():
                return f"Error: File not found: {file_path}"

            # Check if it's a file (not a directory)
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            # Check file size (limit to 10MB for safety)
            file_size = path.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                return f"Error: File too large ({file_size} bytes). Maximum size: {max_size} bytes"

            # Read file
            with open(path, "r", encoding=encoding) as f:
                content = f.read()

            return f"File: {file_path}\nSize: {file_size} bytes\n\n{content}"

        except UnicodeDecodeError as e:
            return f"Error: Failed to decode file with encoding '{encoding}': {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file: {e}"


class WriteFileTool(Tool):
    """Write file contents with safety checks.

    Essential for SWE tasks that require creating configuration files,
    writing code patches, saving results, etc.
    """

    name = "write_file"
    description = (
        "Write content to a file in the filesystem. "
        "Can create new files or overwrite existing files. "
        "Use with caution as it modifies the filesystem."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to write (relative to working directory or absolute)",
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file",
        },
        "mode": {
            "type": "string",
            "description": "Write mode: 'write' (overwrite) or 'append' (default: write)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None, allow_dangerous: bool = False):
        """Initialize WriteFileTool with optional working directory."""
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.allow_dangerous = allow_dangerous

    def _validate_path(self, file_path: str) -> Path:
        """Validate and resolve file path with security checks."""
        # Convert to Path object
        path = Path(file_path)

        # If relative, make it relative to working_dir
        if not path.is_absolute():
            path = self.working_dir / path

        # Resolve to absolute path
        try:
            # For new files, resolve parent directory
            if not path.exists():
                parent = path.parent.resolve()
                path = parent / path.name
            else:
                path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {e}")

        # Security check: Ensure path is within working_dir
        if self.working_dir:
            try:
                path.relative_to(self.working_dir.resolve())
            except ValueError:
                raise ValueError(
                    f"Access denied: Path {path} is outside working directory {self.working_dir}"
                )

        # Security check: Prevent overwriting system files
        dangerous_patterns = [
            "/etc/",
            "/sys/",
            "/proc/",
            "/dev/",
            "C:\\Windows\\",
            "C:\\Program Files\\",
        ]
        path_str = str(path)
        if not self.allow_dangerous:
            for pattern in dangerous_patterns:
                if pattern in path_str:
                    raise ValueError(f"Access denied: Cannot write to system directory: {path}")

        return path

    def forward(self, file_path: str, content: str, mode: str = "write") -> str:
        """Write file with safety checks."""
        try:
            # Validate mode
            if mode not in ["write", "append"]:
                return f"Error: Invalid mode '{mode}'. Must be 'write' or 'append'"

            # Validate path
            path = self._validate_path(file_path)

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Determine file mode
            file_mode = "a" if mode == "append" else "w"

            # Write file
            with open(path, file_mode, encoding="utf-8") as f:
                f.write(content)

            # Get file info
            file_size = path.stat().st_size

            action = "Appended to" if mode == "append" else "Wrote"
            return f"{action} file: {file_path}\nSize: {file_size} bytes\nContent length: {len(content)} characters"

        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"


class ListDirectoryTool(Tool):
    """List files and directories with safety checks.

    Essential for exploring project structure, finding files in SWE/DevOps tasks.
    """

    name = "list_directory"
    description = (
        "List files and directories in a given path. "
        "Returns file names, sizes, and types. "
        "Useful for exploring project structure and finding files."
    )
    inputs = {
        "directory_path": {
            "type": "string",
            "description": "Path to directory to list (relative to working directory or absolute)",
        },
        "pattern": {
            "type": "string",
            "description": "Optional glob pattern to filter results (e.g., '*.py', '*.json')",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        """Initialize ListDirectoryTool with optional working directory."""
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, dir_path: str) -> Path:
        """Validate and resolve directory path."""
        path = Path(dir_path)

        # If relative, make it relative to working_dir
        if not path.is_absolute():
            path = self.working_dir / path

        # Resolve to absolute path
        try:
            path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {e}")

        # Security check: Ensure path is within working_dir
        if self.working_dir:
            try:
                path.relative_to(self.working_dir.resolve())
            except ValueError:
                raise ValueError(
                    f"Access denied: Path {path} is outside working directory {self.working_dir}"
                )

        return path

    def forward(self, directory_path: str, pattern: Optional[str] = None) -> str:
        """List directory contents with safety checks."""
        try:
            # Validate path
            path = self._validate_path(directory_path)

            # Check if directory exists
            if not path.exists():
                return f"Error: Directory not found: {directory_path}"

            # Check if it's a directory
            if not path.is_dir():
                return f"Error: Path is not a directory: {directory_path}"

            # List files
            if pattern:
                # Use glob pattern
                files = list(path.glob(pattern))
            else:
                # List all files
                files = list(path.iterdir())

            # Sort files (directories first, then files alphabetically)
            files.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

            # Format output
            output_lines = [f"Directory: {directory_path}"]
            output_lines.append(f"Total items: {len(files)}\n")

            for file in files:
                try:
                    if file.is_dir():
                        output_lines.append(f"[DIR]  {file.name}/")
                    else:
                        size = file.stat().st_size
                        output_lines.append(f"[FILE] {file.name} ({size} bytes)")
                except OSError:
                    output_lines.append(f"[?]    {file.name} (access error)")

            return "\n".join(output_lines)

        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {directory_path}"
        except Exception as e:
            return f"Error listing directory: {e}"


class FileSearchTool(Tool):
    """Search for files by name pattern or content.

    Essential for finding specific files, grep-like functionality in SRE/DevOps tasks.
    """

    name = "search_files"
    description = (
        "Search for files by name pattern or content within a directory. "
        "Supports glob patterns for filename search and text search for content. "
        "Returns list of matching file paths."
    )
    inputs = {
        "directory": {
            "type": "string",
            "description": "Directory to search in (relative to working directory or absolute)",
        },
        "pattern": {
            "type": "string",
            "description": "Search pattern (filename glob like '*.py' or text to search in files)",
        },
        "search_type": {
            "type": "string",
            "description": "Type of search: 'name' (filename) or 'content' (file contents). Default: name",
            "nullable": True,
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 100)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        """Initialize FileSearchTool with optional working directory."""
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, dir_path: str) -> Path:
        """Validate and resolve directory path."""
        path = Path(dir_path)

        if not path.is_absolute():
            path = self.working_dir / path

        try:
            path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {e}")

        if self.working_dir:
            try:
                path.relative_to(self.working_dir.resolve())
            except ValueError:
                raise ValueError(
                    f"Access denied: Path {path} is outside working directory {self.working_dir}"
                )

        return path

    def forward(
        self,
        directory: str,
        pattern: str,
        search_type: str = "name",
        max_results: int = 100,
    ) -> str:
        """Search files with safety checks."""
        try:
            # Validate inputs
            if search_type not in ["name", "content"]:
                return f"Error: Invalid search_type '{search_type}'. Must be 'name' or 'content'"

            # Validate path
            path = self._validate_path(directory)

            if not path.exists():
                return f"Error: Directory not found: {directory}"

            if not path.is_dir():
                return f"Error: Path is not a directory: {directory}"

            results = []

            if search_type == "name":
                # Search by filename using glob
                matches = path.rglob(pattern)
                for match in matches:
                    if len(results) >= max_results:
                        break
                    try:
                        rel_path = match.relative_to(path)
                        if match.is_file():
                            size = match.stat().st_size
                            results.append(f"{rel_path} ({size} bytes)")
                        else:
                            results.append(f"{rel_path}/ [directory]")
                    except (OSError, ValueError):
                        continue

            else:  # search_type == "content"
                # Search by content (grep-like)
                # Only search text files (limit by extension for safety)
                text_extensions = {
                    ".txt",
                    ".py",
                    ".js",
                    ".java",
                    ".c",
                    ".cpp",
                    ".h",
                    ".md",
                    ".json",
                    ".yaml",
                    ".yml",
                    ".xml",
                    ".html",
                    ".css",
                    ".sh",
                    ".bash",
                    ".sql",
                    ".log",
                }

                for file_path in path.rglob("*"):
                    if len(results) >= max_results:
                        break

                    if not file_path.is_file():
                        continue

                    if file_path.suffix.lower() not in text_extensions:
                        continue

                    # Check file size (don't search large files)
                    try:
                        if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                            continue
                    except OSError:
                        continue

                    # Search file content
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if pattern.lower() in content.lower():
                                rel_path = file_path.relative_to(path)
                                # Count occurrences
                                count = content.lower().count(pattern.lower())
                                results.append(f"{rel_path} ({count} matches)")
                    except (OSError, UnicodeDecodeError):
                        continue

            # Format output
            if not results:
                return f"No files found matching '{pattern}' in {directory}"

            output_lines = [f"Search: '{pattern}' in {directory} (type: {search_type})"]
            output_lines.append(f"Found {len(results)} results:\n")
            output_lines.extend(results)

            if len(results) >= max_results:
                output_lines.append(f"\n(Showing first {max_results} results)")

            return "\n".join(output_lines)

        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {directory}"
        except Exception as e:
            return f"Error searching files: {e}"


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
