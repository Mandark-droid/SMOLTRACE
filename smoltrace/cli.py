# smoltrace/cli.py
"""CLI for running smoltrace evaluations."""

import argparse


def main():
    """Main entry point for the smoltrace CLI."""
    parser = argparse.ArgumentParser(
        description="Run agent evaluations with enhanced dataset management"
    )

    # Core arguments
    parser.add_argument("--model", type=str, required=True, help="Model ID")
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
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # The core logic will be called from here
    print("SMOLTRACE CLI")
    print("Arguments:", args)
    # In the next steps, we will call the main evaluation logic:
    # run_evaluation_flow(args)


if __name__ == "__main__":
    main()
