# smoltrace/main.py
"""Main execution flow for smoltrace evaluations."""

import os

from .core import run_evaluation
from .utils import (
    compute_leaderboard_row,
    generate_dataset_names,
    get_hf_user_info,
    load_prompt_config,
    push_results_to_hf,
    update_leaderboard,
)


def run_evaluation_flow(args):
    """
    The main function to run the complete evaluation flow.
    """
    # Get user info from HF token
    hf_token = args.hf_token or os.getenv("HF_TOKEN")
    if not hf_token:
        print(
            "Error: HuggingFace token not found. Please provide it via --hf-token or the HF_TOKEN environment variable."
        )
        return

    user_info = get_hf_user_info(hf_token)
    if not user_info:
        print("Error: Invalid HF token or unable to fetch user info.")
        return

    print(f"✅ Logged in as: {user_info['username']}")

    # Generate dataset names
    results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(
        user_info["username"]
    )
    print(f"📊 Results will be saved to: {results_repo}")
    print(f"✨ Traces will be saved to: {traces_repo}")
    print(f"📈 Metrics will be saved to: {metrics_repo}")
    print(f"🏆 Leaderboard will be at: {leaderboard_repo}")

    # Load prompt config
    prompt_config = load_prompt_config(args.prompt_yml)
    if prompt_config:
        print(f"📝 Loaded prompt config from {args.prompt_yml}")

    # Run evaluation
    agent_types = ["tool", "code"] if args.agent_type == "both" else [args.agent_type]
    verbose = not args.quiet

    all_results, trace_data, metric_data, dataset_used = run_evaluation(
        model_name=args.model,
        agent_types=agent_types,
        test_subset=args.difficulty,
        dataset_name=args.dataset_name,
        split=args.split,
        enable_otel=args.enable_otel,
        verbose=verbose,
        debug=args.debug,
        prompt_config=prompt_config,
        mcp_server_url=args.mcp_server_url,
    )

    # Push results, traces, and metrics
    push_results_to_hf(
        all_results,
        trace_data,
        metric_data,
        results_repo,
        traces_repo,
        metrics_repo,
        args.model,
        hf_token,
        args.private,
    )

    # Update leaderboard
    leaderboard_row = compute_leaderboard_row(
        args.model,
        all_results,
        trace_data,
        metric_data,
        dataset_used,
        results_repo,
        traces_repo,
        metrics_repo,
        args.agent_type,
    )
    update_leaderboard(leaderboard_repo, leaderboard_row, hf_token)

    print("\n✅ Evaluation complete!")
