# smoltrace/core.py
"""Core evaluation logic for smoltrace."""

import os
import re
import warnings
from typing import Dict, List, Optional

from datasets import load_dataset
from opentelemetry import trace
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent
from smolagents.memory import ActionStep, FinalAnswerStep, PlanningStep

from .otel import setup_inmemory_otel
from .tools import get_all_tools, initialize_mcp_tools

# Suppress common transformers warnings that don't affect functionality
# This specifically handles the attention_mask warning for models where pad_token == eos_token
warnings.filterwarnings(
    "ignore", message=".*attention mask is not set.*", category=UserWarning, module="transformers.*"
)

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
    dataset_name: str = "kshitijthakkar/smoltrace-tasks", split: str = "train"
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
    provider: str = "litellm",
    prompt_config: Optional[Dict] = None,
    mcp_server_url: Optional[str] = None,
    additional_authorized_imports: Optional[List[str]] = None,
    search_provider: str = "duckduckgo",
    hf_inference_provider: Optional[str] = None,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_directory: Optional[str] = None,
):
    """Initializes and returns an agent (ToolCallingAgent or CodeAgent) with specified configurations.

    Args:
        model_name: Model identifier (e.g., "mistral/mistral-small-latest")
        agent_type: "tool" or "code"
        provider: "litellm", "transformers", "ollama", or "inference"
        prompt_config: Optional prompt configuration
        mcp_server_url: Optional MCP server URL
        additional_authorized_imports: Additional Python modules authorized for CodeAgent imports
        search_provider: Search provider for GoogleSearchTool ("serper", "brave", "duckduckgo")
        hf_inference_provider: HuggingFace inference provider (for "inference" provider)
        enabled_smolagents_tools: List of smolagents tool names to enable
    """

    if provider == "litellm":
        # LiteLLM provider for API models (OpenAI, Anthropic, Mistral, etc.)
        api_key = (
            os.getenv("LITELLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("MISTRAL_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("TOGETHER_API_KEY")
        )

        if not api_key or api_key == "dummy":
            raise ValueError(
                "LiteLLM provider requires an API key. Please set one of: "
                "LITELLM_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, MISTRAL_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY"
            )

        print(f"[PROVIDER] Using LiteLLM with model: {model_name}")
        model = LiteLLMModel(model_id=model_name)

    elif provider == "inference":
        # InferenceClientModel for HuggingFace Inference API
        try:
            from smolagents import InferenceClientModel

            print(f"[PROVIDER] Using InferenceClientModel with model: {model_name}")

            # Build kwargs for InferenceClientModel
            inference_kwargs = {"model_id": model_name}
            if hf_inference_provider:
                inference_kwargs["provider"] = hf_inference_provider
                print(f"[PROVIDER] Using HF inference provider: {hf_inference_provider}")

            model = InferenceClientModel(**inference_kwargs)

        except ImportError:
            raise ImportError(
                "InferenceClientModel requires 'huggingface_hub'. "
                "Install with: pip install huggingface_hub"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model with InferenceClientModel: {e}")

    elif provider == "transformers":
        # Transformers provider for HuggingFace GPU models
        try:
            from smolagents import TransformersModel

            print(f"[PROVIDER] Using Transformers with model: {model_name}")
            print(
                "[WARNING] Transformers provider loads model on GPU - ensure you have sufficient VRAM"
            )

            # Determine if we need trust_remote_code (for Qwen, Phi, and similar models)
            trust_remote_code = any(x in model_name.lower() for x in ["qwen", "phi", "starcoder"])
            if trust_remote_code:
                print(f"[PROVIDER] Enabling trust_remote_code for {model_name}")

            # Load model and tokenizer with proper configuration
            model = TransformersModel(
                model_id=model_name,
                device_map="auto",
                trust_remote_code=trust_remote_code,
                torch_dtype="auto",  # Automatically use the model's default dtype
            )

        except ImportError:
            raise ImportError(
                "Transformers provider requires 'transformers', 'torch', and 'accelerate'. "
                "Install with: pip install 'smoltrace[gpu]' or pip install transformers torch accelerate"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model with transformers: {e}")

    elif provider == "ollama":
        # Ollama provider for local models
        print(f"[PROVIDER] Using Ollama with model: {model_name}")
        print("[WARNING] Ensure Ollama is running locally on http://localhost:11434")

        # Remove provider prefix if present (e.g., "ollama/mistral" -> "mistral")
        model_id = model_name.replace("ollama/", "")
        model = LiteLLMModel(model_id=f"ollama/{model_id}", api_base="http://localhost:11434")

    else:
        raise ValueError(
            f"Unknown provider: {provider}. Must be 'litellm', 'inference', 'transformers', or 'ollama'"
        )

    # Get all tools (default custom tools + optional smolagents tools)
    tools = get_all_tools(
        search_provider=search_provider,
        additional_imports=additional_authorized_imports,
        enabled_smolagents_tools=enabled_smolagents_tools,
        working_dir=working_directory,
    )

    if mcp_server_url:
        mcp_tools = initialize_mcp_tools(mcp_server_url)
        tools.extend(mcp_tools)

    kwargs = {}
    if prompt_config:
        # Extract common parameters
        if "system_prompt" in prompt_config:
            kwargs["system_prompt"] = prompt_config["system_prompt"]
        if "max_steps" in prompt_config:
            kwargs["max_steps"] = prompt_config["max_steps"]
        if "name" in prompt_config:
            kwargs["name"] = prompt_config["name"]
        if "description" in prompt_config:
            kwargs["description"] = prompt_config["description"]
        if "verbosity_level" in prompt_config:
            kwargs["verbosity_level"] = prompt_config["verbosity_level"]

        # CodeAgent-specific parameters
        if agent_type == "code":
            if "prompt_templates" in prompt_config:
                kwargs["prompt_templates"] = prompt_config["prompt_templates"]
            if "additional_authorized_imports" in prompt_config:
                kwargs["additional_authorized_imports"] = prompt_config[
                    "additional_authorized_imports"
                ]
            if "grammar" in prompt_config:
                kwargs["grammar"] = prompt_config["grammar"]
            if "planning_interval" in prompt_config:
                kwargs["planning_interval"] = prompt_config["planning_interval"]

    # Add CLI-provided additional_authorized_imports for CodeAgent
    if agent_type == "code" and additional_authorized_imports:
        # Merge with prompt_config imports if both exist
        if "additional_authorized_imports" in kwargs:
            kwargs["additional_authorized_imports"] = list(
                set(kwargs["additional_authorized_imports"] + additional_authorized_imports)
            )
        else:
            kwargs["additional_authorized_imports"] = additional_authorized_imports

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


def extract_tools_from_code(code: str, available_tools: Optional[list] = None) -> list:
    """Extracts tool names from a given code string.

    Args:
        code: The code string to analyze
        available_tools: Optional list of tool objects to check for. If provided,
                        will look for calls to any of these tools. If not provided,
                        falls back to default tool patterns.

    Returns:
        List of tool names found in the code
    """
    tools_found = []

    if available_tools:
        # Extract tool names from available tools and build dynamic patterns
        for tool in available_tools:
            if hasattr(tool, "name"):
                tool_name = tool.name
                # Escape special regex characters in tool name
                escaped_name = re.escape(tool_name)
                pattern = rf"{escaped_name}\s*\("
                matches = re.findall(pattern, code)
                if matches:
                    tools_found.extend([tool_name] * len(matches))
    else:
        # Fallback to hardcoded patterns for backward compatibility
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
    agent,
    task: str,
    agent_type: str,
    tracer=None,
    debug: bool = False,
    model_args: Optional[Dict] = None,
) -> tuple[list, bool, int]:
    """Analyzes the streamed steps of an agent's run to extract tool usage, final answer calls, and step count.

    Args:
        agent: The agent instance to analyze
        task: The task/prompt to execute
        agent_type: Type of agent ("tool" or "code")
        tracer: Optional OpenTelemetry tracer
        debug: Whether to print debug information

    Returns:
        Tuple of (tools_used, final_answer_called, steps_count)
    """

    tools_used = []

    final_answer_called = False

    steps_count = 0

    # Extract available tools from agent for dynamic tool detection
    available_tools = getattr(agent, "tools", None)

    for event in agent.run(task, stream=True, max_steps=20, reset=True, additional_args=model_args):
        if debug:
            print(f"[DEBUG] Event type: {type(event).__name__}")

        if tracer:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.add_event(
                    "step",
                    attributes={"step_index": steps_count, "type": type(event).__name__},
                )

        if isinstance(event, ActionStep):
            steps_count += 1

            # Pass available_tools for dynamic MCP tool detection
            tools_used.extend(
                extract_tools_from_action_step(event, agent_type, debug, tracer, available_tools)
            )

            if is_final_answer_called_in_action_step(event, agent_type):
                final_answer_called = True

        elif isinstance(event, FinalAnswerStep):
            final_answer_called = True

            steps_count += 1

        elif isinstance(event, PlanningStep):
            steps_count += 1

    return tools_used, final_answer_called, steps_count


def extract_tools_from_action_step(
    event: ActionStep, agent_type: str, debug: bool, tracer, available_tools: Optional[list] = None
) -> list:
    """Extracts tools used from an ActionStep event.

    Args:
        event: The ActionStep event to analyze
        agent_type: Type of agent ("tool" or "code")
        debug: Whether to print debug information
        tracer: OpenTelemetry tracer for instrumentation
        available_tools: Optional list of available tool objects for dynamic extraction

    Returns:
        List of tool names used in this action step
    """

    tools = []

    if hasattr(event, "tool_calls") and event.tool_calls:
        for tool_call in event.tool_calls:
            if hasattr(tool_call, "name"):
                tool_name = tool_call.name

                if debug:
                    print(f"[DEBUG] Tool call: {tool_name}")

                if tracer:
                    current_span = trace.get_current_span()
                    if current_span and current_span.is_recording():
                        current_span.add_event("tool_call", attributes={"name": tool_name})

                if tool_name != "final_answer":
                    tools.append(tool_name)

    if agent_type == "code" and hasattr(event, "code") and event.code:
        # Pass available_tools to enable dynamic MCP tool detection
        code_tools = extract_tools_from_code(event.code, available_tools=available_tools)

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
    model_args: Optional[Dict] = None,
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
        "expected_tool": test_case.get("expected_tool"),
        "expected_tool_calls": test_case.get("expected_tool_calls"),
        "success": False,
        "tool_called": False,
        "correct_tool": False,
        "final_answer_called": False,
        "response_correct": True,  # Default to True, will be set to False if keyword check fails
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
                    agent,
                    test_case["prompt"],
                    agent_type,
                    tracer=tracer,
                    debug=debug,
                    model_args=model_args,
                )
                response = agent.run(test_case["prompt"], reset=True, additional_args=model_args)
                span.set_attribute("tests.tool_calls", len(tools_used))
                span.set_attribute("tests.steps", steps_count)
        else:
            tools_used, final_answer_called, steps_count = analyze_streamed_steps(
                agent, test_case["prompt"], agent_type, debug=debug, model_args=model_args
            )
            response = agent.run(test_case["prompt"], reset=True, additional_args=model_args)
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
        else:
            # If no expected keywords, consider response correct (no validation needed)
            result["response_correct"] = True

        # Hybrid approach: Different success criteria for code vs tool agents
        if agent_type == "code":
            # Code agents: Judge by response quality
            # Philosophy: Code agents write Python to solve problems,
            # they naturally batch multiple tool calls in one execution
            result["success"] = (
                result["tool_called"]  # Must use python_interpreter
                and result["final_answer_called"]  # Must call final_answer
                and result["response_correct"]  # Must have correct response (PRIMARY)
            )
            # Note: correct_tool is calculated but not required for success
        else:
            # Tool agents: Judge by tool usage + response quality
            # Philosophy: Tool agents should use the right tools
            result["success"] = (
                result["tool_called"]
                and result.get("correct_tool", True)  # Must use correct tool
                and result["final_answer_called"]
                and result["response_correct"]
            )
        if verbose:
            print(f"[RESPONSE] {response}")
            print(f"Tools used: {result['tools_used']}")
            print(f"Success: {result['success']}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Broad exception is caught here to ensure all test cases are evaluated
        # even if an unexpected error occurs during a single test run.
        result["error"] = str(e)
        if verbose:
            print(f"[ERROR] {e}")
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
    provider: str = "litellm",
    prompt_config: Optional[Dict] = None,
    mcp_server_url: Optional[str] = None,
    run_id: Optional[str] = None,
    enable_gpu_metrics: bool = False,
    additional_authorized_imports: Optional[List[str]] = None,
    search_provider: str = "duckduckgo",
    hf_inference_provider: Optional[str] = None,
    parallel_workers: int = 1,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_directory: Optional[str] = None,
    model_args: Optional[Dict] = None,
):
    """Runs the evaluation for specified agent types and test subsets, collecting traces and metrics.

    Args:
        model_name: Model identifier
        agent_types: List of agent types to evaluate ("tool" and/or "code")
        test_subset: Test difficulty filter
        dataset_name: HuggingFace dataset name for test cases
        split: Dataset split to use
        enable_otel: Whether to enable OpenTelemetry instrumentation
        verbose: Whether to print verbose output
        debug: Whether to enable debug mode
        provider: Model provider ("litellm", "inference", "transformers", or "ollama")
        prompt_config: Optional prompt configuration
        mcp_server_url: Optional MCP server URL
        run_id: Optional unique run identifier. If None, generates UUID.
        enable_gpu_metrics: Whether to enable GPU metrics collection (for GPU jobs)
        additional_authorized_imports: Additional Python modules authorized for CodeAgent imports
        search_provider: Search provider for GoogleSearchTool
        hf_inference_provider: HuggingFace inference provider (for "inference" provider)
        parallel_workers: Number of parallel workers (default: 1)
        enabled_smolagents_tools: List of smolagents tool names to enable
        working_directory: Working directory for file tools
        model_args: Additional model generation parameters (temperature, top_p, etc.)

    Returns:
        tuple: (all_results, trace_data, metric_data, dataset_name, run_id)
    """

    test_cases = load_test_cases_from_hf(dataset_name, split)

    # Setup OTEL with run_id support
    tracer, _, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
        enable_otel=enable_otel,
        service_name="smoltrace-eval",
        run_id=run_id,
        enable_gpu_metrics=enable_gpu_metrics,
    )

    all_results = {"tool": [], "code": []}

    for agent_type in agent_types:
        all_results[agent_type] = _run_agent_tests(
            agent_type,
            model_name,
            provider,
            prompt_config,
            mcp_server_url,
            test_cases,
            test_subset,
            tracer,
            verbose,
            debug,
            additional_authorized_imports,
            search_provider,
            hf_inference_provider,
            enabled_smolagents_tools,
            working_directory,
            model_args,
        )

    if verbose:
        print_combined_summary(all_results)

    # Extract traces and metrics
    trace_data = extract_traces(span_exporter, run_id) if span_exporter else []

    # CRITICAL FIX: Force flush metrics before collection
    # PeriodicExportingMetricReader exports every 10 seconds
    # If evaluation finishes in <10 seconds, metrics are still buffered
    if metric_exporter and enable_otel:
        try:
            from opentelemetry import metrics as otel_metrics

            meter_provider = otel_metrics.get_meter_provider()
            if hasattr(meter_provider, "force_flush"):
                meter_provider.force_flush(timeout_millis=30000)
                print("[OK] Forced metrics flush before extraction")
        except Exception as e:
            print(f"[WARNING] Failed to force flush metrics: {e}")

    # Extract metrics: both GPU time-series and trace aggregates
    metric_data = extract_metrics(
        metric_exporter, trace_aggregator, trace_data, all_results, run_id
    )

    # Enhance results with trace info and run_id
    test_index = 0
    for agent_type, results in all_results.items():
        for result in results:
            # Add run_id to every result
            result["run_id"] = run_id
            result["test_index"] = test_index
            test_index += 1

            if enable_otel:
                result["enhanced_trace_info"] = create_enhanced_trace_info(
                    trace_data, metric_data, result["test_id"]
                )

    return all_results, trace_data, metric_data, dataset_name, run_id


def _run_agent_tests(
    agent_type: str,
    model_name: str,
    provider: str,
    prompt_config: Optional[Dict],
    mcp_server_url: Optional[str],
    test_cases: List[Dict],
    test_subset: Optional[str],
    tracer,
    verbose: bool,
    debug: bool,
    additional_authorized_imports: Optional[List[str]] = None,
    search_provider: str = "duckduckgo",
    hf_inference_provider: Optional[str] = None,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_directory: Optional[str] = None,
    model_args: Optional[Dict] = None,
) -> List[Dict]:
    """Helper function to run tests for a single agent type and return results."""

    agent = initialize_agent(
        model_name,
        agent_type,
        provider,
        prompt_config,
        mcp_server_url,
        additional_authorized_imports,
        search_provider,
        hf_inference_provider,
        enabled_smolagents_tools,
        working_directory,
    )

    valid_tests = _filter_tests(test_cases, agent_type, test_subset)

    results = []

    for tc in valid_tests:
        result = evaluate_single_test(
            agent, tc.copy(), agent_type, tracer, None, verbose, debug, model_args
        )

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


def extract_traces(span_exporter, run_id: str) -> List[Dict]:
    """Extract trace data from the in-memory span exporter with run_id.

    Args:
        span_exporter: InMemorySpanExporter instance
        run_id: Unique run identifier to attach to all traces

    Returns:
        List of trace dictionaries with run_id and aggregated metrics
    """
    if not span_exporter:
        return []

    spans = span_exporter.get_finished_spans()

    # Import CostCalculator for post-processing cost calculation
    try:
        from genai_otel.cost_calculator import CostCalculator

        cost_calculator = CostCalculator()
        print("[OK] CostCalculator initialized for trace enrichment")
    except ImportError:
        cost_calculator = None
        print("[WARNING] genai_otel not available, costs will not be calculated")

    # Group spans by trace_id
    traces_by_id = {}
    for span in spans:
        trace_id = span.get("trace_id")
        if trace_id not in traces_by_id:
            traces_by_id[trace_id] = {
                "trace_id": trace_id,
                "run_id": run_id,  # Add run_id to trace
                "spans": [],
                "total_tokens": 0,
                "total_duration_ms": 0,
                "total_cost_usd": 0.0,
            }

        # POST-PROCESS: Calculate cost if not present in span attributes
        attrs = span.get("attributes", {})
        span_cost = 0.0

        # Check if cost is already in attributes
        if "gen_ai.usage.cost.total" in attrs:
            span_cost = float(attrs["gen_ai.usage.cost.total"])
        elif cost_calculator and ("llm.model_name" in attrs or "gen_ai.request.model" in attrs):
            # Cost not present but we have model and token info - calculate it!
            model = attrs.get("llm.model_name") or attrs.get("gen_ai.request.model")
            prompt_tokens = int(
                attrs.get("llm.token_count.prompt", 0) or attrs.get("gen_ai.usage.prompt_tokens", 0)
            )
            completion_tokens = int(
                attrs.get("llm.token_count.completion", 0)
                or attrs.get("gen_ai.usage.completion_tokens", 0)
            )

            if model and (prompt_tokens > 0 or completion_tokens > 0):
                # Determine call type from span kind
                span_kind = attrs.get("openinference.span.kind", "").upper()
                call_type = "chat" if span_kind == "LLM" else "chat"

                # Calculate cost using genai_otel's CostCalculator
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }

                cost_info = cost_calculator.calculate_granular_cost(
                    model=str(model),
                    usage=usage,
                    call_type=call_type,
                )

                if cost_info and cost_info.get("total", 0.0) > 0:
                    span_cost = cost_info["total"]
                    # Add cost to span attributes for downstream processing
                    span["attributes"]["gen_ai.usage.cost.total"] = span_cost
                    print(
                        f"[POST-CALC] Added cost ${span_cost:.6f} to span '{span.get('name')}' (model: {model}, tokens: {usage['total_tokens']})"
                    )

        traces_by_id[trace_id]["spans"].append(span)

        # Aggregate metrics
        if "llm.token_count.total" in attrs:
            traces_by_id[trace_id]["total_tokens"] += int(attrs["llm.token_count.total"])
        if "duration_ms" in span:
            traces_by_id[trace_id]["total_duration_ms"] += float(span["duration_ms"])
        if span_cost > 0:
            traces_by_id[trace_id]["total_cost_usd"] += span_cost

    return list(traces_by_id.values())


def extract_metrics(
    metric_exporter, trace_aggregator, trace_data: List[Dict], all_results: Dict, run_id: str
) -> Dict:
    """Extract metrics from both GPU time-series and trace aggregates.

    Args:
        metric_exporter: InMemoryMetricExporter for GPU time-series data
        trace_aggregator: TraceMetricsAggregator for span-based aggregates
        trace_data: List of trace dictionaries
        all_results: Dict of results by agent type
        run_id: Unique run identifier

    Returns:
        Dict containing:
        - run_id: Unique identifier
        - resourceMetrics: GPU time-series data in OpenTelemetry format
        - aggregates: Trace-based aggregate metrics (tokens, CO2, etc.)
    """
    print(f"\n[extract_metrics] Starting metric extraction for run_id: {run_id}")
    print(f"[extract_metrics] metric_exporter present: {metric_exporter is not None}")
    print(f"[extract_metrics] trace_aggregator present: {trace_aggregator is not None}")

    metrics_dict = {"run_id": run_id, "resourceMetrics": [], "aggregates": []}

    # Get GPU time-series metrics from metric_exporter (if available)
    if metric_exporter:
        try:
            gpu_metrics = metric_exporter.get_metrics_data()
            metrics_dict["resourceMetrics"] = gpu_metrics
            if gpu_metrics:
                print(f"[Metrics] Collected {len(gpu_metrics)} GPU metric batches")
            else:
                print("[Metrics] No GPU metrics collected (empty list - likely API model)")
        except Exception as e:
            print(f"[WARNING] Failed to collect GPU metrics: {e}")
            import traceback

            traceback.print_exc()
            metrics_dict["resourceMetrics"] = []
    else:
        print("[Metrics] No metric_exporter available")

    # Get trace-based aggregates from trace_aggregator
    if trace_aggregator:
        try:
            trace_metrics = trace_aggregator.collect_all(trace_data, all_results)
            metrics_dict["aggregates"] = trace_metrics
            print(f"[Metrics] Aggregated {len(trace_metrics)} trace metrics")
        except Exception as e:
            print(f"[WARNING] Failed to aggregate trace metrics: {e}")
            import traceback

            traceback.print_exc()
            metrics_dict["aggregates"] = []
    else:
        print("[Metrics] No trace_aggregator available")

    print("[extract_metrics] Final metrics_dict structure:")
    print(f"  - run_id: {metrics_dict['run_id']}")
    print(f"  - resourceMetrics: {len(metrics_dict['resourceMetrics'])} batches")
    print(f"  - aggregates: {len(metrics_dict['aggregates'])} metrics")

    return metrics_dict


def create_enhanced_trace_info(
    trace_data: List[Dict], metric_data: List[Dict], test_id: str
) -> Dict:
    """Create enhanced trace information summary for a specific test case."""
    # Find trace matching this test
    matching_trace = None
    for trace_item in trace_data:
        for span in trace_item.get("spans", []):
            attrs = span.get("attributes", {})
            if attrs.get("test.id") == test_id:
                matching_trace = trace_item
                break
        if matching_trace:
            break

    if not matching_trace:
        return {}

    # Build summary
    return {
        "trace_id": matching_trace.get("trace_id"),
        "total_tokens": matching_trace.get("total_tokens", 0),
        "duration_ms": matching_trace.get("total_duration_ms", 0),
        "cost_usd": matching_trace.get("total_cost_usd", 0.0),
        "span_count": len(matching_trace.get("spans", [])),
    }
