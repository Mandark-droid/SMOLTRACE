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

    print(f"[OK] Logged in as: {user_info['username']}")

    # Generate dataset names
    results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(
        user_info["username"]
    )
    print(f"[RESULTS] Will be saved to: {results_repo}")
    print(f"[TRACES] Will be saved to: {traces_repo}")
    print(f"[METRICS] Will be saved to: {metrics_repo}")
    print(f"[LEADERBOARD] Will be at: {leaderboard_repo}")

    # Load prompt config
    prompt_config = load_prompt_config(args.prompt_yml)
    if prompt_config:
        print(f"[CONFIG] Loaded prompt config from {args.prompt_yml}")

    # Run evaluation
    agent_types = ["tool", "code"] if args.agent_type == "both" else [args.agent_type]
    verbose = not args.quiet

    # Determine if GPU metrics should be enabled
    # Default: Enable for ALL local models (transformers, ollama), disable for API models (litellm)
    # Allow users to opt-out with --disable-gpu-metrics flag
    is_local_model = args.provider in ["transformers", "ollama"]
    user_disabled = hasattr(args, "disable_gpu_metrics") and args.disable_gpu_metrics

    if user_disabled:
        enable_gpu_metrics = False  # User explicitly disabled GPU metrics
        print("[INFO] GPU metrics disabled by user (--disable-gpu-metrics flag)")
    elif is_local_model:
        enable_gpu_metrics = True  # Auto-enable for local models (transformers, ollama)
    else:
        enable_gpu_metrics = False  # API models (litellm) don't need GPU metrics

    all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
        model_name=args.model,
        agent_types=agent_types,
        test_subset=args.difficulty,
        dataset_name=args.dataset_name,
        split=args.split,
        enable_otel=args.enable_otel,
        verbose=verbose,
        debug=args.debug,
        provider=args.provider,
        prompt_config=prompt_config,
        mcp_server_url=args.mcp_server_url,
        run_id=getattr(args, "run_id", None),  # Get from CLI if provided
        enable_gpu_metrics=enable_gpu_metrics,
        additional_authorized_imports=getattr(args, "additional_imports", None),
        search_provider=getattr(args, "search_provider", "duckduckgo"),
        hf_inference_provider=getattr(args, "hf_inference_provider", None),
        parallel_workers=getattr(args, "parallel_workers", 1),
        enabled_smolagents_tools=getattr(args, "enable_tools", None),
        working_directory=getattr(args, "working_directory", None),
        model_args=getattr(args, "model_args_dict", None),
    )

    print(f"\n[RUN ID] {run_id}")

    # Output results based on format
    if args.output_format == "hub":
        # Push results, traces, and metrics to HuggingFace
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
            run_id,  # Pass run_id
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
            run_id,  # Pass run_id
            provider=args.provider,  # Pass provider
        )
        update_leaderboard(leaderboard_repo, leaderboard_row, hf_token)

        print("\n[SUCCESS] Evaluation complete! Results pushed to HuggingFace Hub.")
        print(f"  Results: https://huggingface.co/datasets/{results_repo}")
        print(f"  Traces: https://huggingface.co/datasets/{traces_repo}")
        print(f"  Metrics: https://huggingface.co/datasets/{metrics_repo}")
        print(f"  Leaderboard: https://huggingface.co/datasets/{leaderboard_repo}")

    elif args.output_format == "json":
        # Save results locally as JSON files
        from .utils import save_results_locally

        output_dir = save_results_locally(
            all_results,
            trace_data,
            metric_data,
            args.model,
            args.agent_type,
            dataset_used,
            args.output_dir,
        )

        print("\n[SUCCESS] Evaluation complete! Results saved locally.")
        print(f"  Output directory: {output_dir}")
        print("  - results.json")
        print("  - traces.json")
        print("  - metrics.json")
        print("  - leaderboard_row.json")
