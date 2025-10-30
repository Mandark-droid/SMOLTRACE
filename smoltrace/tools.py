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


def get_smolagents_optional_tools(
    enabled_tools: List[str],
    search_provider: str = "duckduckgo",
    additional_imports: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
) -> List[Tool]:
    """Get optional tools from smolagents.default_tools and custom file tools.

    Available optional tools:
    - google_search: GoogleSearchTool (requires SERPER_API_KEY, BRAVE_API_KEY, or provider=duckduckgo)
    - duckduckgo_search: DuckDuckGoSearchTool
    - visit_webpage: VisitWebpageTool
    - python_interpreter: PythonInterpreterTool
    - wikipedia_search: WikipediaSearchTool
    - user_input: UserInputTool
    - read_file: ReadFileTool (requires working_dir)
    - write_file: WriteFileTool (requires working_dir)
    - list_directory: ListDirectoryTool (requires working_dir)
    - search_files: FileSearchTool (requires working_dir)

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

    # File System Tools (Phase 1 + Phase 2) - Custom tools for GAIA/SWE/DevOps benchmarks
    # These tools require a working directory for security (path traversal prevention)

    file_tools_map = {
        # Phase 1: File Operations
        "read_file": (ReadFileTool, "ReadFileTool"),
        "write_file": (WriteFileTool, "WriteFileTool"),
        "list_directory": (ListDirectoryTool, "ListDirectoryTool"),
        "search_files": (FileSearchTool, "FileSearchTool"),
        # Phase 2: Text Processing
        "grep": (GrepTool, "GrepTool"),
        "sed": (SedTool, "SedTool"),
        "sort": (SortTool, "SortTool"),
        "head_tail": (HeadTailTool, "HeadTailTool"),
    }

    # Check if any file tools are requested
    requested_file_tools = [tool for tool in enabled_tools if tool in file_tools_map]

    if requested_file_tools:
        # Use provided working_dir or default to current directory
        work_dir = working_dir if working_dir else os.getcwd()
        print(f"[TOOLS] File tools working directory: {work_dir}")

        for tool_name in requested_file_tools:
            try:
                tool_class, display_name = file_tools_map[tool_name]
                tools.append(tool_class(working_dir=work_dir))
                print(f"[TOOLS] Enabled {display_name} (working_dir: {work_dir})")
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
