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


# ============================================================================
# Phase 2: Text Processing Tools
# ============================================================================


class GrepTool(Tool):
    """Search for patterns in files with regex support (grep-like)."""

    name = "grep"
    description = (
        "Search for regex patterns in file contents. "
        "Supports line numbers, context lines, case-insensitive search, "
        "and invert matching. Returns matching lines with optional context."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to search (relative to working directory or absolute)",
        },
        "pattern": {
            "type": "string",
            "description": "Regex pattern to search for",
        },
        "case_insensitive": {
            "type": "boolean",
            "description": "Case-insensitive search (default: False)",
            "nullable": True,
        },
        "line_numbers": {
            "type": "boolean",
            "description": "Show line numbers (default: True)",
            "nullable": True,
        },
        "context_before": {
            "type": "integer",
            "description": "Number of lines of context before match (default: 0)",
            "nullable": True,
        },
        "context_after": {
            "type": "integer",
            "description": "Number of lines of context after match (default: 0)",
            "nullable": True,
        },
        "invert_match": {
            "type": "boolean",
            "description": "Invert match - show non-matching lines (default: False)",
            "nullable": True,
        },
        "count_only": {
            "type": "boolean",
            "description": "Only count matching lines (default: False)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, file_path: str) -> Path:
        path = Path(file_path)
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
        file_path: str,
        pattern: str,
        case_insensitive: bool = False,
        line_numbers: bool = True,
        context_before: int = 0,
        context_after: int = 0,
        invert_match: bool = False,
        count_only: bool = False,
    ) -> str:
        import re

        try:
            path = self._validate_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"Error: Invalid regex pattern '{pattern}': {e}"

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            matches = []
            for i, line in enumerate(lines):
                is_match = bool(regex.search(line))
                if invert_match:
                    is_match = not is_match
                if is_match:
                    matches.append(i)

            if count_only:
                return f"{len(matches)} matches in {file_path}"
            if not matches:
                return f"No matches found for pattern '{pattern}' in {file_path}"

            output_lines = []
            shown_lines = set()
            for match_idx in matches:
                start = max(0, match_idx - context_before)
                end = min(len(lines), match_idx + context_after + 1)
                if output_lines and start > 0 and start - 1 not in shown_lines:
                    output_lines.append("--")
                for i in range(start, end):
                    if i not in shown_lines:
                        line = lines[i].rstrip("\n")
                        if line_numbers:
                            prefix = f"{i + 1}:" if i == match_idx else f"{i + 1}-"
                            output_lines.append(f"{prefix}{line}")
                        else:
                            output_lines.append(line)
                        shown_lines.add(i)

            result = f"Matches in {file_path} (pattern: '{pattern}'):\n"
            result += "\n".join(output_lines)
            return result

        except UnicodeDecodeError:
            return f"Error: Cannot read {file_path} - not a text file"
        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error: {e}"


class SedTool(Tool):
    """Stream editor for text transformations (sed-like)."""

    name = "sed"
    description = (
        "Perform text transformations on files using sed-like commands. "
        "Supports substitution (s/pattern/replacement/), deletion (d), and line selection. "
        "Can optionally write results to a new file."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to process (relative to working directory or absolute)",
        },
        "command": {
            "type": "string",
            "description": "Sed command: 's/pattern/replacement/' for substitution, '/pattern/d' for deletion, or 'Np' for printing line N",
        },
        "global_replace": {
            "type": "boolean",
            "description": "Replace all occurrences in each line (default: False)",
            "nullable": True,
        },
        "case_insensitive": {
            "type": "boolean",
            "description": "Case-insensitive pattern matching (default: False)",
            "nullable": True,
        },
        "output_file": {
            "type": "string",
            "description": "Optional output file path",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, file_path: str) -> Path:
        path = Path(file_path)
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
        file_path: str,
        command: str,
        global_replace: bool = False,
        case_insensitive: bool = False,
        output_file: Optional[str] = None,
    ) -> str:
        import re

        try:
            path = self._validate_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            transformed_lines = []

            if command.startswith("s/") and command.count("/") >= 2:
                parts = command[2:].split("/", 2)
                if len(parts) < 2:
                    return f"Error: Invalid substitution command '{command}'"
                pattern, replacement = parts[0], parts[1]
                flags = re.IGNORECASE if case_insensitive else 0
                try:
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    return f"Error: Invalid regex pattern '{pattern}': {e}"
                count = 0 if global_replace else 1
                for line in lines:
                    transformed_lines.append(regex.sub(replacement, line, count=count))

            elif command.endswith("/d") and command.startswith("/"):
                pattern = command[1:-2]
                flags = re.IGNORECASE if case_insensitive else 0
                try:
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    return f"Error: Invalid regex pattern '{pattern}': {e}"
                for line in lines:
                    if not regex.search(line):
                        transformed_lines.append(line)

            elif command.endswith("p") and command[:-1].isdigit():
                line_num = int(command[:-1])
                if 1 <= line_num <= len(lines):
                    return lines[line_num - 1].rstrip("\n")
                else:
                    return f"Error: Line {line_num} out of range (file has {len(lines)} lines)"
            else:
                return f"Error: Unsupported command '{command}'. Use 's/pattern/replacement/', '/pattern/d', or 'Np'"

            result_text = "".join(transformed_lines)

            if output_file:
                output_path = self._validate_path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
                return f"Transformation complete. Output written to: {output_file}\nLines: {len(transformed_lines)}"
            else:
                return f"Transformation result:\n{result_text}"

        except UnicodeDecodeError:
            return f"Error: Cannot read {file_path} - not a text file"
        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error: {e}"


class SortTool(Tool):
    """Sort lines in a file."""

    name = "sort"
    description = (
        "Sort lines in a file alphabetically or numerically. "
        "Supports reverse sorting, unique lines only, and case-insensitive sorting."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to sort",
        },
        "numeric": {
            "type": "boolean",
            "description": "Numeric sort (default: False)",
            "nullable": True,
        },
        "reverse": {
            "type": "boolean",
            "description": "Reverse sort order (default: False)",
            "nullable": True,
        },
        "unique": {
            "type": "boolean",
            "description": "Remove duplicate lines (default: False)",
            "nullable": True,
        },
        "case_insensitive": {
            "type": "boolean",
            "description": "Case-insensitive sorting (default: False)",
            "nullable": True,
        },
        "output_file": {
            "type": "string",
            "description": "Optional output file path",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, file_path: str) -> Path:
        path = Path(file_path)
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
        file_path: str,
        numeric: bool = False,
        reverse: bool = False,
        unique: bool = False,
        case_insensitive: bool = False,
        output_file: Optional[str] = None,
    ) -> str:
        try:
            path = self._validate_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            with open(path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f.readlines()]

            original_count = len(lines)

            if unique:
                seen = set()
                unique_lines = []
                for line in lines:
                    key = line.lower() if case_insensitive else line
                    if key not in seen:
                        seen.add(key)
                        unique_lines.append(line)
                lines = unique_lines

            if numeric:

                def numeric_key(line):
                    import re

                    match = re.match(r"^(-?\d+\.?\d*)", line.strip())
                    if match:
                        try:
                            return float(match.group(1))
                        except ValueError:
                            return 0
                    return 0

                lines.sort(key=numeric_key, reverse=reverse)
            else:
                if case_insensitive:
                    lines.sort(key=str.lower, reverse=reverse)
                else:
                    lines.sort(reverse=reverse)

            result_text = "\n".join(lines) + "\n" if lines else ""

            if output_file:
                output_path = self._validate_path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
                msg = f"Sorted {original_count} lines"
                if unique:
                    msg += f" ({len(lines)} unique)"
                msg += f". Output written to: {output_file}"
                return msg
            else:
                header = f"Sorted {original_count} lines"
                if unique:
                    header += f" ({len(lines)} unique)"
                header += ":\n"
                return header + result_text

        except UnicodeDecodeError:
            return f"Error: Cannot read {file_path} - not a text file"
        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error: {e}"


class HeadTailTool(Tool):
    """View first or last N lines of a file (head/tail)."""

    name = "head_tail"
    description = (
        "View the first N lines (head) or last N lines (tail) of a file. "
        "Useful for quick file inspection and log analysis."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to view",
        },
        "mode": {
            "type": "string",
            "description": "Mode: 'head' for first N lines, 'tail' for last N lines (default: head)",
            "nullable": True,
        },
        "lines": {
            "type": "integer",
            "description": "Number of lines to show (default: 10)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, working_dir: Optional[str] = None):
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def _validate_path(self, file_path: str) -> Path:
        path = Path(file_path)
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

    def forward(self, file_path: str, mode: str = "head", lines: int = 10) -> str:
        try:
            path = self._validate_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"
            if mode not in ["head", "tail"]:
                return f"Error: Invalid mode '{mode}'. Use 'head' or 'tail'"
            if lines < 1:
                return "Error: Number of lines must be at least 1"

            with open(path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)

            if mode == "head":
                result_lines = all_lines[:lines]
                header = f"First {len(result_lines)} lines of {file_path} (total: {total_lines} lines):\n"
            else:
                result_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                header = (
                    f"Last {len(result_lines)} lines of {file_path} (total: {total_lines} lines):\n"
                )

            return header + "".join(result_lines)

        except UnicodeDecodeError:
            return f"Error: Cannot read {file_path} - not a text file"
        except ValueError as e:
            return f"Error: {e}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error: {e}"


# ============================================================================
# Phase 3: Process & System Tools
# ============================================================================


class PsTool(Tool):
    """List running processes with filtering options (ps-like)."""

    name = "ps"
    description = (
        "List running processes on the system. "
        "Supports filtering by name pattern, sorting by CPU/memory usage, "
        "and limiting the number of results. Returns process information "
        "including PID, name, CPU%, memory%, and status."
    )
    inputs = {
        "filter_name": {
            "type": "string",
            "description": "Filter processes by name pattern (case-insensitive substring match)",
            "nullable": True,
        },
        "sort_by": {
            "type": "string",
            "description": "Sort processes by field: 'cpu', 'memory', 'pid', or 'name'",
            "nullable": True,
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of processes to return (default: 50, max: 500)",
            "nullable": True,
        },
        "descending": {
            "type": "boolean",
            "description": "Sort in descending order (default: True for cpu/memory, False for pid/name)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(
        self,
        filter_name: Optional[str] = None,
        sort_by: Optional[str] = "cpu",
        limit: int = 50,
        descending: Optional[bool] = None,
    ) -> str:
        """List running processes with optional filtering and sorting.

        Args:
            filter_name: Filter processes by name pattern (case-insensitive)
            sort_by: Sort by 'cpu', 'memory', 'pid', or 'name'
            limit: Maximum number of processes to return
            descending: Sort in descending order

        Returns:
            Formatted string with process information
        """
        import psutil

        try:
            # Validate inputs
            if limit < 1:
                return "Error: Limit must be at least 1"
            if limit > 500:
                limit = 500  # Cap at 500 for safety

            valid_sort_fields = ["cpu", "memory", "pid", "name"]
            if sort_by and sort_by not in valid_sort_fields:
                return (
                    f"Error: Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"
                )

            # Default descending based on sort field
            if descending is None:
                descending = sort_by in ["cpu", "memory"]

            # Collect process information
            processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "status"]
            ):
                try:
                    pinfo = proc.info
                    # Filter by name if specified
                    if filter_name and filter_name.lower() not in pinfo["name"].lower():
                        continue

                    processes.append(
                        {
                            "pid": pinfo["pid"],
                            "name": pinfo["name"],
                            "cpu": pinfo["cpu_percent"] or 0.0,
                            "memory": pinfo["memory_percent"] or 0.0,
                            "status": pinfo["status"],
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Sort processes
            if sort_by == "cpu":
                processes.sort(key=lambda x: x["cpu"], reverse=descending)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x["memory"], reverse=descending)
            elif sort_by == "pid":
                processes.sort(key=lambda x: x["pid"], reverse=descending)
            elif sort_by == "name":
                processes.sort(key=lambda x: x["name"].lower(), reverse=descending)

            # Limit results
            processes = processes[:limit]

            if not processes:
                return "No processes found matching criteria"

            # Format output
            result = [f"Found {len(processes)} processes (showing top {limit}):\n"]
            result.append(f"{'PID':<8} {'NAME':<30} {'CPU%':<8} {'MEM%':<8} {'STATUS':<12}")
            result.append("-" * 75)

            for proc in processes:
                result.append(
                    f"{proc['pid']:<8} {proc['name']:<30} {proc['cpu']:<8.1f} "
                    f"{proc['memory']:<8.2f} {proc['status']:<12}"
                )

            return "\n".join(result)

        except ImportError:
            return "Error: psutil library not installed. Install with: pip install psutil"
        except Exception as e:
            return f"Error listing processes: {e}"


class KillTool(Tool):
    """Terminate a process by PID with safety checks."""

    name = "kill"
    description = (
        "Terminate a process by its Process ID (PID). "
        "Includes safety checks to prevent terminating critical system processes. "
        "Returns success or error message. Use with caution in production environments."
    )
    inputs = {
        "pid": {
            "type": "integer",
            "description": "Process ID (PID) to terminate",
        },
        "force": {
            "type": "boolean",
            "description": "Force kill (SIGKILL) instead of graceful termination (SIGTERM)",
            "nullable": True,
        },
    }
    output_type = "string"

    # Protected PIDs and process names (safety checks)
    PROTECTED_PIDS = [0, 1]  # kernel, init/systemd
    PROTECTED_NAMES = [
        "systemd",
        "init",
        "kernel",
        "launchd",  # macOS
        "System",
        "svchost.exe",  # Windows
        "csrss.exe",  # Windows
        "wininit.exe",  # Windows
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(self, pid: int, force: bool = False) -> str:
        """Terminate a process by PID.

        Args:
            pid: Process ID to terminate
            force: Use SIGKILL instead of SIGTERM

        Returns:
            Success or error message
        """

        import psutil

        try:
            # Validate PID
            if pid < 1:
                return "Error: Invalid PID. Must be a positive integer."

            # Check if PID exists
            if not psutil.pid_exists(pid):
                return f"Error: No process found with PID {pid}"

            # Get process info
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                return f"Error: Cannot access process {pid}: {e}"

            # Safety checks
            if pid in self.PROTECTED_PIDS:
                return f"Error: Cannot kill protected system process (PID {pid})"

            if proc_name.lower() in [name.lower() for name in self.PROTECTED_NAMES]:
                return f"Error: Cannot kill protected system process: {proc_name} (PID {pid})"

            # Check if it's the current Python process
            if pid == os.getpid():
                return "Error: Cannot kill the current process"

            # Attempt to terminate
            try:
                if force:
                    proc.kill()  # SIGKILL
                    action = "Force killed"
                else:
                    proc.terminate()  # SIGTERM
                    action = "Terminated"

                # Wait briefly to confirm termination
                try:
                    proc.wait(timeout=2)
                    return f"{action} process: {proc_name} (PID {pid})"
                except psutil.TimeoutExpired:
                    return f"{action} signal sent to process: {proc_name} (PID {pid}) - termination in progress"

            except psutil.NoSuchProcess:
                return f"Process {pid} no longer exists"
            except psutil.AccessDenied:
                return f"Error: Permission denied to kill process {pid} ({proc_name}). May require elevated privileges."

        except ImportError:
            return "Error: psutil library not installed. Install with: pip install psutil"
        except Exception as e:
            return f"Error killing process: {e}"


class EnvTool(Tool):
    """Read and set environment variables."""

    name = "env"
    description = (
        "Read or set environment variables. "
        "Can list all environment variables, get a specific variable value, "
        "or set a new variable (only affects current process and child processes). "
        "Returns variable value(s) or confirmation message."
    )
    inputs = {
        "action": {
            "type": "string",
            "description": "Action to perform: 'get', 'set', or 'list'",
        },
        "name": {
            "type": "string",
            "description": "Variable name (required for 'get' and 'set' actions)",
            "nullable": True,
        },
        "value": {
            "type": "string",
            "description": "Variable value (required for 'set' action)",
            "nullable": True,
        },
        "filter_pattern": {
            "type": "string",
            "description": "Filter environment variables by name pattern for 'list' action",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(
        self,
        action: str,
        name: Optional[str] = None,
        value: Optional[str] = None,
        filter_pattern: Optional[str] = None,
    ) -> str:
        """Perform environment variable operations.

        Args:
            action: Action to perform ('get', 'set', 'list')
            name: Variable name (for get/set)
            value: Variable value (for set)
            filter_pattern: Pattern to filter variable names (for list)

        Returns:
            Variable value(s) or confirmation message
        """
        try:
            if action == "get":
                if not name:
                    return "Error: Variable name required for 'get' action"

                env_value = os.getenv(name)
                if env_value is None:
                    return f"Environment variable '{name}' is not set"
                return f"{name}={env_value}"

            elif action == "set":
                if not name:
                    return "Error: Variable name required for 'set' action"
                if value is None:
                    return "Error: Variable value required for 'set' action"

                os.environ[name] = value
                return f"Set environment variable: {name}={value}"

            elif action == "list":
                env_vars = dict(os.environ)

                # Filter by pattern if specified
                if filter_pattern:
                    filtered = {
                        k: v for k, v in env_vars.items() if filter_pattern.lower() in k.lower()
                    }
                    env_vars = filtered

                if not env_vars:
                    return "No environment variables found matching criteria"

                # Sort and format
                sorted_vars = sorted(env_vars.items())
                result = [f"Found {len(sorted_vars)} environment variables:\n"]

                for key, val in sorted_vars:
                    # Truncate long values
                    display_val = val if len(val) <= 80 else val[:77] + "..."
                    result.append(f"{key}={display_val}")

                return "\n".join(result)

            else:
                return f"Error: Invalid action '{action}'. Must be 'get', 'set', or 'list'"

        except Exception as e:
            return f"Error: {e}"


class WhichTool(Tool):
    """Find the location of an executable in PATH."""

    name = "which"
    description = (
        "Find the full path of an executable command by searching the PATH environment variable. "
        "Returns the full path if found, or an error message if not found. "
        "Useful for locating installed programs and verifying command availability."
    )
    inputs = {
        "command": {
            "type": "string",
            "description": "Command/executable name to search for (e.g., 'python', 'git', 'node')",
        },
        "all_matches": {
            "type": "boolean",
            "description": "Return all matching paths instead of just the first one",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(self, command: str, all_matches: bool = False) -> str:
        """Find executable location in PATH.

        Args:
            command: Executable name to search for
            all_matches: Return all matches instead of first one

        Returns:
            Full path to executable or error message
        """
        import shutil

        try:
            if not command:
                return "Error: Command name cannot be empty"

            if all_matches:
                # Find all matching executables in PATH
                paths = []
                path_env = os.getenv("PATH", "")
                path_dirs = path_env.split(os.pathsep)

                for dir_path in path_dirs:
                    potential_path = os.path.join(dir_path, command)

                    # Check with and without common extensions on Windows
                    extensions = [""] if os.name != "nt" else ["", ".exe", ".bat", ".cmd", ".com"]

                    for ext in extensions:
                        full_path = potential_path + ext
                        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                            paths.append(full_path)
                            break  # Only add one match per directory

                if not paths:
                    return f"Command '{command}' not found in PATH"

                result = [f"Found {len(paths)} location(s) for '{command}':\n"]
                result.extend(paths)
                return "\n".join(result)

            else:
                # Find first matching executable
                path = shutil.which(command)
                if path:
                    return f"{command}: {path}"
                else:
                    return f"Command '{command}' not found in PATH"

        except Exception as e:
            return f"Error: {e}"


class CurlTool(Tool):
    """Make HTTP requests with support for different methods and headers."""

    name = "curl"
    description = (
        "Make HTTP requests to URLs with support for GET, POST, PUT, DELETE methods. "
        "Can send custom headers, request bodies, and query parameters. "
        "Returns response status code, headers, and body. "
        "Includes timeout and error handling for network issues."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "URL to make the request to (must start with http:// or https://)",
        },
        "method": {
            "type": "string",
            "description": "HTTP method: 'GET', 'POST', 'PUT', 'DELETE', 'HEAD'",
            "nullable": True,
        },
        "headers": {
            "type": "string",
            "description": 'JSON string of custom headers (e.g., \'{"Authorization": "Bearer token"}\')',
            "nullable": True,
        },
        "body": {
            "type": "string",
            "description": "Request body for POST/PUT requests",
            "nullable": True,
        },
        "timeout": {
            "type": "integer",
            "description": "Request timeout in seconds (default: 30)",
            "nullable": True,
        },
        "follow_redirects": {
            "type": "boolean",
            "description": "Follow HTTP redirects (default: True)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[str] = None,
        body: Optional[str] = None,
        timeout: int = 30,
        follow_redirects: bool = True,
    ) -> str:
        """Make an HTTP request.

        Args:
            url: URL to request
            method: HTTP method
            headers: JSON string of headers
            body: Request body
            timeout: Request timeout in seconds
            follow_redirects: Follow redirects

        Returns:
            Formatted response with status, headers, and body
        """
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return "Error: URL must start with http:// or https://"

            # Validate method
            valid_methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH"]
            method = method.upper()
            if method not in valid_methods:
                return f"Error: Invalid HTTP method. Must be one of: {', '.join(valid_methods)}"

            # Parse headers
            request_headers = {}
            if headers:
                try:
                    request_headers = json.loads(headers)
                    if not isinstance(request_headers, dict):
                        return "Error: Headers must be a JSON object/dictionary"
                except json.JSONDecodeError as e:
                    return f"Error: Invalid JSON in headers: {e}"

            # Prepare request
            if body:
                body_bytes = body.encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            else:
                body_bytes = None

            # Create request
            req = urllib.request.Request(
                url, data=body_bytes, headers=request_headers, method=method
            )

            # Make request
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
                    status_code = response.status
                    response_headers = dict(response.headers)
                    response_body = response.read().decode("utf-8", errors="replace")

                    # Format output
                    result = [f"HTTP {status_code} {response.reason}"]
                    result.append(f"URL: {url}")
                    result.append("\nResponse Headers:")
                    for key, value in response_headers.items():
                        # Truncate long header values
                        display_value = value if len(value) <= 100 else value[:97] + "..."
                        result.append(f"  {key}: {display_value}")

                    result.append(f"\nResponse Body ({len(response_body)} bytes):")
                    # Truncate long responses
                    if len(response_body) > 5000:
                        result.append(response_body[:5000])
                        result.append(f"\n... (truncated, total {len(response_body)} bytes)")
                    else:
                        result.append(response_body)

                    return "\n".join(result)

            except urllib.error.HTTPError as e:
                error_body = (
                    e.read().decode("utf-8", errors="replace") if e.fp else "No error details"
                )
                return (
                    f"HTTP Error {e.code}: {e.reason}\nURL: {url}\nError body: {error_body[:500]}"
                )

            except urllib.error.URLError as e:
                return f"URL Error: {e.reason}\nURL: {url}"

            except TimeoutError:
                return f"Error: Request timeout after {timeout} seconds\nURL: {url}"

        except Exception as e:
            return f"Error making HTTP request: {e}"


class PingTool(Tool):
    """Check network connectivity to a host."""

    name = "ping"
    description = (
        "Check network connectivity to a host by sending ICMP echo requests (ping). "
        "Returns round-trip time (RTT) statistics and packet loss percentage. "
        "Useful for diagnosing network issues and verifying host availability. "
        "Cross-platform support (Linux, macOS, Windows)."
    )
    inputs = {
        "host": {
            "type": "string",
            "description": "Hostname or IP address to ping (e.g., 'google.com', '8.8.8.8')",
        },
        "count": {
            "type": "integer",
            "description": "Number of ping packets to send (default: 4)",
            "nullable": True,
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds for each ping (default: 5)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def forward(self, host: str, count: int = 4, timeout: int = 5) -> str:
        """Ping a host to check connectivity.

        Args:
            host: Hostname or IP address
            count: Number of ping packets
            timeout: Timeout per ping in seconds

        Returns:
            Ping statistics including RTT and packet loss
        """
        import platform
        import re
        import subprocess  # nosec B404

        try:
            if not host:
                return "Error: Host cannot be empty"

            if count < 1:
                return "Error: Count must be at least 1"
            if count > 100:
                count = 100  # Cap at 100

            if timeout < 1:
                return "Error: Timeout must be at least 1 second"

            # Determine ping command based on platform
            system = platform.system().lower()

            if system == "windows":
                # Windows: ping -n count -w timeout_ms host
                timeout_ms = timeout * 1000
                cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), host]
            else:
                # Linux/macOS: ping -c count -W timeout host
                cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

            # Execute ping command
            try:
                result = subprocess.run(  # nosec B603
                    cmd, capture_output=True, text=True, timeout=timeout * count + 5
                )
                output = result.stdout + result.stderr

                if result.returncode == 0:
                    # Parse output for statistics
                    if system == "windows":
                        # Windows format
                        packets_match = re.search(
                            r"Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)", output
                        )
                        rtt_match = re.search(
                            r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output
                        )

                        if packets_match:
                            sent, received, lost = packets_match.groups()
                            loss_percent = (int(lost) / int(sent)) * 100 if int(sent) > 0 else 0
                        else:
                            sent = received = lost = "?"
                            loss_percent = 0

                        if rtt_match:
                            rtt_min, rtt_max, rtt_avg = rtt_match.groups()
                        else:
                            rtt_min = rtt_max = rtt_avg = "?"

                    else:
                        # Linux/macOS format
                        packets_match = re.search(
                            r"(\d+) packets transmitted, (\d+) (?:packets )?received", output
                        )
                        loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
                        rtt_match = re.search(
                            r"rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/[\d.]+ ms",
                            output,
                        )

                        if packets_match:
                            sent, received = packets_match.groups()
                            lost = int(sent) - int(received)
                        else:
                            sent = received = lost = "?"

                        if loss_match:
                            loss_percent = float(loss_match.group(1))
                        else:
                            loss_percent = 0

                        if rtt_match:
                            rtt_min, rtt_avg, rtt_max = rtt_match.groups()
                        else:
                            rtt_min = rtt_avg = rtt_max = "?"

                    # Format output
                    status = (
                        "✓ Host is reachable"
                        if float(loss_percent) < 100
                        else "✗ Host is unreachable"
                    )
                    result_lines = [
                        f"Ping statistics for {host}:",
                        f"Status: {status}",
                        f"Packets: Sent={sent}, Received={received}, Lost={lost} ({loss_percent:.1f}% loss)",
                        f"Round-trip time (ms): Min={rtt_min}, Avg={rtt_avg}, Max={rtt_max}",
                    ]
                    return "\n".join(result_lines)

                else:
                    return f"Ping failed: Host '{host}' is unreachable or does not exist\n\nOutput:\n{output[:500]}"

            except subprocess.TimeoutExpired:
                return f"Error: Ping command timed out after {timeout * count + 5} seconds"
            except FileNotFoundError:
                return "Error: Ping command not found on system"

        except Exception as e:
            return f"Error executing ping: {e}"


def get_smolagents_optional_tools(
    enabled_tools: List[str],
    search_provider: str = "duckduckgo",
    additional_imports: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
) -> List[Tool]:
    """Get optional tools from smolagents.default_tools and custom tools (Phases 1-3).

    Available optional tools:
    - google_search: GoogleSearchTool (requires SERPER_API_KEY, BRAVE_API_KEY, or provider=duckduckgo)
    - duckduckgo_search: DuckDuckGoSearchTool
    - visit_webpage: VisitWebpageTool
    - python_interpreter: PythonInterpreterTool
    - wikipedia_search: WikipediaSearchTool
    - user_input: UserInputTool

    Phase 1 - File Operations (require working_dir):
    - read_file: ReadFileTool
    - write_file: WriteFileTool
    - list_directory: ListDirectoryTool
    - search_files: FileSearchTool

    Phase 2 - Text Processing (require working_dir):
    - grep: GrepTool
    - sed: SedTool
    - sort: SortTool
    - head_tail: HeadTailTool

    Phase 3 - Process & System Tools (no working_dir needed):
    - ps: PsTool (list processes)
    - kill: KillTool (terminate processes)
    - env: EnvTool (environment variables)
    - which: WhichTool (find executables)
    - curl: CurlTool (HTTP requests)
    - ping: PingTool (network connectivity)

    Args:
        enabled_tools: List of tool names to enable (e.g., ["google_search", "visit_webpage", "read_file"])
        search_provider: Provider for GoogleSearchTool ("serper", "brave", "duckduckgo")
        additional_imports: Additional Python modules to authorize for PythonInterpreterTool
        working_dir: Working directory for file tools (defaults to current directory if not specified)

    Returns:
        List of enabled Tool instances from smolagents.default_tools and custom file tools
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

    # Custom Tools (Phase 1-3) - For GAIA/SWE/DevOps/SRE benchmarks
    # Phase 1 & 2 require working_dir for security (path traversal prevention)
    # Phase 3 system tools don't require working_dir

    file_tools_map = {
        # Phase 1: File Operations (require working_dir)
        "read_file": (ReadFileTool, "ReadFileTool", True),
        "write_file": (WriteFileTool, "WriteFileTool", True),
        "list_directory": (ListDirectoryTool, "ListDirectoryTool", True),
        "search_files": (FileSearchTool, "FileSearchTool", True),
        # Phase 2: Text Processing (require working_dir)
        "grep": (GrepTool, "GrepTool", True),
        "sed": (SedTool, "SedTool", True),
        "sort": (SortTool, "SortTool", True),
        "head_tail": (HeadTailTool, "HeadTailTool", True),
        # Phase 3: Process & System Tools (no working_dir needed)
        "ps": (PsTool, "PsTool", False),
        "kill": (KillTool, "KillTool", False),
        "env": (EnvTool, "EnvTool", False),
        "which": (WhichTool, "WhichTool", False),
        "curl": (CurlTool, "CurlTool", False),
        "ping": (PingTool, "PingTool", False),
    }

    # Check if any custom tools are requested
    requested_file_tools = [tool for tool in enabled_tools if tool in file_tools_map]

    if requested_file_tools:
        # Use provided working_dir or default to current directory
        work_dir = working_dir if working_dir else os.getcwd()
        print(f"[TOOLS] Custom tools working directory: {work_dir}")

        for tool_name in requested_file_tools:
            try:
                tool_class, display_name, requires_working_dir = file_tools_map[tool_name]

                if requires_working_dir:
                    tools.append(tool_class(working_dir=work_dir))
                    print(f"[TOOLS] Enabled {display_name} (working_dir: {work_dir})")
                else:
                    tools.append(tool_class())
                    print(f"[TOOLS] Enabled {display_name} (system tool)")
            except Exception as e:
                print(f"[WARNING] Failed to initialize {display_name}: {e}")

    return tools


def get_all_tools(
    search_provider: str = "duckduckgo",
    additional_imports: Optional[List[str]] = None,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
) -> List[Tool]:
    """Get all available tools: default tools + optional smolagents tools + file tools.

    By default, returns 5 default tools required for kshitijthakkar/smoltrace-tasks:
    - WeatherTool (custom)
    - CalculatorTool (custom)
    - TimeTool (custom)
    - DuckDuckGoSearchTool (from smolagents) - Required for web search tasks
    - PythonInterpreterTool (from smolagents) - Required for code execution tasks

    Optionally enable additional tools via enabled_smolagents_tools parameter.

    Args:
        search_provider: Provider for GoogleSearchTool ("serper", "brave", "duckduckgo")
        additional_imports: Additional Python modules for PythonInterpreterTool
        enabled_smolagents_tools: List of additional tool names to enable
            Smolagents tools: ["google_search", "visit_webpage", "wikipedia_search", "user_input"]
            File tools: ["read_file", "write_file", "list_directory", "search_files"]
            Note: "duckduckgo_search" and "python_interpreter" are already enabled by default
        working_dir: Working directory for file tools (defaults to current directory)

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

    # Add optional smolagents tools and file tools if requested
    if enabled_smolagents_tools:
        smolagents_tools = get_smolagents_optional_tools(
            enabled_smolagents_tools, search_provider, additional_imports, working_dir
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
