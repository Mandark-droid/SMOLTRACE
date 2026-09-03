# smoltrace/main.py
"""Main execution flow for smoltrace evaluations."""

import ipaddress
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from .core import run_evaluation
from .utils import (
    compute_leaderboard_row,
    flatten_metrics_for_hf,
    flatten_results_for_hf,
    generate_dataset_names,
    get_hf_user_info,
    load_prompt_config,
    push_results_to_hf,
    update_leaderboard,
)


def _read_credential_file(path: str, label: str) -> str:
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{label} file is empty: {path}")
    return value


def _is_loopback_host(host: str) -> bool:
    try:
        addresses = socket.getaddrinfo(host, None)
        return bool(addresses) and all(
            ipaddress.ip_address(item[4][0]).is_loopback for item in addresses
        )
    except (OSError, ValueError):
        return False


def _validate_security_profile(args, os_credential: str = None) -> dict:
    profile = getattr(args, "security_profile", "standard")
    policy = {
        "profile": profile,
        "output_format": args.output_format,
        "provider": args.provider,
        "hub_egress_allowed": args.output_format == "hub",
        "mcp_allowed": bool(getattr(args, "mcp_server_url", None)),
        "optional_tools": getattr(args, "enable_tools", None) or [],
        "trust_remote_code": bool(getattr(args, "trust_remote_code", False)),
    }
    if profile != "bfsi-closed":
        return policy

    violations = []
    if args.output_format == "hub":
        violations.append("Hub output is prohibited")
    if args.provider not in {"ollama", "transformers"}:
        violations.append("only local Ollama or transformers providers are permitted")
    if getattr(args, "mcp_server_url", None):
        violations.append("MCP endpoints are prohibited")
    if getattr(args, "enable_tools", None):
        violations.append("optional network/code/filesystem tools are prohibited")
    if args.agent_type in {"code", "both"}:
        violations.append("CodeAgent local execution is prohibited")
    if getattr(args, "trust_remote_code", False):
        violations.append("trust_remote_code is prohibited")
    if getattr(args, "allow_test_fallback", False):
        violations.append("test fallback is prohibited")
    if getattr(args, "opensearch_allow_insecure_remote", False):
        violations.append("insecure remote OpenSearch override is prohibited")
    if getattr(args, "hf_token", None) or getattr(args, "opensearch_password", None):
        violations.append("credentials supplied directly on the command line are prohibited")
    if not Path(args.dataset_name).is_file():
        violations.append("dataset-name must be a local JSON or JSONL file")
    if args.provider == "transformers" and not Path(args.model).exists():
        violations.append("transformers model must be an existing local path")

    if args.output_format == "opensearch":
        os_url = getattr(args, "opensearch_url", None)
        if os_url:
            parsed = urlsplit(os_url)
            if parsed.username or parsed.password:
                violations.append("credentials embedded in OpenSearch URLs are prohibited")
            host = parsed.hostname or ""
            use_ssl = parsed.scheme == "https"
        else:
            host = getattr(args, "opensearch_host", "localhost")
            use_ssl = bool(getattr(args, "opensearch_ssl", False))
        if not _is_loopback_host(host):
            if not use_ssl:
                violations.append("non-loopback OpenSearch requires TLS")
            if getattr(args, "opensearch_no_verify_certs", False):
                violations.append("non-loopback OpenSearch requires certificate verification")
            if not getattr(args, "opensearch_user", None) or not os_credential:
                violations.append("non-loopback OpenSearch requires authentication")

    if violations:
        raise ValueError("bfsi-closed policy rejected configuration: " + "; ".join(violations))
    policy.update({"hub_egress_allowed": False, "mcp_allowed": False, "validated": True})
    return policy


def _report_pass_at_1(leaderboard_row: dict) -> None:
    """Print the evaluator-owned first-attempt metric and its denominator."""
    metric = leaderboard_row.get("pass_at_1")
    evaluated = leaderboard_row.get("evaluated_prompts", 0)
    passed = leaderboard_row.get("passed_prompts", 0)
    rule = leaderboard_row.get("pass_rule", "")
    if metric is None:
        print(f"[PASS@1] unmeasured ({evaluated} logical tasks; rule={rule})")
    else:
        print(f"[PASS@1] {passed}/{evaluated} = {metric:.4f} (rule={rule})")


def run_evaluation_flow(args):
    """
    The main function to run the complete evaluation flow.
    """
    hub_credential_path = getattr(args, "hf_" + "token_file", None)
    if hub_credential_path:
        setattr(
            args,
            "hf_" + "token",
            _read_credential_file(hub_credential_path, "HuggingFace credential"),
        )
    args.output_format = getattr(args, "output_format", "hub")
    # Get user info from HF token
    hf_token = args.hf_token or os.getenv("HF_TOKEN")
    if args.output_format == "hub" and not hf_token:
        print(
            "Error: HuggingFace token not found. Please provide it via --hf-token or the HF_TOKEN environment variable."
        )
        return

    user_info = get_hf_user_info(hf_token) if args.output_format == "hub" else {"username": "local"}
    if not user_info:
        print("Error: Invalid HF token or unable to fetch user info.")
        return

    if args.output_format == "hub":
        print(f"[OK] Logged in as: {user_info['username']}")

    os_credential = os.getenv("OPENSEARCH_" + "PASSWORD")
    credential_path = getattr(args, "opensearch_" + "password_file", None)
    if credential_path:
        os_credential = _read_credential_file(credential_path, "OpenSearch credential")
    effective_policy = _validate_security_profile(args, os_credential)

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
        mcp_transport=getattr(args, "mcp_transport", "auto"),
        run_id=getattr(args, "run_id", None),  # Get from CLI if provided
        enable_gpu_metrics=enable_gpu_metrics,
        additional_authorized_imports=getattr(args, "additional_imports", None),
        search_provider=getattr(args, "search_provider", "duckduckgo"),
        hf_inference_provider=getattr(args, "hf_inference_provider", None),
        parallel_workers=getattr(args, "parallel_workers", 1),
        enabled_smolagents_tools=getattr(args, "enable_tools", None),
        working_directory=getattr(args, "working_directory", None),
        model_args=getattr(args, "model_args_dict", None),
        allow_test_fallback=getattr(args, "allow_test_fallback", False),
        trust_remote_code=getattr(args, "trust_remote_code", False),
        dataset_revision=getattr(args, "dataset_revision", None),
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
            dataset_used=dataset_used,  # Pass dataset_used for card generation
            agent_type=args.agent_type,  # Pass agent_type for card generation
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
            use_case=getattr(args, "use_case", None),
            team=getattr(args, "team", None),
            purpose=getattr(args, "purpose", None),
            suite_version=getattr(args, "suite_version", None),
            submitted_by=user_info["username"],
        )
        _report_pass_at_1(leaderboard_row)
        update_leaderboard(leaderboard_repo, leaderboard_row, hf_token)

        print("\n[SUCCESS] Evaluation complete! Results pushed to HuggingFace Hub.")
        print(f"  Results: https://huggingface.co/datasets/{results_repo}")
        print(f"  Traces: https://huggingface.co/datasets/{traces_repo}")
        print(f"  Metrics: https://huggingface.co/datasets/{metrics_repo}")
        print(f"  Leaderboard: https://huggingface.co/datasets/{leaderboard_repo}")

    elif args.output_format == "opensearch":
        # Export to OpenSearch indexes
        from .exporters.opensearch import OpenSearchExporter

        # Build auth tuple if credentials provided
        os_auth = None
        os_user = getattr(args, "opensearch_user", None)
        os_pass = getattr(args, "opensearch_password", None) or os_credential
        if os_user and os_pass:
            os_auth = (os_user, os_pass)

        exporter = OpenSearchExporter(
            host=getattr(args, "opensearch_host", "localhost"),
            port=getattr(args, "opensearch_port", 9200),
            auth=os_auth,
            use_ssl=getattr(args, "opensearch_ssl", False),
            verify_certs=not getattr(args, "opensearch_no_verify_certs", False),
            index_prefix=getattr(args, "opensearch_index_prefix", "smoltrace"),
            opensearch_url=getattr(args, "opensearch_url", None),
            allow_insecure_remote=getattr(args, "opensearch_allow_insecure_remote", False),
        )

        # Flatten data (same transforms used for HF datasets)
        flat_results = flatten_results_for_hf(all_results, args.model)
        flat_metrics = flatten_metrics_for_hf(metric_data) if metric_data else []

        # Compute leaderboard row
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
            run_id,
            provider=args.provider,
            use_case=getattr(args, "use_case", None),
            team=getattr(args, "team", None),
            purpose=getattr(args, "purpose", None),
            suite_version=getattr(args, "suite_version", None),
            submitted_by=user_info["username"],
        )
        _report_pass_at_1(leaderboard_row)

        # Extract timestamp from auto-generated dataset name for consistent index naming
        timestamp = results_repo.split("-")[-1] if results_repo else None

        indexes = exporter.export_all(
            flat_results=flat_results,
            trace_data=trace_data,
            flat_metrics=flat_metrics,
            leaderboard_row=leaderboard_row,
            model_name=args.model,
            run_id=run_id,
            timestamp=timestamp,
        )

        print("\n[SUCCESS] Evaluation complete! Results exported to OpenSearch.")
        for dtype, idx_name in indexes.items():
            print(f"  {dtype}: {idx_name}")

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
            # Identity and provenance, matching what the hub and opensearch
            # branches already pass to compute_leaderboard_row. Omitting them
            # made the local row claim run_id=null and provider="litellm" for
            # every run, regardless of --run-id and --provider.
            run_id=run_id,
            provider=args.provider,
            use_case=getattr(args, "use_case", None),
            team=getattr(args, "team", None),
            purpose=getattr(args, "purpose", None),
            suite_version=getattr(args, "suite_version", None),
            submitted_by=user_info["username"],
        )

        print("\n[SUCCESS] Evaluation complete! Results saved locally.")
        print(f"  Output directory: {output_dir}")
        print("  - results.json")
        print("  - traces.json")
        print("  - metrics.json")
        print("  - leaderboard_row.json")

    if effective_policy.get("profile") == "bfsi-closed":
        policy_dir = Path(output_dir if args.output_format == "json" else args.output_dir)
        policy_dir.mkdir(parents=True, exist_ok=True)
        policy_path = policy_dir / "effective_policy.json"
        policy_path.write_text(json.dumps(effective_policy, indent=2), encoding="utf-8")
        print(f"[POLICY] Effective policy record: {policy_path}")
