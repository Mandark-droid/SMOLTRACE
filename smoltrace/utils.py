# smoltrace/utils.py
"""Utility functions for smoltrace, including Hugging Face Hub interactions and data processing."""

import json
import os
from datetime import datetime
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

    return {
        "utilization_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.utilization", [])),
        "utilization_max": safe_max(metrics_by_name.get("gen_ai.gpu.utilization", [])),
        "memory_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.memory.used", [])),
        "memory_max": safe_max(metrics_by_name.get("gen_ai.gpu.memory.used", [])),
        "temperature_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.temperature", [])),
        "temperature_max": safe_max(metrics_by_name.get("gen_ai.gpu.temperature", [])),
        "power_avg": safe_avg(metrics_by_name.get("gen_ai.gpu.power", [])),
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

    # Extract CO2 from aggregate metrics
    total_co2 = 0
    if isinstance(metric_data, dict) and "aggregates" in metric_data:
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

    # Aggregate GPU metrics from time-series data
    gpu_metrics = {}
    if isinstance(metric_data, dict) and "resourceMetrics" in metric_data:
        gpu_metrics = aggregate_gpu_metrics(metric_data["resourceMetrics"])

    # Get HF user info
    hf_token = os.getenv("HF_TOKEN")
    submitted_by = "unknown"
    if hf_token:
        try:
            user_info = get_hf_user_info(hf_token)
            if user_info:
                submitted_by = user_info.get("username", "unknown")
        except Exception:
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
        "evaluation_date": datetime.now().isoformat(),
        "submitted_by": submitted_by,
        # Dataset references
        "results_dataset": results_dataset,
        "traces_dataset": traces_dataset,
        "metrics_dataset": metrics_dataset,
        "dataset_used": dataset_used,
        # Aggregate statistics
        "num_tests": num_tests,
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
        "co2_emissions_g": round(total_co2, 4),
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
            flat_row = {
                "model": model_name,
                "evaluation_date": datetime.now().isoformat(),
                "test_id": res["test_id"],
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
                "enhanced_trace_info": json.dumps(res.get("enhanced_trace_info", {})),
            }
            flat_results.append(flat_row)
    return flat_results


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

    # Add Unix nanosecond timestamps for metrics filtering
    for result in flat_results:
        if "enhanced_trace_info" in result:
            try:
                trace_info = (
                    json.loads(result["enhanced_trace_info"])
                    if isinstance(result["enhanced_trace_info"], str)
                    else result["enhanced_trace_info"]
                )
                # Note: This would need start/end times from traces, skipping for now
                # In production, you'd extract from the matching trace
            except:
                pass

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

    # Push metrics dataset (OpenTelemetry resourceMetrics format)
    # ALWAYS create the metrics dataset, even if resourceMetrics is empty (for API models)
    if metric_data and isinstance(metric_data, dict):
        # Extract resourceMetrics for the dataset
        # Format: Single row with run_id and all time-series data
        if "resourceMetrics" in metric_data:
            metrics_row = {
                "run_id": metric_data.get("run_id", run_id),
                "resourceMetrics": metric_data[
                    "resourceMetrics"
                ],  # Can be empty list for API models
            }

            # Create dataset from single row (wrap in list)
            metrics_ds = Dataset.from_list([metrics_row])
            metrics_ds.push_to_hub(
                metrics_repo,
                private=private,
                commit_message=f"Metrics for {model_name} (run_id: {run_id})",
            )

            if metric_data["resourceMetrics"]:
                print(
                    f"[OK] Pushed {len(metric_data['resourceMetrics'])} GPU metric batches (run_id: {run_id}) to {metrics_repo}"
                )
            else:
                print(
                    f"[OK] Pushed empty metrics dataset (API model, run_id: {run_id}) to {metrics_repo}"
                )
        else:
            print(f"[WARNING] metric_data missing 'resourceMetrics' key, skipping metrics push")


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
