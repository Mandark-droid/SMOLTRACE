# smoltrace/core.py
"""Core evaluation logic for smoltrace."""

import os
import re
from typing import Dict, List, Optional

from datasets import load_dataset
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent
from smolagents.memory import ActionStep, FinalAnswerStep, PlanningStep

from .otel import create_enhanced_trace_info, extract_metrics, extract_traces, setup_inmemory_otel
from .tools import CalculatorTool, DuckDuckGoSearchTool, TimeTool, WeatherTool, initialize_mcp_tools

# --- Default Test Cases ---
DEFAULT_TOOL_TESTS = [
    {
        "id": "tool_weather_single",
        "prompt": "What's the weather in Paris, France?",
        "expected_tool": "get_weather",
        "expected_tool_calls": 1,
        "difficulty": "easy",
        "agent_type": "tool",
    },
    {
        "id": "tool_weather_compare",
        "prompt": "Compare the weather in Paris, France and London, UK. Which one is warmer?",
        "expected_tool": "get_weather",
        "expected_tool_calls": 2,
        "difficulty": "medium",
        "agent_type": "tool",
    },
]
DEFAULT_CODE_TESTS = [
    {
        "id": "code_calculator_single",
        "prompt": "What is 234 multiplied by 67?",
        "expected_tool": "calculator",
        "expected_tool_calls": 1,
        "difficulty": "easy",
        "agent_type": "code",
    },
]


def load_test_cases_from_hf(
    dataset_name: str = "kshitijthakkar/smoalagent-tasks", split: str = "train"
) -> List[Dict]:
    """Loads test cases from a Hugging Face dataset or uses default test cases if loading fails."""
    try:
        ds = load_dataset(dataset_name, split=split)
        return [dict(row) for row in ds]
    except Exception as e:
        print(f"Error loading dataset: {e}. Using defaults.")
        return DEFAULT_TOOL_TESTS + DEFAULT_CODE_TESTS


def initialize_agent(
    model_name: str,
    agent_type: str,
    prompt_config: Optional[Dict] = None,
    mcp_server_url: Optional[str] = None,
):
    """Initializes and returns an agent (ToolCallingAgent or CodeAgent) with specified configurations."""
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key or api_key == "dummy":
        print("Warning: No valid API key; using local fallback")
        model = LiteLLMModel(model_id="ollama/mistral", api_base="http://localhost:11434")
    else:
        model = LiteLLMModel(model_id=model_name, api_key=api_key)

    tools = [WeatherTool(), CalculatorTool(), TimeTool(), DuckDuckGoSearchTool()]

    if mcp_server_url:
        mcp_tools = initialize_mcp_tools(mcp_server_url)
        tools.extend(mcp_tools)

    kwargs = {}
    if prompt_config:
        if "system_prompt" in prompt_config:
            kwargs["system_prompt"] = prompt_config["system_prompt"]
        if "max_steps" in prompt_config:
            kwargs["max_steps"] = prompt_config["max_steps"]

    if agent_type == "tool":
        return ToolCallingAgent(
            tools=tools, model=model, max_steps=kwargs.get("max_steps", 6), **kwargs
        )
    return CodeAgent(
        tools=tools,
        model=model,
        executor_type="local",
        max_steps=kwargs.get("max_steps", 6),
        **kwargs,
    )


def extract_tools_from_code(code: str) -> list:
    """Extracts tool names from a given code string."""
    tools_found = []
    tool_patterns = [
        r"get_weather\s*\(",
        r"calculator\s*\(",
        r"get_current_time\s*\(",
        r"web_search\s*\(",
    ]
    for pattern in tool_patterns:
        matches = re.findall(pattern, code)
        for _ in matches:
            tool_name = pattern.split(r"\s*\(", maxsplit=1)[0]
            tools_found.append(tool_name)
    return tools_found


def analyze_streamed_steps(
    agent, task: str, agent_type: str, tracer=None, debug: bool = False
) -> tuple[list, bool, int]:
    """Analyzes the streamed steps of an agent's run to extract tool usage, final answer calls, and step count."""

    tools_used = []

    final_answer_called = False

    steps_count = 0

    for event in agent.run(task, stream=True, max_steps=20, reset=True):

        if debug:

            print(f"[DEBUG] Event type: {type(event).__name__}")

        if tracer:

            current_span = tracer.trace.get_current_span()

            current_span.add_event(
                "step",
                attributes={"step_index": steps_count, "type": type(event).__name__},
            )

        if isinstance(event, ActionStep):

            steps_count += 1

            tools_used.extend(extract_tools_from_action_step(event, agent_type, debug, tracer))

            if is_final_answer_called_in_action_step(event, agent_type):

                final_answer_called = True

        elif isinstance(event, FinalAnswerStep):

            final_answer_called = True

            steps_count += 1

        elif isinstance(event, PlanningStep):

            steps_count += 1

    return tools_used, final_answer_called, steps_count


def extract_tools_from_action_step(event: ActionStep, agent_type: str, debug: bool, tracer) -> list:
    """Extracts tools used from an ActionStep event."""

    tools = []

    if hasattr(event, "tool_calls") and event.tool_calls:

        for tool_call in event.tool_calls:

            if hasattr(tool_call, "name"):

                tool_name = tool_call.name

                if debug:

                    print(f"[DEBUG] Tool call: {tool_name}")

                if tracer:

                    current_span = tracer.trace.get_current_span()

                    current_span.add_event("tool_call", attributes={"name": tool_name})

                if tool_name != "final_answer":

                    tools.append(tool_name)

    if agent_type == "code" and hasattr(event, "code") and event.code:

        code_tools = extract_tools_from_code(event.code)

        tools.extend(code_tools)

    return tools


def is_final_answer_called_in_action_step(event: ActionStep, agent_type: str) -> bool:
    """Checks if the final_answer tool was called within an ActionStep event."""

    if hasattr(event, "tool_calls") and event.tool_calls:

        for tool_call in event.tool_calls:

            if hasattr(tool_call, "name") and tool_call.name == "final_answer":

                return True

    if agent_type == "code" and hasattr(event, "code") and event.code:

        if re.search(r"\bfinal_answer\s*\(", event.code):

            return True

    return False


def evaluate_single_test(
    agent,
    test_case: dict,
    agent_type: str,
    tracer=None,
    meter=None,
    verbose: bool = True,
    debug: bool = False,
):
    """Evaluates a single test case against an agent, collecting results and trace information."""
    if verbose:
        print(f"\n{'=' * 80}")
        print(f"Test: {test_case['id']} ({test_case['difficulty']}) [{agent_type.upper()}]")
        print(f"Prompt: {test_case['prompt']}")
        print(f"{'=' * 80}")
    result = {
        "test_id": test_case["id"],
        "agent_type": agent_type,
        "difficulty": test_case["difficulty"],
        "prompt": test_case["prompt"],
        "success": False,
        "tool_called": False,
        "correct_tool": False,
        "final_answer_called": False,
        "response_correct": None,
        "error": None,
        "response": None,
        "tools_used": [],
        "steps": 0,
        "enhanced_trace_info": None,
    }
    try:
        span_attributes = {
            "test.id": test_case["id"],
            "test.difficulty": test_case["difficulty"],
            "agent.type": agent_type,
            "prompt": test_case["prompt"][:100],
        }
        if tracer:
            with tracer.start_as_current_span(
                "test_evaluation", attributes=span_attributes
            ) as span:
                tools_used, final_answer_called, steps_count = analyze_streamed_steps(
                    agent, test_case["prompt"], agent_type, tracer=tracer, debug=debug
                )
                response = agent.run(test_case["prompt"], reset=True)
                span.set_attribute("tests.tool_calls", len(tools_used))
                span.set_attribute("tests.steps", steps_count)
        else:
            tools_used, final_answer_called, steps_count = analyze_streamed_steps(
                agent, test_case["prompt"], agent_type, debug=debug
            )
            response = agent.run(test_case["prompt"], reset=True)
        result["response"] = str(response)
        result["tools_used"] = tools_used
        result["tool_called"] = len(tools_used) > 0
        result["final_answer_called"] = final_answer_called
        result["steps"] = steps_count
        expected_tool = test_case.get("expected_tool")
        expected_calls = test_case.get("expected_tool_calls")
        if expected_tool == "multiple":
            result["correct_tool"] = len(result["tools_used"]) >= (expected_calls or 1)
        elif expected_tool:
            count = result["tools_used"].count(expected_tool)
            result["correct_tool"] = count >= expected_calls if expected_calls else count > 0
        else:
            result["correct_tool"] = result["tool_called"]
        expected_keywords = test_case.get("expected_keywords", [])
        if expected_keywords:
            response_lower = result["response"].lower()
            result["response_correct"] = any(
                kw.lower() in response_lower for kw in expected_keywords
            )
        result["success"] = (
            result["tool_called"]
            and result.get("correct_tool", True)
            and result["final_answer_called"]
            and result.get("response_correct", True)
        )
        if verbose:
            print(f"✅ Response: {response}")
            print(f"Tools used: {result['tools_used']}")
            print(f"Success: {result['success']}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Broad exception is caught here to ensure all test cases are evaluated
        # even if an unexpected error occurs during a single test run.
        result["error"] = str(e)
        if verbose:
            print(f"❌ Error: {e}")
    return result


def run_evaluation(
    model_name: str,
    agent_types: List[str],
    test_subset: Optional[str],
    dataset_name: str,
    split: str,
    enable_otel: bool,
    verbose: bool,
    debug: bool,
    prompt_config: Optional[Dict] = None,
    mcp_server_url: Optional[str] = None,
):
    """Runs the evaluation for specified agent types and test subsets, collecting traces and metrics."""

    test_cases = load_test_cases_from_hf(dataset_name, split)

    tracer, _, span_exporter, metric_collector = setup_inmemory_otel(enable_otel)

    all_results = {"tool": [], "code": []}

    for agent_type in agent_types:

        all_results[agent_type] = _run_agent_tests(
            agent_type,
            model_name,
            prompt_config,
            mcp_server_url,
            test_cases,
            test_subset,
            tracer,
            verbose,
            debug,
        )

    if verbose:

        print_combined_summary(all_results)

    # Extract traces and metrics

    trace_data = extract_traces(span_exporter) if span_exporter else []

    metric_data = extract_metrics(metric_collector, trace_data, all_results)

    # Enhance results with trace info

    for agent_type, results in all_results.items():

        for result in results:

            if enable_otel:

                result["enhanced_trace_info"] = create_enhanced_trace_info(
                    trace_data, metric_data, result["test_id"]
                )

    return all_results, trace_data, metric_data, dataset_name


def _run_agent_tests(
    agent_type: str,
    model_name: str,
    prompt_config: Optional[Dict],
    mcp_server_url: Optional[str],
    test_cases: List[Dict],
    test_subset: Optional[str],
    tracer,
    verbose: bool,
    debug: bool,
) -> List[Dict]:
    """Helper function to run tests for a single agent type and return results."""

    agent = initialize_agent(model_name, agent_type, prompt_config, mcp_server_url)

    valid_tests = _filter_tests(test_cases, agent_type, test_subset)

    results = []

    for tc in valid_tests:

        result = evaluate_single_test(agent, tc.copy(), agent_type, tracer, None, verbose, debug)

        results.append(result)

    if verbose:

        print_agent_summary(agent_type, results)

    return results


def _filter_tests(
    test_cases: List[Dict],
    agent_type: str,
    test_subset: Optional[str],
) -> List[Dict]:

    filtered_tests = [tc for tc in test_cases if tc.get("agent_type") in [agent_type, "both"]]

    if test_subset:

        filtered_tests = [tc for tc in filtered_tests if tc["difficulty"] == test_subset]

    return filtered_tests


def print_agent_summary(agent_type: str, results: list):
    """Prints a summary of the evaluation results for a specific agent type."""
    total = len(results)
    if total == 0:
        return
    successful = sum(1 for r in results if r["success"])
    print(f"\n--- {agent_type.upper()} SUMMARY ---")
    print(f"Total: {total}, Success: {successful}/{total} ({successful / total * 100:.1f}%)")


def print_combined_summary(all_results: dict):
    """Prints a combined summary of evaluation results across all agent types."""
    print("\n" + "=" * 50)
    print("COMBINED SUMMARY")
    print("=" * 50)
    for agent_type, results in all_results.items():
        if results:
            total = len(results)
            successful = sum(1 for r in results if r["success"])
            print(f"{agent_type.upper()}: {successful}/{total} ({successful / total * 100:.1f}%)")
