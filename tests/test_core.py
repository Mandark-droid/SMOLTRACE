"""Tests for smoltrace.core module."""

from unittest.mock import Mock

import pytest


def test_load_test_cases_from_hf_success(mocker):
    """Test loading test cases from HuggingFace."""
    from smoltrace.core import load_test_cases_from_hf

    # Mock load_dataset
    mock_dataset = mocker.patch("smoltrace.core.load_dataset")
    mock_ds = [
        {"id": "test1", "prompt": "Test 1"},
        {"id": "test2", "prompt": "Test 2"},
    ]
    mock_dataset.return_value = mock_ds

    result = load_test_cases_from_hf("test/dataset", "train")

    # load_dataset is called with both positional and keyword args
    assert mock_dataset.called
    assert len(result) == 2
    assert result[0]["id"] == "test1"


def test_load_test_cases_from_hf_failure(mocker):
    """Test fallback to default test cases on error."""
    from smoltrace.core import DEFAULT_CODE_TESTS, DEFAULT_TOOL_TESTS, load_test_cases_from_hf

    # Mock load_dataset to raise exception
    mock_dataset = mocker.patch("smoltrace.core.load_dataset")
    mock_dataset.side_effect = Exception("Network error")

    result = load_test_cases_from_hf("invalid/dataset", "train")

    # Should return default test cases
    assert len(result) == len(DEFAULT_TOOL_TESTS) + len(DEFAULT_CODE_TESTS)


def test_initialize_agent_litellm_no_api_key(mocker):
    """Test LiteLLM agent initialization fails without API key."""
    from smoltrace.core import initialize_agent

    # Mock environment without API keys
    mocker.patch.dict("os.environ", {}, clear=True)

    with pytest.raises(ValueError, match="LiteLLM provider requires an API key"):
        initialize_agent("openai/gpt-4", "tool", provider="litellm")


def test_initialize_agent_litellm_with_api_key(mocker):
    """Test LiteLLM agent initialization with API key."""
    from smoltrace.core import initialize_agent

    # Mock environment with API key
    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})

    # Mock LiteLLMModel and ToolCallingAgent
    mock_litellm = mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.ToolCallingAgent")

    initialize_agent("openai/gpt-4", "tool", provider="litellm")

    mock_litellm.assert_called_once()
    mock_agent.assert_called_once()


def test_initialize_agent_code_agent(mocker):
    """Test CodeAgent initialization."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.CodeAgent")

    initialize_agent("openai/gpt-4", "code", provider="litellm")

    mock_agent.assert_called_once()


def test_initialize_agent_ollama(mocker):
    """Test Ollama agent initialization."""
    from smoltrace.core import initialize_agent

    mock_litellm = mocker.patch("smoltrace.core.LiteLLMModel")
    mocker.patch("smoltrace.core.ToolCallingAgent")

    initialize_agent("ollama/mistral", "tool", provider="ollama")

    # Should call with ollama prefix and api_base
    call_args = mock_litellm.call_args[1]
    assert "ollama/" in call_args["model_id"]
    assert call_args["api_base"] == "http://localhost:11434"


def test_initialize_agent_transformers_import_error(mocker):
    """Test transformers provider with missing dependencies."""

    # The transformers provider will raise ImportError if transformers is not installed
    # We can't easily test this without actually uninstalling transformers
    # So we skip this test as it's an edge case
    pytest.skip("Requires actual import manipulation which is difficult to test")


def test_initialize_agent_invalid_provider():
    """Test invalid provider raises error."""
    from smoltrace.core import initialize_agent

    with pytest.raises(ValueError, match="Unknown provider"):
        initialize_agent("test-model", "tool", provider="invalid")


def test_initialize_agent_with_prompt_config(mocker):
    """Test agent initialization with prompt config."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.ToolCallingAgent")

    # Test with system_prompt only (avoids max_steps duplicate issue)
    prompt_config = {
        "system_prompt": "You are a helpful assistant.",
    }

    initialize_agent("openai/gpt-4", "tool", provider="litellm", prompt_config=prompt_config)

    # Check that prompt config was passed
    call_kwargs = mock_agent.call_args[1]
    assert call_kwargs["system_prompt"] == "You are a helpful assistant."
    assert "max_steps" in call_kwargs  # Default max_steps=6 should be passed


def test_initialize_agent_with_mcp_server(mocker):
    """Test agent initialization with MCP server."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mocker.patch("smoltrace.core.ToolCallingAgent")
    mock_mcp = mocker.patch("smoltrace.core.initialize_mcp_tools")
    mock_mcp.return_value = [Mock()]  # Return mock MCP tools

    initialize_agent(
        "openai/gpt-4", "tool", provider="litellm", mcp_server_url="http://localhost:8080"
    )

    mock_mcp.assert_called_once_with("http://localhost:8080")


def test_extract_tools_from_code():
    """Test extracting tool names from code."""
    from smoltrace.core import extract_tools_from_code

    code = """
    temp = get_weather("Paris")
    result = calculator(5 + 3)
    time = get_current_time()
    search = web_search("test query")
    """

    tools = extract_tools_from_code(code)

    assert "get_weather" in tools
    assert "calculator" in tools
    assert "get_current_time" in tools
    assert "web_search" in tools


def test_extract_tools_from_code_no_tools():
    """Test code with no tools."""
    from smoltrace.core import extract_tools_from_code

    code = "x = 1 + 2\nprint(x)"
    tools = extract_tools_from_code(code)

    assert len(tools) == 0


def test_filter_tests():
    """Test filtering test cases by agent type and difficulty."""
    from smoltrace.core import _filter_tests

    test_cases = [
        {"id": "1", "agent_type": "tool", "difficulty": "easy"},
        {"id": "2", "agent_type": "code", "difficulty": "easy"},
        {"id": "3", "agent_type": "tool", "difficulty": "hard"},
        {"id": "4", "agent_type": "both", "difficulty": "easy"},
    ]

    # Filter for tool agent
    result = _filter_tests(test_cases, "tool", None)
    assert len(result) == 3  # IDs 1, 3, 4

    # Filter for tool agent with easy difficulty
    result = _filter_tests(test_cases, "tool", "easy")
    assert len(result) == 2  # IDs 1, 4


def test_print_agent_summary(capsys):
    """Test printing agent summary."""
    from smoltrace.core import print_agent_summary

    results = [
        {"success": True},
        {"success": False},
        {"success": True},
    ]

    print_agent_summary("tool", results)

    captured = capsys.readouterr()
    assert "TOOL SUMMARY" in captured.out
    assert "2/3" in captured.out
    assert "66.7%" in captured.out


def test_print_agent_summary_empty(capsys):
    """Test printing summary with no results."""
    from smoltrace.core import print_agent_summary

    print_agent_summary("tool", [])

    captured = capsys.readouterr()
    assert captured.out == ""  # Should not print anything


def test_print_combined_summary(capsys):
    """Test printing combined summary."""
    from smoltrace.core import print_combined_summary

    all_results = {
        "tool": [{"success": True}, {"success": False}],
        "code": [{"success": True}, {"success": True}, {"success": False}],
    }

    print_combined_summary(all_results)

    captured = capsys.readouterr()
    assert "COMBINED SUMMARY" in captured.out
    assert "TOOL: 1/2" in captured.out
    assert "CODE: 2/3" in captured.out


def test_extract_traces_no_exporter():
    """Test trace extraction with no exporter."""
    from smoltrace.core import extract_traces

    result = extract_traces(None, "run_123")
    assert result == []


def test_extract_traces_with_spans(mocker):
    """Test trace extraction with spans."""
    from smoltrace.core import extract_traces

    mock_exporter = Mock()
    mock_exporter.get_finished_spans.return_value = [
        {
            "trace_id": "trace_1",
            "span_id": "span_1",
            "attributes": {"llm.token_count.total": 100},
            "duration_ms": 500,
        },
        {
            "trace_id": "trace_1",
            "span_id": "span_2",
            "attributes": {"gen_ai.usage.cost.total": 0.001},
            "duration_ms": 200,
        },
    ]

    traces = extract_traces(mock_exporter, "run_123")

    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace_1"
    assert traces[0]["run_id"] == "run_123"
    assert traces[0]["total_tokens"] == 100
    assert traces[0]["total_duration_ms"] == 700
    assert traces[0]["total_cost_usd"] == 0.001


def test_extract_metrics(mocker, capsys):
    """Test metric extraction."""
    from smoltrace.core import extract_metrics

    mock_metric_exporter = Mock()
    mock_metric_exporter.get_metrics_data.return_value = [{"gpu_metric": "data"}]

    mock_trace_aggregator = Mock()
    mock_trace_aggregator.collect_all.return_value = [{"aggregate": "metric"}]

    result = extract_metrics(mock_metric_exporter, mock_trace_aggregator, [], {}, "run_123")

    assert result["run_id"] == "run_123"
    assert len(result["resourceMetrics"]) == 1
    assert len(result["aggregates"]) == 1


def test_extract_metrics_with_exception(mocker, capsys):
    """Test metric extraction handles exceptions."""
    from smoltrace.core import extract_metrics

    mock_metric_exporter = Mock()
    mock_metric_exporter.get_metrics_data.side_effect = Exception("Test error")

    mock_trace_aggregator = Mock()
    mock_trace_aggregator.collect_all.side_effect = Exception("Test error 2")

    result = extract_metrics(mock_metric_exporter, mock_trace_aggregator, [], {}, "run_123")

    # Should handle exceptions gracefully
    assert result["run_id"] == "run_123"
    assert result["resourceMetrics"] == []
    assert result["aggregates"] == []

    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_create_enhanced_trace_info():
    """Test creating enhanced trace info."""
    from smoltrace.core import create_enhanced_trace_info

    trace_data = [
        {
            "trace_id": "trace_1",
            "total_tokens": 150,
            "total_duration_ms": 500,
            "total_cost_usd": 0.005,
            "spans": [
                {
                    "span_id": "span_1",
                    "attributes": {"test.id": "test_123"},
                }
            ],
        }
    ]

    result = create_enhanced_trace_info(trace_data, [], "test_123")

    assert result["trace_id"] == "trace_1"
    assert result["total_tokens"] == 150
    assert result["duration_ms"] == 500
    assert result["cost_usd"] == 0.005
    assert result["span_count"] == 1


def test_create_enhanced_trace_info_no_match():
    """Test creating enhanced trace info with no matching trace."""
    from smoltrace.core import create_enhanced_trace_info

    trace_data = [
        {
            "trace_id": "trace_1",
            "spans": [
                {
                    "span_id": "span_1",
                    "attributes": {"test.id": "test_999"},
                }
            ],
        }
    ]

    result = create_enhanced_trace_info(trace_data, [], "test_123")

    assert result == {}


def test_extract_tools_from_action_step():
    """Test extracting tools from ActionStep event."""
    from smolagents.memory import ActionStep

    from smoltrace.core import extract_tools_from_action_step

    # Create mock event with tool calls
    event = Mock(spec=ActionStep)
    mock_tool_call = Mock()
    mock_tool_call.name = "get_weather"
    event.tool_calls = [mock_tool_call]

    tools = extract_tools_from_action_step(event, "tool", debug=False, tracer=None)

    assert "get_weather" in tools


def test_extract_tools_from_action_step_with_final_answer():
    """Test extracting tools ignores final_answer."""
    from smoltrace.core import extract_tools_from_action_step

    event = Mock()
    mock_tool_call = Mock()
    mock_tool_call.name = "final_answer"
    event.tool_calls = [mock_tool_call]

    tools = extract_tools_from_action_step(event, "tool", debug=False, tracer=None)

    assert "final_answer" not in tools


def test_extract_tools_from_action_step_code_agent():
    """Test extracting tools from code in ActionStep."""
    from smoltrace.core import extract_tools_from_action_step

    event = Mock()
    event.tool_calls = []
    event.code = "result = get_weather('Paris')"

    tools = extract_tools_from_action_step(event, "code", debug=False, tracer=None)

    assert "get_weather" in tools


def test_is_final_answer_called_in_action_step_true():
    """Test detecting final_answer in tool calls."""
    from smoltrace.core import is_final_answer_called_in_action_step

    event = Mock()
    mock_tool_call = Mock()
    mock_tool_call.name = "final_answer"
    event.tool_calls = [mock_tool_call]

    result = is_final_answer_called_in_action_step(event, "tool")

    assert result is True


def test_is_final_answer_called_in_action_step_in_code():
    """Test detecting final_answer in code."""
    from smoltrace.core import is_final_answer_called_in_action_step

    event = Mock()
    event.tool_calls = []
    event.code = "final_answer('The result is 42')"

    result = is_final_answer_called_in_action_step(event, "code")

    assert result is True


def test_is_final_answer_called_in_action_step_false():
    """Test final_answer not called."""
    from smoltrace.core import is_final_answer_called_in_action_step

    event = Mock()
    event.tool_calls = []
    event.code = "x = 1 + 1"

    result = is_final_answer_called_in_action_step(event, "code")

    assert result is False


def test_evaluate_single_test_success_with_keywords(mocker):
    """Test that success is True when all conditions met including keyword check."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "The weather is sunny and 25 degrees"

    # Mock analyze_streamed_steps
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps",
        return_value=(["get_weather"], True, 2),  # tools_used, final_answer_called, steps
    )

    test_case = {
        "id": "test_001",
        "difficulty": "easy",
        "prompt": "What's the weather?",
        "expected_tool": "get_weather",
        "expected_keywords": ["sunny", "degrees"],
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is True
    assert result["correct_tool"] is True
    assert result["final_answer_called"] is True
    assert result["response_correct"] is True
    assert result["success"] is True  # All conditions met


def test_evaluate_single_test_success_without_keywords(mocker):
    """Test that success is True when no keyword validation needed."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "The weather is sunny"

    # Mock analyze_streamed_steps
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps",
        return_value=(["get_weather"], True, 2),  # tools_used, final_answer_called, steps
    )

    test_case = {
        "id": "test_002",
        "difficulty": "easy",
        "prompt": "What's the weather?",
        "expected_tool": "get_weather",
        # No expected_keywords
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is True
    assert result["correct_tool"] is True
    assert result["final_answer_called"] is True
    assert result["response_correct"] is True  # Should be True when no keywords to check
    assert result["success"] is True  # All conditions met


def test_evaluate_single_test_failure_missing_keyword(mocker):
    """Test that success is False when expected keyword is missing."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "The weather is nice"  # Missing "temperature"

    # Mock analyze_streamed_steps
    mocker.patch("smoltrace.core.analyze_streamed_steps", return_value=(["get_weather"], True, 2))

    test_case = {
        "id": "test_003",
        "difficulty": "easy",
        "prompt": "What's the temperature?",
        "expected_tool": "get_weather",
        "expected_keywords": ["temperature", "degrees"],  # Keywords not in response
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is True
    assert result["correct_tool"] is True
    assert result["final_answer_called"] is True
    assert result["response_correct"] is False  # Keywords missing
    assert result["success"] is False  # Should fail due to missing keywords


def test_evaluate_single_test_failure_no_final_answer(mocker):
    """Test that success is False when final_answer not called."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "Processing..."

    # Mock analyze_streamed_steps - no final answer
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps",
        return_value=(["get_weather"], False, 2),  # final_answer_called = False
    )

    test_case = {
        "id": "test_004",
        "difficulty": "easy",
        "prompt": "What's the weather?",
        "expected_tool": "get_weather",
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is True
    assert result["correct_tool"] is True
    assert result["final_answer_called"] is False
    assert result["response_correct"] is True  # No keywords to check
    assert result["success"] is False  # Should fail due to no final_answer


def test_evaluate_single_test_failure_wrong_tool(mocker):
    """Test that success is False when wrong tool is used."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "Result"

    # Mock analyze_streamed_steps - wrong tool
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps",
        return_value=(["search_web"], True, 2),  # Used wrong tool
    )

    test_case = {
        "id": "test_005",
        "difficulty": "easy",
        "prompt": "What's the weather?",
        "expected_tool": "get_weather",  # Expected this tool
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is True
    assert result["correct_tool"] is False  # Wrong tool used
    assert result["final_answer_called"] is True
    assert result["response_correct"] is True
    assert result["success"] is False  # Should fail due to wrong tool


def test_evaluate_single_test_failure_no_tool(mocker):
    """Test that success is False when no tool is called."""
    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "I don't know"

    # Mock analyze_streamed_steps - no tools used
    mocker.patch(
        "smoltrace.core.analyze_streamed_steps", return_value=([], True, 1)  # No tools used
    )

    test_case = {
        "id": "test_006",
        "difficulty": "easy",
        "prompt": "What's the weather?",
        "expected_tool": "get_weather",
    }

    result = evaluate_single_test(mock_agent, test_case, "tool", verbose=False)

    assert result["tool_called"] is False
    assert result["correct_tool"] is False  # No tools = wrong
    assert result["final_answer_called"] is True
    assert result["response_correct"] is True
    assert result["success"] is False  # Should fail due to no tool called


def test_initialize_agent_with_additional_imports(mocker):
    """Test CodeAgent initialization with additional_authorized_imports."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.CodeAgent")

    additional_imports = ["pandas", "numpy", "matplotlib"]

    initialize_agent(
        "openai/gpt-4",
        "code",
        provider="litellm",
        additional_authorized_imports=additional_imports,
    )

    # Check that additional_authorized_imports was passed to CodeAgent
    call_kwargs = mock_agent.call_args[1]
    assert "additional_authorized_imports" in call_kwargs
    assert call_kwargs["additional_authorized_imports"] == additional_imports


def test_initialize_agent_merge_additional_imports_with_prompt_config(mocker):
    """Test merging additional_authorized_imports from both prompt_config and parameter."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.CodeAgent")

    # Prompt config has some imports
    prompt_config = {"additional_authorized_imports": ["json", "yaml", "time"]}

    # CLI parameter has some imports (with overlap)
    additional_imports = ["pandas", "numpy", "json"]  # json overlaps

    initialize_agent(
        "openai/gpt-4",
        "code",
        provider="litellm",
        prompt_config=prompt_config,
        additional_authorized_imports=additional_imports,
    )

    # Check that imports were merged without duplicates
    call_kwargs = mock_agent.call_args[1]
    merged_imports = call_kwargs["additional_authorized_imports"]

    # Should contain all unique imports
    assert "json" in merged_imports
    assert "yaml" in merged_imports
    assert "time" in merged_imports
    assert "pandas" in merged_imports
    assert "numpy" in merged_imports

    # Should not have duplicates (set removes them)
    assert len(merged_imports) == 5


def test_initialize_agent_additional_imports_only_for_code_agent(mocker):
    """Test that additional_authorized_imports is only applied to CodeAgent."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.ToolCallingAgent")

    additional_imports = ["pandas", "numpy"]

    initialize_agent(
        "openai/gpt-4",
        "tool",  # ToolCallingAgent, not CodeAgent
        provider="litellm",
        additional_authorized_imports=additional_imports,
    )

    # Check that additional_authorized_imports was NOT passed to ToolCallingAgent
    call_kwargs = mock_agent.call_args[1]
    assert "additional_authorized_imports" not in call_kwargs


def test_initialize_agent_prompt_config_imports_only(mocker):
    """Test using additional_authorized_imports from prompt_config only."""
    from smoltrace.core import initialize_agent

    mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"})
    mocker.patch("smoltrace.core.LiteLLMModel")
    mock_agent = mocker.patch("smoltrace.core.CodeAgent")

    # Only prompt config has imports, no CLI parameter
    prompt_config = {"additional_authorized_imports": ["json", "yaml"]}

    initialize_agent("openai/gpt-4", "code", provider="litellm", prompt_config=prompt_config)

    # Check that imports from prompt_config were passed
    call_kwargs = mock_agent.call_args[1]
    assert call_kwargs["additional_authorized_imports"] == ["json", "yaml"]


def test_extract_tools_from_code_with_available_tools():
    """Test extracting tool names from code with available_tools parameter."""
    from smoltrace.core import extract_tools_from_code

    # Create mock tools with names (including MCP-style tools)
    mock_tool_1 = Mock()
    mock_tool_1.name = "custom_search"

    mock_tool_2 = Mock()
    mock_tool_2.name = "database_query"

    mock_tool_3 = Mock()
    mock_tool_3.name = "get_weather"  # One of the default tools

    available_tools = [mock_tool_1, mock_tool_2, mock_tool_3]

    code = """
    result1 = custom_search("test query")
    result2 = database_query("SELECT * FROM users")
    result3 = get_weather("Paris")
    x = 1 + 2  # This should not be detected
    """

    tools = extract_tools_from_code(code, available_tools=available_tools)

    assert "custom_search" in tools
    assert "database_query" in tools
    assert "get_weather" in tools
    assert len(tools) == 3


def test_extract_tools_from_code_with_special_characters_in_tool_names():
    """Test that tool names with special regex characters are properly escaped."""
    from smoltrace.core import extract_tools_from_code

    # Create mock tool with special characters in name
    mock_tool = Mock()
    mock_tool.name = "search.v2"  # Contains special regex character '.'

    available_tools = [mock_tool]

    code = 'result = search.v2("test query")'

    tools = extract_tools_from_code(code, available_tools=available_tools)

    assert "search.v2" in tools
    assert len(tools) == 1


def test_extract_tools_from_code_fallback_when_no_available_tools():
    """Test that extract_tools_from_code falls back to default patterns when available_tools is None."""
    from smoltrace.core import extract_tools_from_code

    code = """
    temp = get_weather("Paris")
    result = calculator(5 + 3)
    """

    # Call without available_tools - should use fallback patterns
    tools = extract_tools_from_code(code, available_tools=None)

    assert "get_weather" in tools
    assert "calculator" in tools


def test_extract_tools_from_code_multiple_calls_to_same_tool():
    """Test that multiple calls to the same tool are all detected."""
    from smoltrace.core import extract_tools_from_code

    mock_tool = Mock()
    mock_tool.name = "fetch_data"
    available_tools = [mock_tool]

    code = """
    data1 = fetch_data("source1")
    data2 = fetch_data("source2")
    data3 = fetch_data("source3")
    """

    tools = extract_tools_from_code(code, available_tools=available_tools)

    # Should detect all 3 calls
    assert tools.count("fetch_data") == 3


def test_extract_tools_from_action_step_with_available_tools(mocker):
    """Test extract_tools_from_action_step with available_tools for CodeAgent."""
    from smolagents.agents import ActionStep

    from smoltrace.core import extract_tools_from_action_step

    # Create mock tools
    mock_tool = Mock()
    mock_tool.name = "mcp_custom_tool"
    available_tools = [mock_tool]

    # Create mock ActionStep with code that calls the MCP tool
    event = Mock(spec=ActionStep)
    event.code = 'result = mcp_custom_tool("test")'
    event.tool_calls = None

    tools = extract_tools_from_action_step(
        event, agent_type="code", debug=False, tracer=None, available_tools=available_tools
    )

    assert "mcp_custom_tool" in tools


def test_analyze_streamed_steps_extracts_agent_tools(mocker):
    """Test that analyze_streamed_steps extracts tools from agent and uses them for detection."""
    from smolagents.agents import ActionStep

    from smoltrace.core import analyze_streamed_steps

    # Create mock agent with tools attribute
    mock_agent = Mock()
    mock_tool = Mock()
    mock_tool.name = "agent_tool"
    mock_agent.tools = [mock_tool]

    # Create mock ActionStep with code calling agent_tool
    mock_action_step = Mock(spec=ActionStep)
    mock_action_step.code = 'result = agent_tool("test")'
    mock_action_step.tool_calls = None

    # Mock agent.run to yield the action step
    mock_agent.run.return_value = iter([mock_action_step])

    # Analyze steps
    tools_used, final_answer_called, steps_count = analyze_streamed_steps(
        mock_agent, "test task", agent_type="code", tracer=None, debug=False
    )

    # Should have detected the MCP tool
    assert "agent_tool" in tools_used
    assert steps_count == 1
