"""Final tests to push coverage from 88.93% to 90%+.

Targeting specific uncovered lines in core.py and utils.py.
"""

from unittest.mock import Mock, patch


def test_run_evaluation_with_verbose(mocker, capsys):
    """Test run_evaluation with verbose=True to cover print statements."""
    from smoltrace.core import run_evaluation

    mocker.patch(
        "smoltrace.core.load_test_cases_from_hf",
        return_value=[{"id": "test1", "prompt": "Test", "agent_types": ["tool"]}],
    )

    mocker.patch(
        "smoltrace.core.setup_inmemory_otel",
        return_value=(None, None, None, None, None, "test-run-id"),
    )

    mock_agent = Mock()
    mock_agent.run.return_value = "Test response"
    mocker.patch("smoltrace.core.initialize_agent", return_value=mock_agent)
    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})

    mocker.patch("smoltrace.core.extract_traces", return_value=[])
    mocker.patch("smoltrace.core.extract_metrics", return_value=[])

    # Mock print_combined_summary to verify it's called
    mock_print = mocker.patch("smoltrace.core.print_combined_summary")

    run_evaluation(
        model_name="openai/gpt-3.5-turbo",
        provider="litellm",
        agent_types=["tool"],
        test_subset=None,
        dataset_name="test/dataset",
        split="train",
        verbose=True,  # Enable verbose
        debug=False,
        enable_otel=False,
    )

    # Verify print was called
    mock_print.assert_called_once()


def test_run_evaluation_with_multiple_agent_types_verbose(mocker):
    """Test run_evaluation with both agent types and verbose output."""
    from smoltrace.core import run_evaluation

    mocker.patch(
        "smoltrace.core.load_test_cases_from_hf",
        return_value=[{"id": "test1", "prompt": "Test", "agent_types": ["tool", "code"]}],
    )

    mocker.patch(
        "smoltrace.core.setup_inmemory_otel",
        return_value=(None, None, None, None, None, "test-run-id"),
    )

    mock_agent = Mock()
    mock_agent.run.return_value = "Test"
    mocker.patch("smoltrace.core.initialize_agent", return_value=mock_agent)
    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})

    mocker.patch("smoltrace.core.extract_traces", return_value=[])
    mocker.patch("smoltrace.core.extract_metrics", return_value=[])

    results, _, _, _, _ = run_evaluation(
        model_name="openai/gpt-3.5-turbo",
        provider="litellm",
        agent_types=["tool", "code"],
        test_subset=None,
        dataset_name="test/dataset",
        split="train",
        verbose=True,
        debug=False,
        enable_otel=False,
    )

    assert "tool" in results
    assert "code" in results


def test_run_evaluation_enhanced_trace_info_creation(mocker):
    """Test that enhanced_trace_info is created when OTEL enabled."""
    from smoltrace.core import run_evaluation

    mocker.patch(
        "smoltrace.core.load_test_cases_from_hf",
        return_value=[
            {
                "id": "test1",
                "prompt": "Test",
                "agent_type": "tool",
                "difficulty": "easy",
                "expected_tool": "test_tool",
            }
        ],
    )

    mock_span_exporter = Mock()
    mock_metric_exporter = Mock()
    mocker.patch(
        "smoltrace.core.setup_inmemory_otel",
        return_value=(None, None, mock_span_exporter, mock_metric_exporter, None, "test-run-id"),
    )

    mock_agent = Mock()
    mock_agent.run.return_value = "Test"
    mock_agent.tools = []

    # Mock analyze_streamed_steps to return proper values
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps",
        return_value=(["test_tool"], True, 2),  # tools_used, final_answer_called, steps_count
    )

    mocker.patch("smoltrace.core.initialize_agent", return_value=mock_agent)
    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})

    # Mock extract_traces to return trace data with matching test_id
    mock_traces = [
        {
            "trace_id": "trace123",
            "spans": [{"attributes": {"test.id": "test1"}}],
            "total_tokens": 100,
        }
    ]
    mocker.patch("smoltrace.core.extract_traces", return_value=mock_traces)
    mocker.patch("smoltrace.core.extract_metrics", return_value={"run_id": "test-run-id"})

    # Mock create_enhanced_trace_info
    mock_create_trace = mocker.patch(
        "smoltrace.core.create_enhanced_trace_info", return_value={"enhanced": "info"}
    )

    results, _, _, _, _ = run_evaluation(
        model_name="openai/gpt-3.5-turbo",
        provider="litellm",
        agent_types=["tool"],
        test_subset=None,
        dataset_name="test/dataset",
        split="train",
        verbose=False,
        debug=False,
        enable_otel=True,
    )

    # Verify create_enhanced_trace_info was called
    assert mock_create_trace.called
    # Verify results were enhanced
    assert "tool" in results
    assert len(results["tool"]) > 0


def test_extract_traces_with_token_aggregation(mocker):
    """Test extract_traces aggregates token counts correctly."""
    from smoltrace.core import extract_traces

    mock_exporter = Mock()
    mock_spans = [
        {
            "trace_id": "trace123",
            "name": "Span 1",
            "attributes": {"llm.token_count.total": 100, "gen_ai.usage.cost.total": "0.001"},
            "duration_ms": 1000,
        },
        {
            "trace_id": "trace123",
            "name": "Span 2",
            "attributes": {"llm.token_count.total": 50, "gen_ai.usage.cost.total": "0.0005"},
            "duration_ms": 500,
        },
    ]
    mock_exporter.get_finished_spans.return_value = mock_spans

    with patch("genai_otel.cost_calculator.CostCalculator"):
        traces = extract_traces(mock_exporter, "run-id")

    # Verify aggregation
    assert len(traces) == 1
    assert traces[0]["total_tokens"] == 150
    assert traces[0]["total_duration_ms"] == 1500
    assert traces[0]["total_cost_usd"] > 0


def test_extract_traces_with_no_cost_calculator(mocker, capsys):
    """Test extract_traces when CostCalculator import fails (line 703-705)."""
    from smoltrace.core import extract_traces

    mock_exporter = Mock()
    mock_span = {
        "trace_id": "trace123",
        "name": "LLM Call",
        "attributes": {
            "gen_ai.request.model": "gpt-3.5-turbo",
            "gen_ai.usage.prompt_tokens": 100,
        },
        "duration_ms": 1000,
    }
    mock_exporter.get_finished_spans.return_value = [mock_span]

    # Force ImportError for CostCalculator - correct import path
    with patch("genai_otel.cost_calculator.CostCalculator", side_effect=ImportError("No module")):
        traces = extract_traces(mock_exporter, "run-id")

    # Should still work
    assert len(traces) == 1

    # Check warning was printed
    captured = capsys.readouterr()
    assert "WARNING" in captured.out or "genai_otel not available" in captured.out


def test_run_evaluation_test_subset_filtering(mocker):
    """Test run_evaluation with test_subset parameter."""
    from smoltrace.core import run_evaluation

    mock_tests = [
        {"id": "easy1", "prompt": "Easy", "agent_types": ["tool"], "difficulty": "easy"},
        {"id": "hard1", "prompt": "Hard", "agent_types": ["tool"], "difficulty": "hard"},
    ]
    mocker.patch("smoltrace.core.load_test_cases_from_hf", return_value=mock_tests)

    mocker.patch(
        "smoltrace.core.setup_inmemory_otel",
        return_value=(None, None, None, None, None, "test-run-id"),
    )

    mock_agent = Mock()
    mock_agent.run.return_value = "Test"
    mocker.patch("smoltrace.core.initialize_agent", return_value=mock_agent)
    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})

    mocker.patch("smoltrace.core.extract_traces", return_value=[])
    mocker.patch("smoltrace.core.extract_metrics", return_value=[])

    # Test with difficulty subset
    results, _, _, _, _ = run_evaluation(
        model_name="openai/gpt-3.5-turbo",
        provider="litellm",
        agent_types=["tool"],
        test_subset="easy",  # Filter by difficulty
        dataset_name="test/dataset",
        split="train",
        verbose=False,
        debug=False,
        enable_otel=False,
    )

    assert "tool" in results


def test_extract_metrics_exception_handling(mocker, capsys):
    """Test extract_metrics handles exceptions gracefully."""
    from smoltrace.core import extract_metrics

    mock_metric_exporter = Mock()
    mock_trace_aggregator = Mock()

    # Make trace_aggregator raise exception
    mock_trace_aggregator.collect_all.side_effect = Exception("Test error")

    metrics = extract_metrics(
        metric_exporter=mock_metric_exporter,
        trace_aggregator=mock_trace_aggregator,
        trace_data=[],
        all_results={"tool": []},
        run_id="test-run",
    )

    # Should handle exception and continue - returns dict not list
    assert isinstance(metrics, dict)
    assert "run_id" in metrics
    assert metrics["run_id"] == "test-run"


def test_list_directory_tool_success(tmp_path):
    """Test ListDirectoryTool with actual directory."""
    from smoltrace.tools import ListDirectoryTool

    # Create test directory structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")
    (test_dir / "subdir").mkdir()

    tool = ListDirectoryTool(working_dir=str(tmp_path))
    result = tool.forward(str(test_dir))

    assert "file1.txt" in result
    assert "file2.txt" in result
    assert "subdir" in result


def test_file_search_tool_success(tmp_path):
    """Test FileSearchTool with actual files."""
    from smoltrace.tools import FileSearchTool

    # Create test files
    (tmp_path / "test1.txt").write_text("Hello world")
    (tmp_path / "test2.txt").write_text("Goodbye world")
    (tmp_path / "other.txt").write_text("No match here")

    tool = FileSearchTool(working_dir=str(tmp_path))
    # FileSearchTool signature: forward(directory, pattern, search_type, max_results)
    # Search by filename pattern
    result = tool.forward(str(tmp_path), "test*.txt", search_type="name")

    assert "test1.txt" in result and "test2.txt" in result


def test_grep_tool_success(tmp_path):
    """Test GrepTool with actual file."""
    from smoltrace.tools import GrepTool

    test_file = tmp_path / "grep_test.txt"
    test_file.write_text("Line 1: error occurred\nLine 2: all good\nLine 3: another error")

    tool = GrepTool(working_dir=str(tmp_path))
    # GrepTool signature: forward(file_path, pattern, ...)
    result = tool.forward(str(test_file), "error")

    assert "error occurred" in result or "another error" in result


def test_sed_tool_success(tmp_path):
    """Test SedTool with actual file."""
    from smoltrace.tools import SedTool

    test_file = tmp_path / "sed_test.txt"
    test_file.write_text("Hello world\nHello everyone")

    tool = SedTool(working_dir=str(tmp_path))
    result = tool.forward(str(test_file), "s/Hello/Hi/g")

    # SedTool returns the modified content, not modifying file in place
    assert "Hi" in result


def test_sort_tool_success(tmp_path):
    """Test SortTool with actual file."""
    from smoltrace.tools import SortTool

    test_file = tmp_path / "sort_test.txt"
    test_file.write_text("zebra\napple\nbanana")

    tool = SortTool(working_dir=str(tmp_path))
    result = tool.forward(str(test_file))

    # SortTool returns the sorted content with header line
    # Skip the first line which is "Sorted X lines:"
    lines = result.strip().split("\n")[1:]  # Skip header line
    assert lines == ["apple", "banana", "zebra"]


def test_head_tail_tool_success(tmp_path):
    """Test HeadTailTool with actual file."""
    from smoltrace.tools import HeadTailTool

    test_file = tmp_path / "head_test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

    tool = HeadTailTool(working_dir=str(tmp_path))

    # Test head - HeadTailTool signature: forward(file_path, mode='head', lines=10)
    result = tool.forward(str(test_file), mode="head", lines=3)
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result

    # Test tail
    result = tool.forward(str(test_file), mode="tail", lines=2)
    assert "Line 4" in result or "Line 5" in result
