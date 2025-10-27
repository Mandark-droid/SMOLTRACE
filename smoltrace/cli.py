# smoltrace/cli.py
"""CLI for running smoltrace evaluations."""

import argparse

from dotenv import load_dotenv

from .main import run_evaluation_flow

# Load .env file at startup
load_dotenv()


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
        choices=["litellm", "transformers", "ollama"],
        default="litellm",
        help="Model provider: litellm (API models), transformers (HF GPU models), ollama (local)",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help="HuggingFace token (can also be set with HF_TOKEN env var)",
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
    parser.add_argument("--mcp-server-url", type=str, help="MCP server URL for MCP tools")

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
        default="kshitijthakkar/smoalagent-tasks",
        help="HF dataset for tasks",
    )
    parser.add_argument("--split", type=str, default="train", help="Dataset split to use")

    # Options
    parser.add_argument("--private", action="store_true", help="Make result datasets private")
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
        "--output-format",
        type=str,
        choices=["hub", "json"],
        default="hub",
        help="Output format: 'hub' (push to HuggingFace) or 'json' (save locally)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./smoltrace_results",
        help="Directory for local JSON output (when --output-format=json)",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Run evaluation
    run_evaluation_flow(args)


if __name__ == "__main__":  # pragma: no cover
    main()
