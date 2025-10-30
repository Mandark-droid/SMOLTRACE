# smoltrace/utils.py
"""Utility functions for smoltrace, including Hugging Face Hub interactions and data processing."""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml
from datasets import Dataset, load_dataset
from huggingface_hub import HfApi, login


def get_hf_user_info(token: str) -> Optional[Dict]:
    """Fetches user information from Hugging Face Hub using the provided token."""
    api = HfApi(token=token)
    try:
        user_info = api.whoami()
        return {
            "username": user_info["name"],
            "type": user_info["type"],
            "fullname": user_info.get("fullname"),
            "email": user_info.get("email"),
            "avatar_url": user_info.get("avatarUrl"),
            "isPro": user_info.get("isPro", False),
            "canPay": user_info.get("canPay", False),
        }
    except (
        ValueError,
        requests.exceptions.RequestException,
    ) as e:  # Catch specific exceptions
        print(f"Error fetching user info: {e}")
        return None


def generate_dataset_names(username: str) -> Tuple[str, str, str, str]:
    """Generates unique dataset names for results, traces, metrics, and the leaderboard."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_name = f"{username}/smoltrace-results-{timestamp}"
    traces_name = f"{username}/smoltrace-traces-{timestamp}"
    metrics_name = f"{username}/smoltrace-metrics-{timestamp}"
    leaderboard_name = f"{username}/smoltrace-leaderboard"
    return results_name, traces_name, metrics_name, leaderboard_name


def load_prompt_config(prompt_file: Optional[str]) -> Optional[Dict]:
    """Loads prompt configuration from a YAML file."""
    if not prompt_file or not os.path.exists(prompt_file):
        return None
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:  # Specify encoding
            return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:  # Catch specific exceptions
        print(f"Error loading prompt config: {e}")
        return None


def aggregate_gpu_metrics(resource_metrics: List[Dict]) -> Dict:
    """
    Aggregate GPU metrics from time-series data.

    Args:
        resource_metrics: List of resourceMetrics in OpenTelemetry format

    Returns:
        Dict with avg and max values for each GPU metric type
    """
    if not resource_metrics:
        return {
            "utilization_avg": None,
            "utilization_max": None,
            "memory_avg": None,
            "memory_max": None,
            "temperature_avg": None,
            "temperature_max": None,
            "power_avg": None,
            "co2_total": None,
            "power_cost_total": None,
        }

    # Extract all data points by metric name
    metrics_by_name = {}

    for rm in resource_metrics:
        for scope_metric in rm.get("scopeMetrics", []):
            for metric in scope_metric.get("metrics", []):
                metric_name = metric.get("name")
                data_points = []

                if "gauge" in metric:
                    data_points = metric["gauge"].get("dataPoints", [])
                elif "sum" in metric:
                    data_points = metric["sum"].get("dataPoints", [])

                if metric_name not in metrics_by_name:
                    metrics_by_name[metric_name] = []

                for dp in data_points:
                    value = None
                    if dp.get("asInt"):
                        value = int(dp["asInt"])
                    elif dp.get("asDouble") is not None:
                        value = float(dp["asDouble"])

                    if value is not None:
                        metrics_by_name[metric_name].append(value)

    # Compute aggregates
    def safe_avg(values):
        return sum(values) / len(values) if values else None

    def safe_max(values):
        return max(values) if values else None

    # For CO2 and cost, use max (cumulative metrics) instead of avg
    def safe_sum(values):
        return sum(values) if values else None

    return {
        "utilization_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.utilization", [])),
        "utilization_max": safe_max(metrics_by_name.get("gen_ai.gpu.utilization", [])),
        "memory_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.memory.used", [])),
        "memory_max": safe_max(metrics_by_name.get("gen_ai.gpu.memory.used", [])),
        "temperature_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.temperature", [])),
        "temperature_max": safe_max(metrics_by_name.get("gen_ai.gpu.temperature", [])),
        "power_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.power", [])),
        # CO2 and power cost are cumulative, use max (final value)
        "co2_total": safe_max(metrics_by_name.get("gen_ai.co2.emissions", [])),
        "power_cost_total": safe_max(metrics_by_name.get("gen_ai.power.cost", [])),
    }


def compute_leaderboard_row(
    model_name: str,
    all_results: Dict[str, List[Dict]],
    trace_data: List[Dict],
    metric_data: Dict,
    dataset_used: str,
    results_dataset: str,
    traces_dataset: str,
    metrics_dataset: str,
    agent_type: str = "both",
    run_id: str = None,
    provider: str = "litellm",
) -> Dict:
    """Computes a single row for the leaderboard dataset based on evaluation results, traces, and metrics."""
    results = all_results.get("tool", []) + all_results.get("code", [])
    if agent_type != "both":
        results = all_results.get(agent_type, [])

    num_tests = len(results)
    success_rate = sum(1 for r in results if r["success"]) / num_tests * 100 if num_tests > 0 else 0
    avg_steps = sum(r["steps"] for r in results) / num_tests if num_tests > 0 else 0

    total_tokens = 0
    total_duration_ms = 0
    total_cost_usd = 0.0
    for t in trace_data:
        token_value = t.get("total_tokens", 0)
        try:
            token_value = int(token_value) if isinstance(token_value, str) else token_value
        except (ValueError, TypeError):
            token_value = 0
        total_tokens += token_value

        duration_value = t.get("total_duration_ms", 0)
        try:
            duration_value = (
                float(duration_value) if isinstance(duration_value, str) else duration_value
            )
        except (ValueError, TypeError):
            duration_value = 0
        total_duration_ms += duration_value

        cost_value = t.get("total_cost_usd", 0.0)
        try:
            cost_value = float(cost_value) if isinstance(cost_value, str) else cost_value
        except (ValueError, TypeError):
            cost_value = 0.0
        total_cost_usd += cost_value

    avg_duration_ms = total_duration_ms / num_tests if num_tests > 0 else 0

    # Aggregate GPU metrics from time-series data (includes CO2 and power cost)
    gpu_metrics = {}
    if isinstance(metric_data, dict) and "resourceMetrics" in metric_data:
        gpu_metrics = aggregate_gpu_metrics(metric_data["resourceMetrics"])

    # Use GPU metrics CO2/cost if available, otherwise fall back to trace aggregates
    total_co2 = gpu_metrics.get("co2_total", 0)
    total_power_cost = gpu_metrics.get("power_cost_total", 0)

    # Fallback to aggregate metrics if GPU metrics not available
    if total_co2 == 0 and isinstance(metric_data, dict) and "aggregates" in metric_data:
        for m in metric_data["aggregates"]:
            if m.get("name") == "gen_ai.co2.emissions":
                for dp in m.get("data_points", []):
                    value_dict = dp.get("value", {})
                    value = value_dict.get("value", 0)
                    try:
                        value = float(value) if isinstance(value, str) else value
                    except (ValueError, TypeError):
                        value = 0
                    total_co2 += value

    # Get HF user info
    hf_token = os.getenv("HF_TOKEN")
    submitted_by = "unknown"
    if hf_token:
        try:
            user_info = get_hf_user_info(hf_token)
            if user_info:
                submitted_by = user_info.get("username", "unknown")
        except Exception:  # nosec B110
            # Silently ignore errors when fetching user info - not critical for leaderboard
            pass

    # Calculate additional stats
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = num_tests - successful_tests
    avg_tokens = total_tokens / num_tests if num_tests > 0 else 0
    avg_cost = total_cost_usd / num_tests if num_tests > 0 else 0

    return {
        # Identification
        "run_id": run_id,
        "model": model_name,
        "agent_type": agent_type,
        "provider": provider,
        "timestamp": datetime.now().isoformat(),  # Renamed from evaluation_date for UI consistency
        "submitted_by": submitted_by,
        # Dataset references
        "results_dataset": results_dataset,
        "traces_dataset": traces_dataset,
        "metrics_dataset": metrics_dataset,
        "dataset_used": dataset_used,
        # Aggregate statistics
        "total_tests": num_tests,  # Renamed from num_tests for UI consistency
        "successful_tests": successful_tests,
        "failed_tests": failed_tests,
        "success_rate": round(success_rate, 2),
        "avg_steps": round(avg_steps, 2),
        "avg_duration_ms": round(avg_duration_ms, 2),
        "total_duration_ms": round(total_duration_ms, 2),
        "total_tokens": total_tokens,
        "avg_tokens_per_test": int(avg_tokens),
        "total_cost_usd": round(total_cost_usd, 6),
        "avg_cost_per_test_usd": round(avg_cost, 6),
        # Environmental impact
        "co2_emissions_g": round(total_co2, 4) if total_co2 else 0,
        "power_cost_total_usd": round(total_power_cost, 6) if total_power_cost else 0,
        # GPU metrics (null for API models)
        "gpu_utilization_avg": (
            round(gpu_metrics["utilization_avg"], 2)
            if gpu_metrics.get("utilization_avg") is not None
            else None
        ),
        "gpu_utilization_max": (
            round(gpu_metrics["utilization_max"], 2)
            if gpu_metrics.get("utilization_max") is not None
            else None
        ),
        "gpu_memory_avg_mib": (
            round(gpu_metrics["memory_avg"], 2)
            if gpu_metrics.get("memory_avg") is not None
            else None
        ),
        "gpu_memory_max_mib": (
            round(gpu_metrics["memory_max"], 2)
            if gpu_metrics.get("memory_max") is not None
            else None
        ),
        "gpu_temperature_avg": (
            round(gpu_metrics["temperature_avg"], 2)
            if gpu_metrics.get("temperature_avg") is not None
            else None
        ),
        "gpu_temperature_max": (
            round(gpu_metrics["temperature_max"], 2)
            if gpu_metrics.get("temperature_max") is not None
            else None
        ),
        "gpu_power_avg_w": (
            round(gpu_metrics["power_avg"], 2) if gpu_metrics.get("power_avg") is not None else None
        ),
        # Metadata
        "notes": f"Evaluation on {datetime.now().strftime('%Y-%m-%d')}; {num_tests} tests",
    }


def update_leaderboard(leaderboard_repo: str, new_row: Dict, hf_token: Optional[str]):
    """Updates the leaderboard dataset on Hugging Face Hub with a new evaluation row."""
    if not leaderboard_repo:
        print("No leaderboard repo; skipping update.")
        return
    token = hf_token or os.getenv("HF_TOKEN")
    if token:
        login(token)
    try:
        ds = load_dataset(leaderboard_repo, split="train")
        existing_data = [dict(row) for row in ds]
    except (FileNotFoundError, ValueError) as e:  # Catch specific exceptions
        print(f"Creating new leaderboard: {e}")
        existing_data = []
    existing_data.append(new_row)
    new_ds = Dataset.from_list(existing_data)
    new_ds.push_to_hub(
        leaderboard_repo,
        split="train",
        commit_message=f"Update: {new_row['model']} {new_row['agent_type']}",
    )
    print(f"[OK] Updated leaderboard at {leaderboard_repo} (total rows: {len(existing_data)})")


def flatten_results_for_hf(
    all_results: Dict[str, List[Dict]], model_name: str
) -> List[Dict[str, Any]]:
    """Flattens the nested evaluation results into a list of dictionaries suitable for Hugging Face Dataset."""
    flat_results = []
    for (
        _,
        results,
    ) in all_results.items():  # Removed agent_type as it's not directly used here
        for res in results:
            # Extract enhanced trace info for top-level fields
            enhanced_info = res.get("enhanced_trace_info", {})
            if isinstance(enhanced_info, str):
                try:
                    enhanced_info = json.loads(enhanced_info)
                except (json.JSONDecodeError, TypeError):
                    enhanced_info = {}

            # Extract critical fields from enhanced_trace_info to top level
            trace_id = enhanced_info.get("trace_id")
            execution_time_ms = enhanced_info.get("duration_ms", 0)
            total_tokens = enhanced_info.get("total_tokens", 0)
            cost_usd = enhanced_info.get("cost_usd", 0.0)

            flat_row = {
                "model": model_name,
                "evaluation_date": datetime.now().isoformat(),
                "task_id": res["test_id"],  # Renamed from test_id for UI consistency
                "agent_type": res["agent_type"],
                "difficulty": res["difficulty"],
                "prompt": res["prompt"],
                "success": res["success"],
                "tool_called": res["tool_called"],
                "correct_tool": res["correct_tool"],
                "final_answer_called": res["final_answer_called"],
                "response_correct": res.get("response_correct"),
                "tools_used": res["tools_used"],
                "steps": res["steps"],
                "response": res["response"],
                "error": res.get("error"),
                # Top-level fields extracted from enhanced_trace_info (CRITICAL for UI)
                "trace_id": trace_id,
                "execution_time_ms": execution_time_ms,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                # Keep enhanced_trace_info for backward compatibility
                "enhanced_trace_info": json.dumps(res.get("enhanced_trace_info", {})),
            }
            flat_results.append(flat_row)
    return flat_results


def flatten_metrics_for_hf(metric_data: Dict) -> List[Dict[str, Any]]:
    """Flattens the nested OpenTelemetry metrics into a list of time-series rows suitable for dashboards.

    Args:
        metric_data: Dict containing run_id and resourceMetrics (OpenTelemetry format)

    Returns:
        List of flat dictionaries, each representing one timestamp with all metrics

    Example output format:
        [{
            "run_id": "uuid",
            "timestamp": "2025-10-27T11:28:15",
            "timestamp_unix_nano": "1761544695460017300",
            "gpu_id": "0",
            "gpu_name": "NVIDIA GeForce RTX 3060",
            "co2_emissions_gco2e": 0.036,
            "power_cost_usd": 9.19e-06,
            "gpu_utilization_percent": 0.0,
            "gpu_memory_used_mib": 375.07,
            "gpu_memory_total_mib": 6144.0,
            "gpu_temperature_celsius": 84.0,
            "gpu_power_watts": 18.741
        }, ...]
    """
    if not metric_data or "resourceMetrics" not in metric_data:
        return []

    run_id = metric_data.get("run_id", "unknown")
    resource_metrics = metric_data.get("resourceMetrics", [])

    flat_metrics = []

    for rm in resource_metrics:
        # Get resource attributes
        resource_attrs = {}
        if "resource" in rm and "attributes" in rm["resource"]:
            for attr in rm["resource"]["attributes"]:
                key = attr.get("key", "")
                # Extract value from the nested structure
                value_dict = attr.get("value", {})
                if value_dict:
                    # Get first non-None value from value dict
                    value = next((v for v in value_dict.values() if v is not None), None)
                    resource_attrs[key] = value

        # Get scope metrics
        if "scopeMetrics" not in rm:
            continue

        for sm in rm["scopeMetrics"]:
            if "metrics" not in sm:
                continue

            # Create a flat row for this timestamp with ALL expected columns initialized
            # This ensures all 13 columns exist even if some metrics have no data points yet
            flat_row = {
                "run_id": run_id,
                "service_name": resource_attrs.get("service.name", "unknown"),
                # Initialize ALL expected metric columns with defaults
                "co2_emissions_gco2e": 0.0,
                "power_cost_usd": 0.0,
                "gpu_utilization_percent": 0.0,
                "gpu_memory_used_mib": 0.0,
                "gpu_memory_total_mib": 0.0,
                "gpu_temperature_celsius": 0.0,
                "gpu_power_watts": 0.0,
            }

            # Process each metric
            for metric in sm["metrics"]:
                metric_name = metric.get("name", "")

                # Get data points
                data_points = []
                if metric.get("gauge") and metric["gauge"].get("dataPoints"):
                    data_points = metric["gauge"]["dataPoints"]
                elif metric.get("sum") and metric["sum"].get("dataPoints"):
                    data_points = metric["sum"]["dataPoints"]

                if not data_points:
                    # Metric has no data points yet (common for CO2/power cost at start)
                    # Column already initialized with default value above, so skip to next metric
                    continue

                # Process first data point (should only be one per timestamp)
                dp = data_points[0]

                # Get timestamp
                timestamp_ns = dp.get("timeUnixNano", "")
                if timestamp_ns:
                    timestamp_s = int(timestamp_ns) / 1e9
                    dt = datetime.fromtimestamp(timestamp_s)
                    flat_row["timestamp"] = dt.isoformat()
                    flat_row["timestamp_unix_nano"] = str(timestamp_ns)

                # Get value and ensure numeric type
                value = dp.get("asDouble")
                if value is None:
                    value = dp.get("asInt")
                if value is None:
                    value = 0

                # Convert to float for consistency
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = 0.0

                # Get attributes from data point (e.g., gpu_id, gpu_name)
                if "attributes" in dp:
                    for attr in dp["attributes"]:
                        key = attr.get("key", "")
                        value_dict = attr.get("value", {})
                        if value_dict:
                            attr_value = next(
                                (v for v in value_dict.values() if v is not None), None
                            )
                            flat_row[key] = attr_value

                # Map metric name to flat column name
                metric_mapping = {
                    "gen_ai.co2.emissions": "co2_emissions_gco2e",
                    "gen_ai.power.cost": "power_cost_usd",
                    "gen_ai.gpu.utilization": "gpu_utilization_percent",
                    "gen_ai.gpu.memory.used": "gpu_memory_used_mib",
                    "gen_ai.gpu.memory.total": "gpu_memory_total_mib",
                    "gen_ai.gpu.temperature": "gpu_temperature_celsius",
                    "gen_ai.gpu.power": "gpu_power_watts",
                }

                column_name = metric_mapping.get(metric_name, metric_name.replace(".", "_"))
                flat_row[column_name] = value

            # Add this timestamp row to results
            if "timestamp" in flat_row:  # Only add if we have a timestamp
                flat_metrics.append(flat_row)

    return flat_metrics


def push_results_to_hf(
    all_results: Dict,
    trace_data: List[Dict],
    metric_data: Dict,
    results_repo: str,
    traces_repo: str,
    metrics_repo: str,
    model_name: str,
    hf_token: Optional[str],
    private: bool = False,
    run_id: str = None,
):
    """Pushes consolidated evaluation results, traces, and metrics to Hugging Face Hub.

    Args:
        all_results: Dict of results by agent type
        trace_data: List of trace dictionaries
        metric_data: Dict containing run_id, resourceMetrics (GPU time-series), and aggregates
        results_repo: HuggingFace repo for results dataset
        traces_repo: HuggingFace repo for traces dataset
        metrics_repo: HuggingFace repo for metrics dataset
        model_name: Model identifier
        hf_token: HuggingFace authentication token
        private: Whether datasets should be private
        run_id: Unique run identifier
    """
    if not results_repo:
        print("No results repo; skipping push.")
        return

    token = hf_token or os.getenv("HF_TOKEN")
    if token:
        login(token)

    # Flatten results with enhanced info and add timestamps
    flat_results = flatten_results_for_hf(all_results, model_name)

    # Note: Unix nanosecond timestamps for metrics filtering could be added here
    # by extracting start/end times from the matching trace data

    # Push results dataset
    results_ds = Dataset.from_list(flat_results)
    results_ds.push_to_hub(
        results_repo,
        private=private,
        commit_message=f"Eval results for {model_name} (run_id: {run_id})",
    )
    print(f"[OK] Pushed {len(flat_results)} results to {results_repo}")

    # Push traces dataset
    if trace_data:
        traces_ds = Dataset.from_list(trace_data)
        traces_ds.push_to_hub(
            traces_repo,
            private=private,
            commit_message=f"Trace data for {model_name} (run_id: {run_id})",
        )
        print(f"[OK] Pushed {len(trace_data)} traces to {traces_repo}")

    # Push metrics dataset (flattened time-series format for easy dashboard use)
    # ALWAYS create the metrics dataset, even if resourceMetrics is empty (for API models)
    if metric_data and isinstance(metric_data, dict):
        # Flatten the nested OpenTelemetry format into time-series rows
        flat_metrics = flatten_metrics_for_hf(metric_data)

        if flat_metrics:
            # Create dataset from flattened metrics (multiple rows, one per timestamp)
            metrics_ds = Dataset.from_list(flat_metrics)
            metrics_ds.push_to_hub(
                metrics_repo,
                private=private,
                commit_message=f"Metrics for {model_name} (run_id: {run_id})",
            )
            print(
                f"[OK] Pushed {len(flat_metrics)} GPU metric time-series rows (run_id: {run_id}) to {metrics_repo}"
            )
        else:
            # For API models with no GPU metrics, create empty dataset with schema
            empty_metrics = [
                {
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(),
                    "service_name": "smoltrace-eval",
                    "gpu_id": None,
                    "gpu_name": None,
                    "co2_emissions_gco2e": 0.0,
                    "power_cost_usd": 0.0,
                    "gpu_utilization_percent": 0.0,
                    "gpu_memory_used_mib": 0.0,
                    "gpu_memory_total_mib": 0.0,
                    "gpu_temperature_celsius": 0.0,
                    "gpu_power_watts": 0.0,
                }
            ]
            metrics_ds = Dataset.from_list(empty_metrics)
            metrics_ds.push_to_hub(
                metrics_repo,
                private=private,
                commit_message=f"Empty metrics for API model {model_name} (run_id: {run_id})",
            )
            print(
                f"[OK] Pushed empty metrics dataset (API model, run_id: {run_id}) to {metrics_repo}"
            )


def save_results_locally(
    all_results: Dict,
    trace_data: List[Dict],
    metric_data: List[Dict],
    model_name: str,
    agent_type: str,
    dataset_used: str,
    output_dir: str = "./smoltrace_results",
) -> str:
    """Saves evaluation results, traces, and metrics as JSON files locally.

    Args:
        all_results: Dictionary of evaluation results by agent type
        trace_data: List of trace dictionaries
        metric_data: List of metric dictionaries
        model_name: Model identifier
        agent_type: Agent type used ("tool", "code", or "both")
        dataset_used: Dataset name used for evaluation
        output_dir: Base directory for output files

    Returns:
        Path to the output directory
    """
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = model_name.replace("/", "_").replace(":", "_")
    dir_name = f"{model_safe}_{agent_type}_{timestamp}"
    full_output_dir = Path(output_dir) / dir_name

    # Create directory
    full_output_dir.mkdir(parents=True, exist_ok=True)

    # Flatten results for JSON serialization
    flat_results = flatten_results_for_hf(all_results, model_name)

    # Save results.json
    results_path = full_output_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(flat_results, f, indent=2, default=str)
    print(f"[OK] Saved {len(flat_results)} results to {results_path}")

    # Save traces.json
    if trace_data:
        traces_path = full_output_dir / "traces.json"
        with open(traces_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2, default=str)
        print(f"[OK] Saved {len(trace_data)} traces to {traces_path}")

    # Save metrics.json
    if metric_data:
        metrics_path = full_output_dir / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metric_data, f, indent=2, default=str)
        print(f"[OK] Saved {len(metric_data)} metrics to {metrics_path}")

    # Compute and save leaderboard row
    leaderboard_row = compute_leaderboard_row(
        model_name=model_name,
        all_results=all_results,
        trace_data=trace_data,
        metric_data=metric_data,
        dataset_used=dataset_used,
        results_dataset=f"local:{results_path}",
        traces_dataset=f"local:{traces_path if trace_data else 'none'}",
        metrics_dataset=f"local:{metrics_path if metric_data else 'none'}",
        agent_type=agent_type,
    )

    leaderboard_path = full_output_dir / "leaderboard_row.json"
    with open(leaderboard_path, "w", encoding="utf-8") as f:
        json.dump(leaderboard_row, f, indent=2, default=str)
    print(f"[OK] Saved leaderboard row to {leaderboard_path}")

    # Save metadata
    metadata = {
        "model": model_name,
        "agent_type": agent_type,
        "dataset_used": dataset_used,
        "timestamp": timestamp,
        "num_results": len(flat_results),
        "num_traces": len(trace_data) if trace_data else 0,
        "num_metrics": len(metric_data) if metric_data else 0,
    }

    metadata_path = full_output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[OK] Saved metadata to {metadata_path}")

    return str(full_output_dir)


# ============================================================================
# Dataset Cleanup Functions
# ============================================================================


def discover_smoltrace_datasets(username: str, hf_token: str) -> Dict[str, List[Dict]]:
    """
    Discovers all SMOLTRACE datasets for a user on HuggingFace Hub.

    Protected datasets (NEVER included in cleanup):
    - {username}/smoltrace-benchmark-v1 (benchmark dataset)
    - {username}/smoltrace-tasks (default tasks dataset)

    Args:
        username: HuggingFace username
        hf_token: HuggingFace authentication token

    Returns:
        Dictionary with lists of datasets by type:
        {
            "results": [{"name": "user/smoltrace-results-...", "created_at": ...}, ...],
            "traces": [...],
            "metrics": [...],
            "leaderboard": [...]
        }
    """
    api = HfApi(token=hf_token)

    # Get all datasets for the user
    try:
        all_datasets = api.list_datasets(author=username)
    except Exception as e:
        print(f"Error listing datasets: {e}")
        return {"results": [], "traces": [], "metrics": [], "leaderboard": []}

    # Protected datasets that should NEVER be deleted
    PROTECTED_DATASETS = {
        f"{username}/smoltrace-benchmark-v1",
        f"{username}/smoltrace-tasks",
    }

    # Patterns for SMOLTRACE datasets
    patterns = {
        "results": re.compile(rf"^{re.escape(username)}/smoltrace-results-\d{{8}}_\d{{6}}$"),
        "traces": re.compile(rf"^{re.escape(username)}/smoltrace-traces-\d{{8}}_\d{{6}}$"),
        "metrics": re.compile(rf"^{re.escape(username)}/smoltrace-metrics-\d{{8}}_\d{{6}}$"),
        "leaderboard": re.compile(rf"^{re.escape(username)}/smoltrace-leaderboard$"),
    }

    # Categorize datasets
    discovered = {"results": [], "traces": [], "metrics": [], "leaderboard": []}

    for dataset in all_datasets:
        dataset_name = dataset.id

        # Skip protected datasets (benchmark and tasks datasets)
        if dataset_name in PROTECTED_DATASETS:
            continue

        for category, pattern in patterns.items():
            if pattern.match(dataset_name):
                discovered[category].append(
                    {
                        "name": dataset_name,
                        "created_at": (
                            dataset.created_at if hasattr(dataset, "created_at") else None
                        ),
                        "private": dataset.private if hasattr(dataset, "private") else False,
                    }
                )
                break

    print(
        f"[INFO] Discovered {len(discovered['results'])} results, "
        f"{len(discovered['traces'])} traces, "
        f"{len(discovered['metrics'])} metrics datasets"
    )
    print("[INFO] Protected datasets (never deleted): " "smoltrace-benchmark-v1, smoltrace-tasks")

    return discovered


def group_datasets_by_run(datasets: Dict[str, List[Dict]]) -> List[Dict]:
    """
    Groups datasets by timestamp (evaluation run).

    Args:
        datasets: Dictionary from discover_smoltrace_datasets()

    Returns:
        List of run dictionaries:
        [
            {
                "timestamp": "20250115_120000",
                "datetime": datetime(...),
                "results": "user/smoltrace-results-20250115_120000",
                "traces": "user/smoltrace-traces-20250115_120000",
                "metrics": "user/smoltrace-metrics-20250115_120000",
                "complete": True,  # Has all 3 datasets
            },
            ...
        ]
    """
    # Extract timestamps from dataset names
    timestamp_pattern = re.compile(r"(\d{8}_\d{6})$")

    runs = {}

    # Process results datasets
    for ds in datasets["results"]:
        match = timestamp_pattern.search(ds["name"])
        if match:
            timestamp = match.group(1)
            if timestamp not in runs:
                runs[timestamp] = {
                    "timestamp": timestamp,
                    "results": None,
                    "traces": None,
                    "metrics": None,
                }
            runs[timestamp]["results"] = ds["name"]

    # Process traces datasets
    for ds in datasets["traces"]:
        match = timestamp_pattern.search(ds["name"])
        if match:
            timestamp = match.group(1)
            if timestamp not in runs:
                runs[timestamp] = {
                    "timestamp": timestamp,
                    "results": None,
                    "traces": None,
                    "metrics": None,
                }
            runs[timestamp]["traces"] = ds["name"]

    # Process metrics datasets
    for ds in datasets["metrics"]:
        match = timestamp_pattern.search(ds["name"])
        if match:
            timestamp = match.group(1)
            if timestamp not in runs:
                runs[timestamp] = {
                    "timestamp": timestamp,
                    "results": None,
                    "traces": None,
                    "metrics": None,
                }
            runs[timestamp]["metrics"] = ds["name"]

    # Convert to list and add metadata
    run_list = []
    for timestamp, run_data in runs.items():
        # Parse timestamp
        try:
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        except ValueError:
            dt = None

        # Check completeness
        complete = all([run_data.get("results"), run_data.get("traces"), run_data.get("metrics")])

        run_list.append(
            {
                "timestamp": timestamp,
                "datetime": dt,
                "results": run_data.get("results"),
                "traces": run_data.get("traces"),
                "metrics": run_data.get("metrics"),
                "complete": complete,
            }
        )

    # Sort by datetime (newest first)
    run_list.sort(key=lambda x: x["datetime"] if x["datetime"] else datetime.min, reverse=True)

    print(
        f"[INFO] Grouped into {len(run_list)} runs "
        f"({sum(1 for r in run_list if r['complete'])} complete, "
        f"{sum(1 for r in run_list if not r['complete'])} incomplete)"
    )

    return run_list


def filter_runs(
    runs: List[Dict],
    older_than_days: Optional[int] = None,
    keep_recent: Optional[int] = None,
    incomplete_only: bool = False,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Filters runs based on criteria.

    Args:
        runs: List of run dictionaries from group_datasets_by_run()
        older_than_days: Keep only runs older than N days
        keep_recent: Keep only N most recent runs
        incomplete_only: Keep only incomplete runs (missing datasets)

    Returns:
        Tuple of (runs_to_delete, runs_to_keep)
    """
    to_delete = []
    to_keep = []

    # Filter by incomplete only
    if incomplete_only:
        to_delete = [r for r in runs if not r["complete"]]
        to_keep = [r for r in runs if r["complete"]]
        print(
            f"[INFO] Filter: Incomplete runs only → {len(to_delete)} to delete, {len(to_keep)} to keep"
        )
        return to_delete, to_keep

    # Filter by date
    if older_than_days is not None:
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        to_delete = [r for r in runs if r["datetime"] and r["datetime"] < cutoff_date]
        to_keep = [r for r in runs if r["datetime"] and r["datetime"] >= cutoff_date]
        print(
            f"[INFO] Filter: Older than {older_than_days} days (before {cutoff_date.strftime('%Y-%m-%d')}) "
            f"→ {len(to_delete)} to delete, {len(to_keep)} to keep"
        )
        return to_delete, to_keep

    # Filter by keep recent
    if keep_recent is not None:
        if len(runs) <= keep_recent:
            # Nothing to delete
            to_delete = []
            to_keep = runs
        else:
            # Keep the first N (newest), delete the rest
            to_keep = runs[:keep_recent]
            to_delete = runs[keep_recent:]
        print(
            f"[INFO] Filter: Keep {keep_recent} most recent → {len(to_delete)} to delete, {len(to_keep)} to keep"
        )
        return to_delete, to_keep

    # No filter applied
    return [], runs


def delete_datasets(
    datasets_to_delete: List[str],
    dry_run: bool = True,
    hf_token: Optional[str] = None,
) -> Dict:
    """
    Deletes datasets from HuggingFace Hub.

    Args:
        datasets_to_delete: List of dataset names to delete
        dry_run: If True, don't actually delete (default: True)
        hf_token: HuggingFace authentication token

    Returns:
        Dictionary with deletion results:
        {
            "deleted": ["dataset1", "dataset2", ...],
            "failed": [{"dataset": "dataset3", "error": "..."}],
            "total_count": 6,
        }
    """
    result = {
        "deleted": [],
        "failed": [],
        "total_count": len(datasets_to_delete),
    }

    if dry_run:
        print("[DRY-RUN] No datasets will be deleted")
        return result

    api = HfApi(token=hf_token)

    for dataset_name in datasets_to_delete:
        try:
            print(f"  Deleting {dataset_name}...", end=" ")
            api.delete_repo(repo_id=dataset_name, repo_type="dataset")
            result["deleted"].append(dataset_name)
            print("✓")
        except Exception as e:
            error_msg = str(e)
            result["failed"].append({"dataset": dataset_name, "error": error_msg})
            print(f"✗ Error: {error_msg}")

    return result


def cleanup_datasets(
    older_than_days: Optional[int] = None,
    keep_recent: Optional[int] = None,
    incomplete_only: bool = False,
    delete_all: bool = False,
    only: Optional[str] = None,  # "results", "traces", or "metrics"
    dry_run: bool = True,
    confirm: bool = True,
    preserve_leaderboard: bool = True,
    hf_token: Optional[str] = None,
) -> Dict:
    """
    Main cleanup function for SMOLTRACE datasets.

    Args:
        older_than_days: Delete datasets older than N days
        keep_recent: Keep only N most recent evaluations
        incomplete_only: Delete only incomplete runs (missing datasets)
        delete_all: Delete all SMOLTRACE datasets
        only: Delete only specific dataset type ("results", "traces", "metrics")
        dry_run: If True, show what would be deleted without deleting (default: True)
        confirm: If True, ask for confirmation before deleting (default: True)
        preserve_leaderboard: If True, never delete leaderboard (default: True)
        hf_token: HuggingFace authentication token

    Returns:
        Dictionary with cleanup results:
        {
            "deleted": [...],
            "failed": [...],
            "skipped": [...],
            "total_scanned": int,
            "total_deleted": int,
        }
    """
    token = hf_token or os.getenv("HF_TOKEN")
    if not token:
        raise ValueError(
            "HuggingFace token required. Set HF_TOKEN environment variable or pass hf_token parameter."
        )

    # Get user info
    user_info = get_hf_user_info(token)
    if not user_info:
        raise ValueError("Failed to get HuggingFace user info. Check your token.")

    username = user_info["username"]
    print(f"\n{'='*70}")
    print(f"  SMOLTRACE Dataset Cleanup {'(DRY-RUN)' if dry_run else ''}")
    print(f"{'='*70}\n")
    print(f"User: {username}")

    # Discover datasets
    print("\nScanning datasets...")
    datasets = discover_smoltrace_datasets(username, token)

    # Group by run
    runs = group_datasets_by_run(datasets)

    if len(runs) == 0:
        print("\n[INFO] No SMOLTRACE datasets found. Nothing to clean up.")
        return {"deleted": [], "failed": [], "skipped": [], "total_scanned": 0, "total_deleted": 0}

    # Filter runs
    if delete_all:
        runs_to_delete = runs
        runs_to_keep = []
    else:
        runs_to_delete, runs_to_keep = filter_runs(
            runs,
            older_than_days=older_than_days,
            keep_recent=keep_recent,
            incomplete_only=incomplete_only,
        )

    if len(runs_to_delete) == 0:
        print("\n[INFO] No datasets match the deletion criteria. Nothing to delete.")
        return {
            "deleted": [],
            "failed": [],
            "skipped": [],
            "total_scanned": len(runs),
            "total_deleted": 0,
        }

    # Collect datasets to delete
    datasets_to_delete = []
    for run in runs_to_delete:
        if only is None or only == "results":
            if run["results"]:
                datasets_to_delete.append(run["results"])
        if only is None or only == "traces":
            if run["traces"]:
                datasets_to_delete.append(run["traces"])
        if only is None or only == "metrics":
            if run["metrics"]:
                datasets_to_delete.append(run["metrics"])

    # Show summary
    print(f"\n{'='*70}")
    print("  Deletion Summary")
    print(f"{'='*70}\n")
    print(f"Runs to delete: {len(runs_to_delete)}")
    print(f"Datasets to delete: {len(datasets_to_delete)}")
    if runs_to_keep:
        print(f"Runs to keep: {len(runs_to_keep)}")
    if preserve_leaderboard:
        print("Leaderboard: Preserved [OK]")

    print("\nDatasets to delete:")
    for i, ds in enumerate(datasets_to_delete, 1):
        print(f"  {i}. {ds}")

    if dry_run:
        print(f"\n{'='*70}")
        print("  This is a DRY-RUN. No datasets will be deleted.")
        print(f"{'='*70}")
        print("\nTo actually delete, run with: dry_run=False")
        return {
            "deleted": [],
            "failed": [],
            "skipped": [],
            "total_scanned": len(runs),
            "total_deleted": 0,
        }

    # Confirmation
    if confirm:
        print(f"\n{'='*70}")
        print("  ⚠️  WARNING  ⚠️")
        print(f"{'='*70}")
        print(
            f"\nYou are about to PERMANENTLY DELETE {len(datasets_to_delete)} datasets ({len(runs_to_delete)} runs)."
        )
        print("\nThis action CANNOT be undone!")
        response = input("\nType 'DELETE' to confirm (or Ctrl+C to cancel): ")
        if response != "DELETE":
            print("\n[CANCELLED] No datasets were deleted.")
            return {
                "deleted": [],
                "failed": [],
                "skipped": [],
                "total_scanned": len(runs),
                "total_deleted": 0,
            }

    # Delete datasets
    print(f"\n{'='*70}")
    print("  Deleting Datasets...")
    print(f"{'='*70}\n")

    deletion_result = delete_datasets(datasets_to_delete, dry_run=False, hf_token=token)

    # Final summary
    print(f"\n{'='*70}")
    print("  Cleanup Complete ✓")
    print(f"{'='*70}\n")
    print(f"Deleted: {len(deletion_result['deleted'])} datasets")
    print(f"Failed: {len(deletion_result['failed'])} datasets")
    if preserve_leaderboard:
        print("Skipped: Leaderboard (preserved)")

    if deletion_result["failed"]:
        print("\nFailed deletions:")
        for failure in deletion_result["failed"]:
            print(f"  • {failure['dataset']}: {failure['error']}")

    print(f"\nRemaining SMOLTRACE datasets: {len(runs_to_keep)} runs")

    return {
        "deleted": deletion_result["deleted"],
        "failed": deletion_result["failed"],
        "skipped": ["leaderboard"] if preserve_leaderboard else [],
        "total_scanned": len(runs),
        "total_deleted": len(deletion_result["deleted"]),
    }


# ============================================================================
# Dataset Copy Functions
# ============================================================================


def copy_standard_datasets(
    source_user: str = "kshitijthakkar",
    only: Optional[str] = None,  # "benchmark" or "tasks"
    private: bool = False,
    confirm: bool = True,
    hf_token: Optional[str] = None,
) -> Dict:
    """
    Copy standard SMOLTRACE datasets to user's account.

    Copies:
    - {source_user}/smoltrace-benchmark-v1 → {username}/smoltrace-benchmark-v1
    - {source_user}/smoltrace-tasks → {username}/smoltrace-tasks

    Args:
        source_user: Source username to copy from (default: kshitijthakkar)
        only: Copy only specific dataset ("benchmark" or "tasks", default: both)
        private: Make copied datasets private (default: False)
        confirm: Ask for confirmation before copying (default: True)
        hf_token: HuggingFace authentication token

    Returns:
        Dictionary with copy results:
        {
            "copied": [...],
            "failed": [...],
            "skipped": [...],
        }
    """
    token = hf_token or os.getenv("HF_TOKEN")
    if not token:
        raise ValueError(
            "HuggingFace token required. Set HF_TOKEN environment variable or pass hf_token parameter."
        )

    # Get user info
    user_info = get_hf_user_info(token)
    if not user_info:
        raise ValueError("Failed to get HuggingFace user info. Check your token.")

    username = user_info["username"]

    print(f"\n{'='*70}")
    print("  SMOLTRACE Dataset Copy")
    print(f"{'='*70}\n")
    print(f"Source: {source_user}")
    print(f"Destination: {username}")
    print(f"Privacy: {'Private' if private else 'Public'}")

    # Determine which datasets to copy
    datasets_to_copy = []

    if only is None or only == "benchmark":
        datasets_to_copy.append(
            {
                "name": "smoltrace-benchmark-v1",
                "source": f"{source_user}/smoltrace-benchmark-v1",
                "destination": f"{username}/smoltrace-benchmark-v1",
                "description": "Comprehensive benchmark dataset (132 test cases)",
            }
        )

    if only is None or only == "tasks":
        datasets_to_copy.append(
            {
                "name": "smoltrace-tasks",
                "source": f"{source_user}/smoltrace-tasks",
                "destination": f"{username}/smoltrace-tasks",
                "description": "Default tasks dataset (13 test cases)",
            }
        )

    # Show what will be copied
    print(f"\n{'='*70}")
    print("  Datasets to Copy")
    print(f"{'='*70}\n")

    for i, ds in enumerate(datasets_to_copy, 1):
        print(f"{i}. {ds['name']}")
        print(f"   {ds['description']}")
        print(f"   {ds['source']} -> {ds['destination']}")
        print()

    # Check if datasets already exist
    print("Checking for existing datasets...")
    api = HfApi(token=token)
    existing = []

    for ds in datasets_to_copy:
        try:
            # Try to get dataset info
            api.dataset_info(ds["destination"], token=token)
            existing.append(ds["destination"])
            print(f"  [EXISTS] {ds['destination']}")
        except Exception:
            # Dataset doesn't exist - good to go
            print(f"  [NEW] {ds['destination']}")

    if existing:
        print(f"\n{'='*70}")
        print("  WARNING")
        print(f"{'='*70}")
        print("\nThe following datasets already exist in your account:")
        for ds_name in existing:
            print(f"  - {ds_name}")
        print("\nCopying will OVERWRITE these datasets!")

    # Confirmation
    if confirm:
        print(f"\n{'='*70}")
        print("  Confirmation")
        print(f"{'='*70}")
        print(f"\nYou are about to copy {len(datasets_to_copy)} dataset(s) to your account.")
        if existing:
            print(f"This will OVERWRITE {len(existing)} existing dataset(s).")

        response = input("\nType 'COPY' to confirm (or Ctrl+C to cancel): ")
        if response != "COPY":
            print("\n[CANCELLED] No datasets were copied.")
            return {"copied": [], "failed": [], "skipped": datasets_to_copy}

    # Copy datasets
    print(f"\n{'='*70}")
    print("  Copying Datasets...")
    print(f"{'='*70}\n")

    copied = []
    failed = []

    for ds in datasets_to_copy:
        print(f"Copying {ds['name']}...")
        try:
            # Load source dataset
            print(f"  [1/2] Loading from {ds['source']}...")
            source_ds = load_dataset(ds["source"], split="train", token=token)
            print(f"        Loaded {len(source_ds)} rows")

            # Push to destination
            print(f"  [2/2] Pushing to {ds['destination']}...")
            source_ds.push_to_hub(ds["destination"], token=token, private=private)
            print("        [OK] Copied successfully")

            copied.append(ds["destination"])

        except Exception as e:
            print(f"        [ERROR] Failed to copy: {e}")
            failed.append({"dataset": ds["destination"], "error": str(e)})

    # Summary
    print(f"\n{'='*70}")
    print("  Copy Summary")
    print(f"{'='*70}\n")

    if copied:
        print(f"[SUCCESS] Copied {len(copied)} dataset(s):")
        for ds_name in copied:
            print(f"  - {ds_name}")
            print(f"    URL: https://huggingface.co/datasets/{ds_name}")

    if failed:
        print(f"\n[FAILED] {len(failed)} dataset(s) failed:")
        for item in failed:
            print(f"  - {item['dataset']}: {item['error']}")

    print(f"\n{'='*70}")
    print("Next Steps:")
    print(f"{'='*70}")
    print("\n1. Verify datasets in your HuggingFace account")
    print("2. Run evaluations with your datasets:")
    print(f"   smoltrace-eval --model gpt-4 --dataset-name {username}/smoltrace-tasks")
    print(f"   smoltrace-eval --model gpt-4 --dataset-name {username}/smoltrace-benchmark-v1")

    return {"copied": copied, "failed": failed, "skipped": []}
