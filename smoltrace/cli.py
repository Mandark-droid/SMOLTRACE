# smoltrace/cli.py
"""CLI for running smoltrace evaluations."""

import argparse
import json

from dotenv import load_dotenv

from .main import run_evaluation_flow

# Load .env file at startup
load_dotenv()


def parse_model_args(model_args_list):
    """Parse model arguments from key=value format to dict.

    Supports various value types:
    - Numbers: temperature=0.7, max_tokens=2048
    - Booleans: stream=true, logprobs=false
    - Strings: model=gpt-4, stop=END
    - Lists (JSON): stop=["STOP","END"]

    Args:
        model_args_list: List of "key=value" strings

    Returns:
        Dict of parsed arguments with proper types
    """
    if not model_args_list:
        return {}

    parsed = {}
    for arg in model_args_list:
        if "=" not in arg:
            print(f"[WARNING] Ignoring invalid model arg (missing '='): {arg}")
            continue

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Try to parse as JSON first (handles lists, dicts, etc.)
        try:
            parsed[key] = json.loads(value)
            continue
        except json.JSONDecodeError:
            pass

        # Try to parse as number
        try:
            # Try int first
            if "." not in value:
                parsed[key] = int(value)
                continue
            # Then float
            parsed[key] = float(value)
            continue
        except ValueError:
            pass

        # Try to parse as boolean
        if value.lower() in ("true", "false"):
            parsed[key] = value.lower() == "true"
            continue

        # Default to string
        parsed[key] = value

    return parsed


def main():
    """Main entry point for the smoltrace CLI."""
    parser = argparse.ArgumentParser(
        description="Run agent evaluations with enhanced dataset management"
    )

    # Core arguments
    parser.add_argument("--model", type=str, required=True, help="Model ID")
    parser.add_argument(
        "--provider",
        type=str,
        choices=["litellm", "inference", "transformers", "ollama"],
        default="litellm",
        help="Model provider: litellm (API models), inference (HF Inference API), transformers (HF GPU models), ollama (local)",
    )
    parser.add_argument(
        "--hf-inference-provider",
        type=str,
        help="HuggingFace inference provider for InferenceClientModel (e.g., 'hf-inference-api', 'tgi')",
    )
    parser.add_argument(
        "--search-provider",
        type=str,
        choices=["serper", "brave", "duckduckgo"],
        default="duckduckgo",
        help="Search provider for GoogleSearchTool (default: duckduckgo)",
    )
    parser.add_argument(
        "--enable-tools",
        type=str,
        nargs="+",
        help="Enable optional smolagents tools. Options: google_search, duckduckgo_search, visit_webpage, python_interpreter, wikipedia_search, user_input",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help="Deprecated: HuggingFace token on the command line. Prefer HF_TOKEN or --hf-token-file.",
    )
    parser.add_argument(
        "--hf-token-file",
        type=str,
        help="Read the HuggingFace token from a file instead of exposing it in the process list",
    )

    # Agent configuration
    parser.add_argument(
        "--agent-type",
        type=str,
        choices=["tool", "code", "both"],
        default="both",
        help="Type of agent to evaluate",
    )
    parser.add_argument("--prompt-yml", type=str, help="Path to prompt configuration YAML file")
    parser.add_argument(
        "--mcp-server-url",
        type=str,
        action="append",
        help="MCP server URL for MCP tools. Repeat for multiple servers; use name=URL to prefix tool names and avoid collisions.",
    )
    parser.add_argument(
        "--mcp-transport",
        choices=["auto", "streamable-http", "sse"],
        default="auto",
        help="MCP transport (default: auto; /sse URLs use legacy SSE, other URLs use streamable HTTP).",
    )
    parser.add_argument(
        "--additional-imports",
        type=str,
        nargs="+",
        help="Additional Python modules authorized for CodeAgent imports (e.g., pandas numpy matplotlib)",
    )
    parser.add_argument(
        "--model-args",
        type=str,
        nargs="+",
        metavar="KEY=VALUE",
        help="Additional model generation parameters as key=value pairs. "
        "Examples: temperature=0.7 top_p=0.9 max_tokens=2048 seed=42. "
        "Passed directly to the model via smolagents' additional_args. "
        "Supports: temperature, top_p, top_k, max_tokens, frequency_penalty, presence_penalty, seed, stop, and more. "
        "Available parameters depend on your model provider (OpenAI, Anthropic, etc.).",
    )

    # Test configuration
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        help="Filter tests by difficulty",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="kshitijthakkar/smoltrace-tasks",
        help="HF dataset for tasks",
    )
    parser.add_argument(
        "--dataset-revision",
        type=str,
        help="Immutable HuggingFace dataset commit SHA (required for remote datasets)",
    )
    parser.add_argument("--split", type=str, default="train", help="Dataset split to use")

    # Options
    privacy_group = parser.add_mutually_exclusive_group()
    privacy_group.add_argument(
        "--private", dest="private", action="store_true", help="Keep Hub datasets private (default)"
    )
    privacy_group.add_argument(
        "--public",
        dest="private",
        action="store_false",
        help="Explicitly publish Hub datasets publicly; outputs may contain prompts and responses",
    )
    parser.set_defaults(private=True)
    parser.add_argument("--enable-otel", action="store_true", help="Enable OTEL tracing")
    parser.add_argument(
        "--disable-gpu-metrics",
        action="store_true",
        help="Disable GPU metrics collection (enabled by default for local models: transformers, ollama)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional unique run identifier (UUID format). Generated automatically if not provided. Use this to filter results in the leaderboard.",
    )
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Allow HuggingFace model repositories to execute custom Python code (unsafe for untrusted models)",
    )
    parser.add_argument(
        "--allow-test-fallback",
        action="store_true",
        help="Developer-only: use built-in tasks if the requested dataset cannot be loaded",
    )
    parser.add_argument(
        "--security-profile",
        choices=["standard", "bfsi-closed"],
        default="standard",
        help="Runtime security policy. bfsi-closed denies external egress, unsafe tools, and insecure remote OpenSearch.",
    )
    parser.add_argument(
        "--allow-local-code-execution",
        action="store_true",
        help="Explicitly allow CodeAgent local Python execution (rejected by bfsi-closed unless set)",
    )
    parser.add_argument(
        "--use-case",
        type=str,
        help="Use case or domain this evaluation run belongs to",
    )
    parser.add_argument(
        "--team",
        type=str,
        help="Owning team or organization",
    )
    parser.add_argument(
        "--purpose",
        type=str,
        choices=["selection", "regression", "monitoring"],
        help="Evaluation purpose",
    )
    parser.add_argument(
        "--suite-version",
        type=str,
        help="Version identifier of the evaluated task suite",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["hub", "json", "opensearch"],
        default="hub",
        help="Output format: 'hub' (push to HuggingFace), 'json' (save locally), or 'opensearch' (export to OpenSearch)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./smoltrace_results",
        help="Directory for local JSON output (when --output-format=json)",
    )
    # OpenSearch options
    opensearch_group = parser.add_argument_group(
        "OpenSearch options (for --output-format=opensearch)"
    )
    opensearch_group.add_argument(
        "--opensearch-url",
        type=str,
        help="Full OpenSearch URL (e.g., https://search-my-domain.us-east-1.es.amazonaws.com)",
    )
    opensearch_group.add_argument(
        "--opensearch-host",
        type=str,
        default="localhost",
        help="OpenSearch host (default: localhost)",
    )
    opensearch_group.add_argument(
        "--opensearch-port",
        type=int,
        default=9200,
        help="OpenSearch port (default: 9200)",
    )
    opensearch_group.add_argument(
        "--opensearch-user",
        type=str,
        help="OpenSearch username for basic auth",
    )
    opensearch_group.add_argument(
        "--opensearch-password",
        type=str,
        help="Deprecated: OpenSearch password on the command line. Prefer OPENSEARCH_PASSWORD or --opensearch-password-file.",
    )
    opensearch_group.add_argument(
        "--opensearch-password-file",
        type=str,
        help="Read the OpenSearch password from a file",
    )
    opensearch_group.add_argument(
        "--opensearch-ssl",
        action="store_true",
        help="Use SSL/TLS for OpenSearch connection",
    )
    opensearch_group.add_argument(
        "--opensearch-no-verify-certs",
        action="store_true",
        help="Disable SSL certificate verification",
    )
    opensearch_group.add_argument(
        "--opensearch-index-prefix",
        type=str,
        default="smoltrace",
        help="Prefix for OpenSearch index names (default: smoltrace)",
    )
    opensearch_group.add_argument(
        "--opensearch-allow-insecure-remote",
        action="store_true",
        help="Development-only override for remote OpenSearch without authenticated verified TLS",
    )

    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help="Number of parallel workers for evaluation (default: 1, recommended: 8 for API models)",
    )
    parser.add_argument(
        "--working-directory",
        type=str,
        default=None,
        help="Working directory for file tools (restricts file operations to this directory). Required when using file tools (read_file, write_file, list_directory, search_files). Defaults to current directory if not specified.",
    )

    args = parser.parse_args()

    # Parse model arguments
    args.model_args_dict = parse_model_args(getattr(args, "model_args", None))
    if args.model_args_dict:
        redacted_model_args = {
            key: (
                "[REDACTED]"
                if key.lower() in {"key", "token", "secret", "password", "authorization"}
                or any(
                    key.lower().endswith(f"_{marker}")
                    for marker in ("api_key", "token", "secret", "password")
                )
                else value
            )
            for key, value in args.model_args_dict.items()
        }
        print(f"[MODEL ARGS] Parsed model arguments: {redacted_model_args}")

    # Run evaluation
    run_evaluation_flow(args)


if __name__ == "__main__":  # pragma: no cover
    main()
