# smoltrace/utils.py
"""Utility functions for smoltrace, including Hugging Face Hub interactions and data processing."""

import json
import os
from datetime import datetime
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


def compute_leaderboard_row(
    model_name: str,
    all_results: Dict[str, List[Dict]],
    trace_data: List[Dict],
    metric_data: List[Dict],
    dataset_used: str,
    results_dataset: str,
    traces_dataset: str,
    metrics_dataset: str,
    agent_type: str = "both",
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

    total_co2 = 0
    for m in metric_data:
        if m["name"] == "gen_ai.co2.emissions":
            for dp in m["data_points"]:
                value_dict = dp.get("value", {})
                value = value_dict.get("value", 0)
                try:
                    value = float(value) if isinstance(value, str) else value
                except (ValueError, TypeError):
                    value = 0
                total_co2 += value

    return {
        "evaluation_date": datetime.now().isoformat(),
        "model": model_name,
        "agent_type": agent_type,
        "dataset_used": dataset_used,
        "results_dataset": results_dataset,
        "traces_dataset": traces_dataset,
        "metrics_dataset": metrics_dataset,
        "num_tests": num_tests,
        "success_rate": round(success_rate, 2),
        "avg_steps": round(avg_steps, 2),
        "avg_duration_ms": round(avg_duration_ms, 2),
        "total_duration_ms": round(total_duration_ms, 2),
        "total_tokens": total_tokens,
        "total_co2_g": round(total_co2, 4),
        "total_cost_usd": round(total_cost_usd, 6),
        "notes": f"Eval on {datetime.now().date()}; {len(trace_data)} traces",
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
    print(f"✅ Updated leaderboard at {leaderboard_repo} (total rows: {len(existing_data)})")


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
    metric_data: List[Dict],
    results_repo: str,
    traces_repo: str,
    metrics_repo: str,
    model_name: str,
    hf_token: Optional[str],
    private: bool = False,
):
    """Pushes consolidated evaluation results, traces, and metrics to Hugging Face Hub."""
    if not results_repo:
        print("No results repo; skipping push.")
        return

    token = hf_token or os.getenv("HF_TOKEN")
    if token:
        login(token)

    # Flatten results with enhanced info
    flat_results = flatten_results_for_hf(all_results, model_name)

    # Push results dataset
    results_ds = Dataset.from_list(flat_results)
    results_ds.push_to_hub(
        results_repo, private=private, commit_message=f"Eval results for {model_name}"
    )
    print(f"✅ Pushed {len(flat_results)} results to {results_repo}")

    # Push traces dataset
    if trace_data:
        traces_ds = Dataset.from_list(trace_data)
        traces_ds.push_to_hub(
            traces_repo, private=private, commit_message=f"Trace data for {model_name}"
        )
        print(f"✅ Pushed {len(trace_data)} traces to {traces_repo}")

    # Push metrics dataset
    if metric_data:
        metrics_ds = Dataset.from_list(metric_data)
        metrics_ds.push_to_hub(
            metrics_repo,
            private=private,
            commit_message=f"Metrics data for {model_name}",
        )
        print(f"✅ Pushed {len(metric_data)} metrics to {metrics_repo}")
