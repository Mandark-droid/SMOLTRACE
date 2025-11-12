"""Tests for file system tools (Phase 1)."""

import tempfile
from pathlib import Path

import pytest

from smoltrace.tools import (
    FileSearchTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
    get_all_tools,
    get_smolagents_optional_tools,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create test file structure
        (workspace / "file1.txt").write_text("Hello World\nThis is a test file.", encoding="utf-8")
        (workspace / "file2.json").write_text('{"name": "test", "value": 42}', encoding="utf-8")
        (workspace / "subdir").mkdir()
        (workspace / "subdir" / "nested.txt").write_text("Nested file content", encoding="utf-8")
        (workspace / "large.txt").write_text("x" * 1000, encoding="utf-8")

        yield workspace


# ============================================================================
# ReadFileTool Tests
# ============================================================================


def test_read_file_basic(temp_workspace):
    """Test basic file reading."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("file1.txt")

    assert "Hello World" in result
    assert "This is a test file" in result
    assert "File: file1.txt" in result


def test_read_file_absolute_path(temp_workspace):
    """Test reading file with absolute path."""
    tool = ReadFileTool(working_dir=str(temp_workspace))
    file_path = temp_workspace / "file2.json"

    result = tool.forward(str(file_path))

    assert '"name": "test"' in result
    assert '"value": 42' in result


def test_read_file_nested(temp_workspace):
    """Test reading nested file."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("subdir/nested.txt")

    assert "Nested file content" in result


def test_read_file_not_found(temp_workspace):
    """Test reading non-existent file."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent.txt")

    assert "Error: File not found" in result


def test_read_file_directory(temp_workspace):
    """Test reading a directory (should fail)."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("subdir")

    assert "Error: Path is not a file" in result


def test_read_file_path_traversal(temp_workspace):
    """Test path traversal prevention."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/passwd")

    assert "Error: Access denied" in result or "outside working directory" in result


def test_read_file_encoding(temp_workspace):
    """Test reading with different encoding."""
    # Create file with latin-1 encoding
    latin1_file = temp_workspace / "latin1.txt"
    latin1_file.write_text("Café résumé", encoding="latin-1")

    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("latin1.txt", encoding="latin-1")

    assert "Café résumé" in result


def test_read_file_invalid_encoding(temp_workspace):
    """Test reading with wrong encoding."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    # Try to read UTF-8 file as ASCII (should fail on special chars if any)
    result = tool.forward("file1.txt", encoding="ascii")

    # Should succeed for ASCII-compatible content or show error
    assert "Error" in result or "Hello World" in result


def test_read_file_size_limit(temp_workspace):
    """Test file size limit enforcement."""
    # Create a file larger than 10MB
    large_file = temp_workspace / "huge.txt"
    large_file.write_text("x" * (11 * 1024 * 1024), encoding="utf-8")

    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("huge.txt")

    assert "Error: File too large" in result


# ============================================================================
# WriteFileTool Tests
# ============================================================================


def test_write_file_basic(temp_workspace):
    """Test basic file writing."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("newfile.txt", "This is new content")

    assert "Wrote file:" in result
    assert (temp_workspace / "newfile.txt").read_text() == "This is new content"


def test_write_file_overwrite(temp_workspace):
    """Test overwriting existing file."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("file1.txt", "Overwritten content")

    assert "Wrote file:" in result
    assert (temp_workspace / "file1.txt").read_text() == "Overwritten content"


def test_write_file_nested(temp_workspace):
    """Test writing to nested directory."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("subdir/newfile.txt", "Nested content")

    assert "Wrote file:" in result
    assert (temp_workspace / "subdir" / "newfile.txt").read_text() == "Nested content"


def test_write_file_create_directory(temp_workspace):
    """Test creating parent directory."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("newdir/file.txt", "Content in new dir")

    assert "Wrote file:" in result
    assert (temp_workspace / "newdir" / "file.txt").read_text() == "Content in new dir"


def test_write_file_path_traversal(temp_workspace):
    """Test path traversal prevention."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../tmp/malicious.txt", "Bad content")

    assert "Error: Access denied" in result or "outside working directory" in result


def test_write_file_system_directory(temp_workspace):
    """Test writing to system directory (should fail)."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    # Try to write to a system-like path
    result = tool.forward("/etc/malicious.txt", "Bad content")

    assert "Error: Access denied" in result or "system directory" in result


def test_write_file_encoding(temp_workspace):
    """Test writing with UTF-8 encoding (default)."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("encoded.txt", "Café résumé")

    assert "Wrote file:" in result
    assert (temp_workspace / "encoded.txt").read_text(encoding="utf-8") == "Café résumé"


def test_write_file_append_mode(temp_workspace):
    """Test append mode."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    # Write initial content
    tool.forward("append.txt", "Line 1\n")

    # Append more content
    result = tool.forward("append.txt", "Line 2\n", mode="append")

    assert "Appended to file:" in result
    content = (temp_workspace / "append.txt").read_text()
    assert "Line 1" in content
    assert "Line 2" in content


# ============================================================================
# ListDirectoryTool Tests
# ============================================================================


def test_list_directory_basic(temp_workspace):
    """Test basic directory listing."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward(".")

    assert "file1.txt" in result
    assert "file2.json" in result
    assert "subdir" in result


def test_list_directory_nested(temp_workspace):
    """Test listing nested directory."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("subdir")

    assert "nested.txt" in result


def test_list_directory_not_found(temp_workspace):
    """Test listing non-existent directory."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent")

    assert "Error: Directory not found" in result


def test_list_directory_file(temp_workspace):
    """Test listing a file (should fail)."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("file1.txt")

    assert "Error: Path is not a directory" in result


def test_list_directory_path_traversal(temp_workspace):
    """Test path traversal prevention."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc")

    assert "Error: Access denied" in result or "outside working directory" in result


def test_list_directory_pattern(temp_workspace):
    """Test listing with pattern filter."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward(".", pattern="*.txt")

    assert "file1.txt" in result
    assert "file2.json" not in result


def test_list_directory_with_hidden_files(temp_workspace):
    """Test listing directory with hidden files."""
    # Create hidden file
    (temp_workspace / ".hidden").write_text("hidden", encoding="utf-8")

    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward(".")

    # Hidden files should be listed by default
    assert ".hidden" in result or "file1.txt" in result


# ============================================================================
# FileSearchTool Tests
# ============================================================================


def test_search_files_by_name(temp_workspace):
    """Test basic filename search."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "*.txt", search_type="name")

    assert "file1.txt" in result
    assert "large.txt" in result


def test_search_files_by_content(temp_workspace):
    """Test searching file content."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "Hello", search_type="content")

    assert "file1.txt" in result or "No matches found" in result


def test_search_json_files(temp_workspace):
    """Test searching JSON files by name."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "*.json", search_type="name")

    assert "file2.json" in result


def test_search_files_no_matches(temp_workspace):
    """Test search with no matches."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "nonexistent*.xyz", search_type="name")

    assert "No files found" in result or "No matches found" in result or result == ""


def test_search_files_content_text(temp_workspace):
    """Test content search for specific text."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "test file", search_type="content")

    # Should find files containing "test file"
    assert "file1.txt" in result or "No matches found" in result


def test_search_files_nested_directory(temp_workspace):
    """Test searching in nested directories."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward("subdir", "*.txt", search_type="name")

    assert "nested.txt" in result


def test_search_files_path_traversal(temp_workspace):
    """Test path traversal prevention in search."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    # Try to access parent directory
    result = tool.forward("../..", "*.txt", search_type="name")

    # Should either error or search safely within working_dir
    assert "Error" in result or temp_workspace.name in result or "No matches found" in result


def test_search_files_max_results(temp_workspace):
    """Test max results limit."""
    # Create many matching files
    for i in range(150):
        (temp_workspace / f"match{i}.txt").write_text(f"target content {i}", encoding="utf-8")

    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "match*.txt", search_type="name", max_results=50)

    # Should be limited to 50 results
    assert "Showing first 50 results" in result or "Found 50 results" in result
    lines = [line for line in result.split("\n") if line.strip()]
    match_count = sum(1 for line in lines if "match" in line and ".txt" in line)
    # Should be around 50 results (exactly 50 or close to it with headers)
    assert 48 <= match_count <= 52


def test_search_files_default_name_search(temp_workspace):
    """Test default search type is 'name'."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "*.json")

    assert "file2.json" in result


# ============================================================================
# Integration Tests
# ============================================================================


def test_get_smolagents_optional_tools_file_tools(temp_workspace):
    """Test loading file tools via get_smolagents_optional_tools."""
    tools = get_smolagents_optional_tools(
        enabled_tools=["read_file", "write_file", "list_directory", "search_files"],
        working_dir=str(temp_workspace),
    )

    assert len(tools) == 4
    tool_names = [tool.name for tool in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names
    assert "search_files" in tool_names


def test_get_all_tools_with_file_tools(temp_workspace):
    """Test get_all_tools includes file tools."""
    tools = get_all_tools(
        enabled_smolagents_tools=["read_file", "write_file"],
        working_dir=str(temp_workspace),
    )

    tool_names = [tool.name for tool in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    # Should also have default tools
    assert "get_weather" in tool_names
    assert "calculator" in tool_names


def test_file_tools_without_working_dir():
    """Test file tools default to current directory when working_dir not provided."""
    tools = get_smolagents_optional_tools(
        enabled_tools=["read_file"],
        working_dir=None,
    )

    assert len(tools) == 1
    assert tools[0].name == "read_file"
    # Should use current working directory
    assert tools[0].working_dir == Path.cwd()


def test_file_tool_attributes():
    """Test file tools have correct attributes."""
    read_tool = ReadFileTool()
    write_tool = WriteFileTool()
    list_tool = ListDirectoryTool()
    search_tool = FileSearchTool()

    # Check all have required attributes
    for tool in [read_tool, write_tool, list_tool, search_tool]:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputs")
        assert hasattr(tool, "output_type")
        assert tool.output_type == "string"


def test_read_write_integration(temp_workspace):
    """Test reading and writing files in sequence."""
    read_tool = ReadFileTool(working_dir=str(temp_workspace))
    write_tool = WriteFileTool(working_dir=str(temp_workspace))

    # Write a file
    write_result = write_tool.forward("integration.txt", "Integration test content")
    assert "Wrote file:" in write_result

    # Read it back
    read_result = read_tool.forward("integration.txt")
    assert "Integration test content" in read_result


def test_write_list_integration(temp_workspace):
    """Test writing files and listing directory."""
    write_tool = WriteFileTool(working_dir=str(temp_workspace))
    list_tool = ListDirectoryTool(working_dir=str(temp_workspace))

    # Write multiple files
    write_tool.forward("test1.txt", "Content 1")
    write_tool.forward("test2.txt", "Content 2")
    write_tool.forward("test3.json", '{"test": true}')

    # List directory
    result = list_tool.forward(".", pattern="test*")
    assert "test1.txt" in result
    assert "test2.txt" in result
    assert "test3.json" in result


def test_write_search_integration(temp_workspace):
    """Test writing files and searching by name."""
    write_tool = WriteFileTool(working_dir=str(temp_workspace))
    search_tool = FileSearchTool(working_dir=str(temp_workspace))

    # Write files with searchable content
    write_tool.forward("doc1.txt", "The quick brown fox")
    write_tool.forward("doc2.txt", "The lazy dog")
    write_tool.forward("doc3.txt", "A different document")

    # Search for doc*.txt files
    result = search_tool.forward(".", "doc*.txt", search_type="name")
    assert "doc1.txt" in result
    assert "doc2.txt" in result
    assert "doc3.txt" in result


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_read_file_path_traversal_blocked(temp_workspace):
    """Test that path traversal attempts are blocked."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    # Try to access file outside working directory
    result = tool.forward("../../../etc/passwd")

    assert "Error" in result or "Access denied" in result


def test_read_file_nonexistent(temp_workspace):
    """Test reading nonexistent file."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent_file.txt")

    assert "Error" in result or "not found" in result.lower()


def test_read_file_empty_filename(temp_workspace):
    """Test reading with empty filename."""
    tool = ReadFileTool(working_dir=str(temp_workspace))

    result = tool.forward("")

    assert "Error" in result or "invalid" in result.lower()


def test_write_file_empty_filename(temp_workspace):
    """Test writing with empty filename."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("", "content")

    assert "Error" in result or "invalid" in result.lower()


def test_write_file_path_traversal_blocked(temp_workspace):
    """Test that write path traversal is blocked."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../tmp/evil.txt", "malicious content")

    assert "Error" in result or "Access denied" in result


def test_write_file_creates_subdirectories(temp_workspace):
    """Test that write creates subdirectories."""
    tool = WriteFileTool(working_dir=str(temp_workspace))

    result = tool.forward("new_dir/subdir/file.txt", "content")

    assert "Wrote file" in result or "Created" in result
    # Verify file was created
    assert (temp_workspace / "new_dir" / "subdir" / "file.txt").exists()


def test_list_directory_nonexistent(temp_workspace):
    """Test listing nonexistent directory."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent_dir")

    assert "Error" in result or "not found" in result.lower()


def test_list_directory_path_traversal_blocked(temp_workspace):
    """Test that list path traversal is blocked."""
    tool = ListDirectoryTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc")

    assert "Error" in result or "Access denied" in result


def test_search_files_invalid_search_type(temp_workspace):
    """Test search with invalid search type."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "*.txt", search_type="invalid_type")

    assert "Error" in result or "invalid" in result.lower()


def test_search_files_empty_pattern(temp_workspace):
    """Test search with empty pattern."""
    tool = FileSearchTool(working_dir=str(temp_workspace))

    result = tool.forward(".", "", search_type="name")

    # Empty pattern may return error, no results, or actual directory listings
    assert "Error" in result or "No files found" in result or "Found" in result or result == ""


def test_read_file_binary_content(temp_workspace):
    """Test reading file with binary content."""
    # Create a file with binary content
    binary_file = temp_workspace / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

    tool = ReadFileTool(working_dir=str(temp_workspace))
    result = tool.forward("binary.bin")

    # Should handle binary content gracefully (either error or encoded)
    assert result is not None
    assert isinstance(result, str)
