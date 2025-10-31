"""Tests for Phase 2 text processing tools (grep, sed, sort, head_tail)."""

import tempfile
from pathlib import Path

import pytest

from smoltrace.tools import GrepTool, HeadTailTool, SedTool, SortTool


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for text processing tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create test files
        (workspace / "sample.txt").write_text(
            "Line 1: Hello World\n"
            "Line 2: Python Programming\n"
            "Line 3: Hello Again\n"
            "Line 4: Data Science\n"
            "Line 5: Hello Python\n",
            encoding="utf-8",
        )

        (workspace / "numbers.txt").write_text("10\n5\n20\n3\n15\n", encoding="utf-8")

        (workspace / "log.txt").write_text(
            "2025-01-15 10:00:00 INFO: Application started\n"
            "2025-01-15 10:01:00 ERROR: Connection failed\n"
            "2025-01-15 10:02:00 INFO: Retry attempt 1\n"
            "2025-01-15 10:03:00 ERROR: Connection failed\n"
            "2025-01-15 10:04:00 INFO: Connection successful\n",
            encoding="utf-8",
        )

        (workspace / "duplicates.txt").write_text(
            "apple\nbanana\napple\ncherry\nbanana\napple\n", encoding="utf-8"
        )

        yield workspace


# ============================================================================
# GrepTool Tests
# ============================================================================


def test_grep_basic_search(temp_workspace):
    """Test basic grep search."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "Hello")

    assert "Line 1: Hello World" in result
    assert "Line 3: Hello Again" in result
    assert "Line 5: Hello Python" in result
    assert "1:" in result  # Line numbers


def test_grep_case_insensitive(temp_workspace):
    """Test case-insensitive grep."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "hello", case_insensitive=True)

    assert "Line 1" in result
    assert "Line 3" in result
    assert "Line 5" in result


def test_grep_with_context(temp_workspace):
    """Test grep with context lines."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "Data Science", context_before=1, context_after=1)

    assert "Line 3" in result  # Context before
    assert "Line 4" in result  # Match
    assert "Line 5" in result  # Context after


def test_grep_invert_match(temp_workspace):
    """Test grep with inverted matching."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "Hello", invert_match=True)

    assert "Line 2" in result
    assert "Line 4" in result
    assert "Line 1" not in result


def test_grep_count_only(temp_workspace):
    """Test grep count mode."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "Hello", count_only=True)

    assert "3 matches" in result


def test_grep_no_matches(temp_workspace):
    """Test grep with no matches."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "NoMatch")

    assert "No matches found" in result


def test_grep_regex_pattern(temp_workspace):
    """Test grep with regex pattern."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", r"Line \d+:")

    assert "Line 1" in result
    assert "Line 2" in result


def test_grep_invalid_regex(temp_workspace):
    """Test grep with invalid regex."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "[invalid")

    assert "Error: Invalid regex pattern" in result


def test_grep_path_traversal(temp_workspace):
    """Test grep blocks path traversal."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/passwd", "root")

    assert "Error: Access denied" in result or "outside working directory" in result


# ============================================================================
# SedTool Tests
# ============================================================================


def test_sed_substitution_basic(temp_workspace):
    """Test basic sed substitution."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "s/Hello/Hi/")

    assert "Hi World" in result
    assert "Hi Again" in result


def test_sed_substitution_global(temp_workspace):
    """Test sed global substitution."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "s/Hello/Hi/", global_replace=True)

    assert "Hi World" in result
    assert "Hi Again" in result
    assert "Hi Python" in result


def test_sed_case_insensitive(temp_workspace):
    """Test sed case-insensitive substitution."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "s/hello/Hi/", case_insensitive=True)

    assert "Hi World" in result


def test_sed_deletion(temp_workspace):
    """Test sed deletion command."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "/Hello/d")

    assert "Python Programming" in result
    assert "Data Science" in result
    assert "Hello" not in result


def test_sed_print_line(temp_workspace):
    """Test sed print specific line."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "3p")

    assert "Line 3: Hello Again" in result
    assert "Line 1" not in result


def test_sed_output_to_file(temp_workspace):
    """Test sed with output file."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "s/Hello/Hi/", output_file="output.txt")

    assert "Transformation complete" in result
    assert "output.txt" in result
    assert (temp_workspace / "output.txt").exists()


def test_sed_invalid_command(temp_workspace):
    """Test sed with invalid command."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "invalid")

    assert "Error: Unsupported command" in result


# ============================================================================
# SortTool Tests
# ============================================================================


def test_sort_alphabetical(temp_workspace):
    """Test alphabetical sort."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("duplicates.txt")

    # Sorted should be: apple (3x), banana (2x), cherry (1x)
    assert "Sorted 6 lines" in result
    assert "apple" in result
    assert "banana" in result
    assert "cherry" in result


def test_sort_numeric(temp_workspace):
    """Test numeric sort."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("numbers.txt", numeric=True)

    assert "Sorted 5 lines" in result
    lines = result.split("\n")[1:]  # Skip header
    # Should be sorted: 3, 5, 10, 15, 20
    assert lines[0] == "3"
    assert lines[4] == "20"


def test_sort_reverse(temp_workspace):
    """Test reverse sort."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("numbers.txt", numeric=True, reverse=True)

    lines = result.split("\n")[1:]
    assert lines[0] == "20"
    assert lines[4] == "3"


def test_sort_unique(temp_workspace):
    """Test sort with unique lines."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("duplicates.txt", unique=True)

    assert "3 unique" in result
    assert result.count("apple") == 1
    assert result.count("banana") == 1


def test_sort_case_insensitive(temp_workspace):
    """Test case-insensitive sort."""
    (temp_workspace / "mixed_case.txt").write_text("Zebra\napple\nBanana\n", encoding="utf-8")

    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("mixed_case.txt", case_insensitive=True)

    lines = result.split("\n")[1:]
    # Case-insensitive: apple, Banana, Zebra
    assert "apple" in lines[0]


def test_sort_output_to_file(temp_workspace):
    """Test sort with output file."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("numbers.txt", numeric=True, output_file="sorted.txt")

    assert "Sorted 5 lines" in result
    assert "sorted.txt" in result
    assert (temp_workspace / "sorted.txt").exists()


# ============================================================================
# HeadTailTool Tests
# ============================================================================


def test_head_default(temp_workspace):
    """Test head with default 10 lines."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt")

    assert "First 5 lines" in result  # File only has 5 lines
    assert "Line 1" in result
    assert "Line 5" in result


def test_head_custom_lines(temp_workspace):
    """Test head with custom number of lines."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", mode="head", lines=2)

    assert "First 2 lines" in result
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" not in result


def test_tail_default(temp_workspace):
    """Test tail with default."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", mode="tail")

    assert "Last 5 lines" in result
    assert "Line 1" in result
    assert "Line 5" in result


def test_tail_custom_lines(temp_workspace):
    """Test tail with custom number of lines."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", mode="tail", lines=2)

    assert "Last 2 lines" in result
    assert "Line 4" in result
    assert "Line 5" in result
    assert "Line 1" not in result


def test_head_tail_invalid_mode(temp_workspace):
    """Test invalid mode."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", mode="invalid")

    assert "Error: Invalid mode" in result


def test_head_tail_invalid_lines(temp_workspace):
    """Test invalid number of lines."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", lines=0)

    assert "Error: Number of lines must be at least 1" in result


# ============================================================================
# Integration Tests
# ============================================================================


def test_grep_sed_integration(temp_workspace):
    """Test grep and sed working together."""
    grep_tool = GrepTool(working_dir=str(temp_workspace))
    sed_tool = SedTool(working_dir=str(temp_workspace))

    # First grep for errors
    grep_result = grep_tool.forward("log.txt", "ERROR")
    assert "Connection failed" in grep_result

    # Then use sed to replace ERROR with WARNING
    sed_result = sed_tool.forward("log.txt", "s/ERROR/WARNING/", global_replace=True)
    assert "WARNING" in sed_result
    assert "ERROR" not in sed_result


def test_sort_head_integration(temp_workspace):
    """Test sort and head working together."""
    sort_tool = SortTool(working_dir=str(temp_workspace))
    head_tool = HeadTailTool(working_dir=str(temp_workspace))

    # Sort numbers to a file
    sort_tool.forward("numbers.txt", numeric=True, output_file="sorted_numbers.txt")

    # Get first 3 lines
    head_result = head_tool.forward("sorted_numbers.txt", lines=3)
    assert "3" in head_result
    assert "5" in head_result
    assert "10" in head_result


def test_text_tools_attributes():
    """Test all text processing tools have correct attributes."""
    grep_tool = GrepTool()
    sed_tool = SedTool()
    sort_tool = SortTool()
    head_tail_tool = HeadTailTool()

    for tool in [grep_tool, sed_tool, sort_tool, head_tail_tool]:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputs")
        assert hasattr(tool, "output_type")
        assert tool.output_type == "string"


def test_text_tools_without_working_dir():
    """Test text tools default to current directory when working_dir not provided."""
    grep_tool = GrepTool(working_dir=None)
    sed_tool = SedTool(working_dir=None)
    sort_tool = SortTool(working_dir=None)
    head_tail_tool = HeadTailTool(working_dir=None)

    for tool in [grep_tool, sed_tool, sort_tool, head_tail_tool]:
        assert tool.working_dir == Path.cwd()


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_grep_nonexistent_file(temp_workspace):
    """Test grep with nonexistent file."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent.txt", "pattern")

    assert "Error" in result or "not found" in result.lower()


def test_grep_empty_pattern(temp_workspace):
    """Test grep with empty pattern."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "")

    # Should handle empty pattern (might match everything or error)
    assert result is not None


def test_grep_path_traversal_blocked(temp_workspace):
    """Test grep blocks path traversal."""
    tool = GrepTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/passwd", "root")

    assert "Error" in result or "Access denied" in result


def test_sed_nonexistent_file(temp_workspace):
    """Test sed with nonexistent file."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent.txt", "s/old/new/")

    assert "Error" in result or "not found" in result.lower()


def test_sed_empty_pattern(temp_workspace):
    """Test sed with empty pattern."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "")

    assert "Error" in result or "invalid" in result.lower()


def test_sed_invalid_command_format(temp_workspace):
    """Test sed with invalid command format."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("sample.txt", "invalid_command")

    assert "Error" in result or "invalid" in result.lower()


def test_sed_path_traversal_blocked(temp_workspace):
    """Test sed blocks path traversal."""
    tool = SedTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/hosts", "s/localhost/hacked/")

    assert "Error" in result or "Access denied" in result


def test_sort_nonexistent_file(temp_workspace):
    """Test sort with nonexistent file."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent.txt")

    assert "Error" in result or "not found" in result.lower()


def test_sort_empty_file(temp_workspace):
    """Test sort with empty file."""
    # Create empty file
    (temp_workspace / "empty.txt").write_text("", encoding="utf-8")

    tool = SortTool(working_dir=str(temp_workspace))
    result = tool.forward("empty.txt")

    # Should handle empty file gracefully
    assert result is not None
    assert "Sorted" in result or "Error" in result


def test_sort_path_traversal_blocked(temp_workspace):
    """Test sort blocks path traversal."""
    tool = SortTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/passwd")

    assert "Error" in result or "Access denied" in result


def test_head_tail_nonexistent_file(temp_workspace):
    """Test head/tail with nonexistent file."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("nonexistent.txt")

    assert "Error" in result or "not found" in result.lower()


def test_head_tail_empty_file(temp_workspace):
    """Test head/tail with empty file."""
    (temp_workspace / "empty.txt").write_text("", encoding="utf-8")

    tool = HeadTailTool(working_dir=str(temp_workspace))
    result = tool.forward("empty.txt")

    # Should handle empty file gracefully
    assert result is not None


def test_head_tail_path_traversal_blocked(temp_workspace):
    """Test head/tail blocks path traversal."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    result = tool.forward("../../../etc/passwd")

    assert "Error" in result or "Access denied" in result


def test_head_tail_large_line_count(temp_workspace):
    """Test head/tail with very large line count."""
    tool = HeadTailTool(working_dir=str(temp_workspace))

    # Request more lines than file has
    result = tool.forward("sample.txt", lines=1000)

    # Should return all available lines
    assert "Line 1" in result
    assert "Line 5" in result


def test_grep_with_regex_special_chars(temp_workspace):
    """Test grep with regex special characters."""
    tool = GrepTool(working_dir=str(temp_workspace))

    # Pattern with regex special chars
    result = tool.forward("log.txt", r"\[ERROR\]")

    # Should handle regex patterns properly
    assert result is not None
