# smoltrace/core.py
"""Core evaluation logic for smoltrace."""

import gc
import json
import os
import re
import threading
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Union

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

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


def _cleanup_gpu_memory(verbose: bool = False):
    """Frees GPU memory between test iterations to prevent OOM.

    Clears PyTorch's CUDA cache and runs Python garbage collection to release
    tensors (KV cache, activations, intermediate buffers) that are no longer
    referenced but haven't been returned to the CUDA allocator yet.
    """
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            if verbose:
                allocated = torch.cuda.memory_allocated() / 1024**2
                reserved = torch.cuda.memory_reserved() / 1024**2
                print(
                    f"[GPU] After cleanup: {allocated:.0f} MiB allocated, {reserved:.0f} MiB reserved"
                )
    except ImportError:
        pass


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
    dataset_name: str = "kshitijthakkar/smoltrace-tasks",
    split: str = "train",
    allow_fallback: bool = False,
    revision: Optional[str] = None,
) -> List[Dict]:
    """Load test cases, failing closed unless developer fallback is explicitly enabled."""
    try:
        dataset_path = Path(dataset_name)
        if dataset_path.is_file() and dataset_path.suffix.lower() in {".json", ".jsonl"}:
            if dataset_path.suffix.lower() == ".jsonl":
                return [
                    json.loads(line)
                    for line in dataset_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            payload = json.loads(dataset_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = payload.get(split, payload.get("data"))
            if not isinstance(payload, list):
                raise ValueError("Local JSON dataset must contain a list or a split/data list")
            return [dict(row) for row in payload]
        else:
            if not revision:
                raise ValueError("Remote datasets require an immutable --dataset-revision")
            ds = load_dataset(dataset_name, split=split, revision=revision)
        return [dict(row) for row in ds]
    except Exception as e:
        if allow_fallback:
            print(f"[WARNING] Error loading dataset: {e}. Using explicit developer fallback.")
            return DEFAULT_TOOL_TESTS + DEFAULT_CODE_TESTS
        raise RuntimeError(
            f"Failed to load requested dataset '{dataset_name}' split '{split}'; "
            "refusing to substitute fallback tasks. Use --allow-test-fallback only for local development."
        ) from e


def _initialize_model(
    model_name: str,
    provider: str,
    hf_inference_provider: Optional[str] = None,
    trust_remote_code: bool = False,
):
    """Initialize one provider model so it can be reused across sequential agent types."""

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

            if trust_remote_code:
                print(f"[WARNING] trust_remote_code explicitly enabled for {model_name}")

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
    return model


def initialize_agent(
    model_name: str,
    agent_type: str,
    provider: str = "litellm",
    prompt_config: Optional[Dict] = None,
    mcp_server_url: Optional[Union[str, List[str]]] = None,
    additional_authorized_imports: Optional[List[str]] = None,
    search_provider: str = "duckduckgo",
    hf_inference_provider: Optional[str] = None,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_directory: Optional[str] = None,
    mcp_transport: str = "auto",
    model_instance=None,
    trust_remote_code: bool = False,
):
    """Initialize an evaluation agent with an optionally shared provider model."""
    model = model_instance or _initialize_model(
        model_name, provider, hf_inference_provider, trust_remote_code=trust_remote_code
    )

    # Get all tools (default custom tools + optional smolagents tools)
    tools = get_all_tools(
        search_provider=search_provider,
        additional_imports=additional_authorized_imports,
        enabled_smolagents_tools=enabled_smolagents_tools,
        working_dir=working_directory,
    )

    if mcp_server_url:
        if mcp_transport == "auto":
            mcp_tools = initialize_mcp_tools(mcp_server_url)
        else:
            mcp_tools = initialize_mcp_tools(mcp_server_url, transport=mcp_transport)
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

    max_steps = kwargs.pop("max_steps", 6)
    if agent_type == "tool":
        return ToolCallingAgent(tools=tools, model=model, max_steps=max_steps, **kwargs)
    return CodeAgent(
        tools=tools,
        model=model,
        executor_type="local",
        max_steps=max_steps,
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
) -> tuple[list, bool, int, str]:
    """Analyzes the streamed steps of an agent's run to extract tool usage, final answer calls, step count, and response.

    Args:
        agent: The agent instance to analyze
        task: The task/prompt to execute
        agent_type: Type of agent ("tool" or "code")
        tracer: Optional OpenTelemetry tracer
        debug: Whether to print debug information

    Returns:
        Tuple of (tools_used, final_answer_called, steps_count, response)
    """

    tools_used = []

    final_answer_called = False

    steps_count = 0

    response = None

    # Extract available tools from agent for dynamic tool detection
    available_tools = getattr(agent, "tools", None)

    for event in agent.run(task, stream=True, reset=True, additional_args=model_args):
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
            response = event.output

            steps_count += 1

        elif isinstance(event, PlanningStep):
            steps_count += 1

    return tools_used, final_answer_called, steps_count, response


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


def build_test_case_uid(agent_type: str, test_id: str) -> str:
    """Builds the stable key that identifies one execution of one test case.

    A test case declared with ``agent_type: "both"`` is executed once per agent
    type and emits a separate trace each time, so ``test_id`` on its own is not
    unique within a run. ``"<agent_type>:<test_id>"`` is deterministic, which
    keeps it usable as a join key on both the result and the trace side.
    """
    return f"{agent_type}:{test_id}"


def span_identifiers(span) -> Dict[str, Optional[str]]:
    """Reads ``trace_id``/``span_id`` off a live span in the exporter's format.

    Must stay byte-identical to ``InMemorySpanExporter._to_dict`` (``hex()``),
    otherwise results and trace documents would not join.
    """
    try:
        context = span.get_span_context()
        return {"trace_id": hex(context.trace_id), "span_id": hex(context.span_id)}
    except Exception:  # pylint: disable=broad-exception-caught
        # A no-op/non-recording span must never break an evaluation.
        return {"trace_id": None, "span_id": None}


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
    test_case_uid = build_test_case_uid(agent_type, test_case["id"])
    result = {
        "test_id": test_case["id"],
        # Stable per-execution key. A test case with agent_type "both" runs once
        # per agent type and produces a distinct trace each time, so test_id
        # alone cannot identify which execution a trace belongs to.
        "test_case_uid": test_case_uid,
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
        # Captured at the source from the root test span so the link survives
        # even when the test errors out or its spans never reach the exporter.
        "trace_id": None,
        "span_id": None,
        "enhanced_trace_info": None,
    }
    try:
        span_attributes = {
            "test.id": test_case["id"],
            "test.case_uid": test_case_uid,
            "test.difficulty": test_case["difficulty"],
            "agent.type": agent_type,
            "prompt": test_case["prompt"][:100],
        }
        if tracer:
            with tracer.start_as_current_span(
                "test_evaluation", attributes=span_attributes
            ) as span:
                # Record the trace context BEFORE running the agent: an agent
                # failure must not cost us the trace link.
                result.update(span_identifiers(span))
                tools_used, final_answer_called, steps_count, response = analyze_streamed_steps(
                    agent,
                    test_case["prompt"],
                    agent_type,
                    tracer=tracer,
                    debug=debug,
                    model_args=model_args,
                )
                span.set_attribute("tests.tool_calls", len(tools_used))
                span.set_attribute("tests.steps", steps_count)
        else:
            tools_used, final_answer_called, steps_count, response = analyze_streamed_steps(
                agent, test_case["prompt"], agent_type, debug=debug, model_args=model_args
            )
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
    mcp_server_url: Optional[Union[str, List[str]]] = None,
    run_id: Optional[str] = None,
    enable_gpu_metrics: bool = False,
    additional_authorized_imports: Optional[List[str]] = None,
    search_provider: str = "duckduckgo",
    hf_inference_provider: Optional[str] = None,
    parallel_workers: int = 1,
    enabled_smolagents_tools: Optional[List[str]] = None,
    working_directory: Optional[str] = None,
    model_args: Optional[Dict] = None,
    mcp_transport: str = "auto",
    allow_test_fallback: bool = False,
    trust_remote_code: bool = False,
    dataset_revision: Optional[str] = None,
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
        mcp_server_url: Optional MCP server URL or list of URL specifications
        run_id: Optional unique run identifier. If None, generates UUID.
        enable_gpu_metrics: Whether to enable GPU metrics collection (for GPU jobs)
        additional_authorized_imports: Additional Python modules authorized for CodeAgent imports
        search_provider: Search provider for GoogleSearchTool
        hf_inference_provider: HuggingFace inference provider (for "inference" provider)
        parallel_workers: Number of parallel workers (default: 1)
        enabled_smolagents_tools: List of smolagents tool names to enable
        working_directory: Working directory for file tools
        model_args: Additional model generation parameters (temperature, top_p, etc.)
        mcp_transport: MCP transport override ("auto", "streamable-http", or "sse")

    Returns:
        tuple: (all_results, trace_data, metric_data, dataset_name, run_id)
    """

    test_cases = load_test_cases_from_hf(
        dataset_name,
        split,
        allow_fallback=allow_test_fallback,
        revision=dataset_revision,
    )

    run_id = run_id or str(uuid.uuid4())
    # Setup OTEL with run_id support
    generated_run_id = run_id
    tracer, _, span_exporter, metric_exporter, trace_aggregator, otel_run_id = setup_inmemory_otel(
        enable_otel=enable_otel,
        service_name="smoltrace-eval",
        run_id=run_id,
        enable_gpu_metrics=enable_gpu_metrics,
    )
    run_id = otel_run_id or generated_run_id

    all_results = {"tool": [], "code": []}

    # Only run GPU cleanup for local model providers that use VRAM
    gpu_provider = provider in ("transformers",)
    effective_workers = max(1, parallel_workers)
    if gpu_provider and effective_workers > 1:
        print("[WARNING] Parallel workers are disabled for the transformers provider")
        effective_workers = 1
    if mcp_server_url and effective_workers > 1:
        print("[WARNING] Parallel workers are disabled when MCP servers are configured")
        effective_workers = 1

    shared_model = None
    if effective_workers == 1:
        shared_model = _initialize_model(
            model_name,
            provider,
            hf_inference_provider,
            trust_remote_code=trust_remote_code,
        )

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
            gpu_provider=gpu_provider,
            mcp_transport=mcp_transport,
            parallel_workers=effective_workers,
            model_instance=shared_model,
            trust_remote_code=trust_remote_code,
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
    trace_index = _build_trace_summary_index(trace_data)
    test_index = 0
    for agent_type, results in all_results.items():
        for result in results:
            # Add run_id to every result
            result["run_id"] = run_id
            result["test_index"] = test_index
            test_index += 1
            result.setdefault("test_case_uid", build_test_case_uid(agent_type, result["test_id"]))

            if enable_otel:
                result["enhanced_trace_info"] = create_enhanced_trace_info(
                    trace_data,
                    metric_data,
                    result["test_id"],
                    trace_index=trace_index,
                    test_case_uid=result.get("test_case_uid"),
                )
                # The source-captured ids win; fall back to the reconstructed
                # summary only when the span context was never available.
                if not result.get("trace_id"):
                    result["trace_id"] = result["enhanced_trace_info"].get("trace_id")
                if not result.get("span_id"):
                    result["span_id"] = result["enhanced_trace_info"].get("root_span_id")

    return all_results, trace_data, metric_data, dataset_name, run_id


def _run_agent_tests(
    agent_type: str,
    model_name: str,
    provider: str,
    prompt_config: Optional[Dict],
    mcp_server_url: Optional[Union[str, List[str]]],
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
    gpu_provider: bool = False,
    mcp_transport: str = "auto",
    parallel_workers: int = 1,
    model_instance=None,
    trust_remote_code: bool = False,
) -> List[Dict]:
    """Helper function to run tests for a single agent type and return results."""

    valid_tests = _filter_tests(test_cases, agent_type, test_subset)
    if parallel_workers > 1 and valid_tests:
        worker_state = threading.local()

        def evaluate_in_worker(test_case):
            if not hasattr(worker_state, "agent"):
                worker_state.agent = initialize_agent(
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
                    mcp_transport=mcp_transport,
                    trust_remote_code=trust_remote_code,
                )
            return evaluate_single_test(
                worker_state.agent,
                test_case.copy(),
                agent_type,
                tracer,
                None,
                verbose,
                debug,
                model_args,
            )

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            results = list(executor.map(evaluate_in_worker, valid_tests))
    else:
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
            mcp_transport=mcp_transport,
            model_instance=model_instance,
            trust_remote_code=trust_remote_code,
        )
        results = []
        for test_number, tc in enumerate(valid_tests, start=1):
            results.append(
                evaluate_single_test(
                    agent, tc.copy(), agent_type, tracer, None, verbose, debug, model_args
                )
            )
            if gpu_provider and test_number % 10 == 0:
                _cleanup_gpu_memory(verbose=debug)
        if gpu_provider and valid_tests and len(valid_tests) % 10:
            _cleanup_gpu_memory(verbose=debug)

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
                # Test-case identity, promoted to the top level so the trace can
                # be joined back to its result row without walking nested spans.
                "root_span_id": None,
                "test_ids": [],
                "test_case_uids": [],
                "agent_type": None,
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

        # Promote test-case identity from the root test span to the trace doc.
        trace_entry = traces_by_id[trace_id]
        for attr_key, field in (("test.id", "test_ids"), ("test.case_uid", "test_case_uids")):
            value = attrs.get(attr_key)
            if value and value not in trace_entry[field]:
                trace_entry[field].append(value)
        if trace_entry["agent_type"] is None and attrs.get("agent.type"):
            trace_entry["agent_type"] = attrs["agent.type"]
        if trace_entry["root_span_id"] is None and not span.get("parent_span_id"):
            trace_entry["root_span_id"] = span.get("span_id")

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


def _build_trace_summary_index(trace_data: List[Dict]) -> Dict[str, Dict]:
    """Build a single-pass lookup for trace summaries.

    Indexed by ``test.case_uid`` (unique per execution) and, for backward
    compatibility, by ``test.id``. The ``test.id`` keys stay first-wins and are
    therefore ambiguous for ``agent_type: "both"`` test cases — prefer the uid.
    """
    trace_index: Dict[str, Dict] = {}
    for trace_item in trace_data:
        summary = {
            "trace_id": trace_item.get("trace_id"),
            "root_span_id": trace_item.get("root_span_id"),
            "total_tokens": trace_item.get("total_tokens", 0),
            "duration_ms": trace_item.get("total_duration_ms", 0),
            "cost_usd": trace_item.get("total_cost_usd", 0.0),
            "span_count": len(trace_item.get("spans", [])),
        }
        for span in trace_item.get("spans", []):
            attributes = span.get("attributes", {}) or {}
            for key in (attributes.get("test.case_uid"), attributes.get("test.id")):
                if key and key not in trace_index:
                    trace_index[key] = summary
    return trace_index


def create_enhanced_trace_info(
    trace_data: List[Dict],
    metric_data: List[Dict],
    test_id: str,
    trace_index: Optional[Dict[str, Dict]] = None,
    test_case_uid: Optional[str] = None,
) -> Dict:
    """Create enhanced trace information summary for a specific test case.

    ``test_case_uid`` is preferred when supplied because ``test_id`` is not
    unique across agent types; ``test_id`` remains the fallback so existing
    callers keep working.
    """
    del metric_data  # Reserved for future metric-derived summary fields.
    index = trace_index or _build_trace_summary_index(trace_data)
    if test_case_uid and test_case_uid in index:
        return index[test_case_uid]
    return index.get(test_id, {})
