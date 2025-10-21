# smoltrace/utils.py
import yaml
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from huggingface_hub import login, HfApi
from datasets import load_dataset, Dataset

def get_hf_user_info(token: str) -> Optional[Dict]:
    api = HfApi(token=token)
    try:
        user_info = api.whoami()
        return {
            'username': user_info['name'],
            'type': user_info['type'],
            'fullname': user_info.get('fullname'),
            'email': user_info.get('email'),
            'avatar_url': user_info.get('avatarUrl'),
            'isPro': user_info.get('isPro', False),
            'canPay': user_info.get('canPay', False)
        }
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None

def generate_dataset_names(username: str) -> Tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_name = f"{username}/agent-eval-results-{timestamp}"
    leaderboard_name = f"{username}/agent-eval-leaderboard"
    return results_name, leaderboard_name

def load_prompt_config(prompt_file: Optional[str]) -> Optional[Dict]:
    if not prompt_file or not os.path.exists(prompt_file):
        return None
    try:
        with open(prompt_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading prompt config: {e}")
        return None

def compute_leaderboard_row(model_name: str, all_results: Dict[str, List[Dict]], trace_data: List[Dict], metric_data: List[Dict], dataset_used: str, results_dataset: str, agent_type: str = "both") -> Dict:
    results = all_results.get("tool", []) + all_results.get("code", [])
    if agent_type != "both":
        results = all_results.get(agent_type, [])
    num_tests = len(results)
    success_rate = sum(1 for r in results if r['success']) / num_tests * 100 if num_tests > 0 else 0
    avg_steps = sum(r['steps'] for r in results) / num_tests if num_tests > 0 else 0
    total_tokens = 0
    for t in trace_data:
        token_value = t.get("total_tokens", 0)
        if isinstance(token_value, str):
            try:
                token_value = int(token_value)
            except (ValueError, TypeError):
                token_value = 0
        elif not isinstance(token_value, (int, float)):
            token_value = 0
        total_tokens += token_value
    total_co2 = 0
    for m in metric_data:
        if m["name"] == "gen_ai.co2.emissions":
            for dp in m["data_points"]:
                value_dict = dp.get("value", {})
                value = value_dict.get("value", 0)
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = 0
                total_co2 += value
    return {"evaluation_date": datetime.now().isoformat(), "model": model_name, "agent_type": agent_type, "dataset_used": dataset_used, "results_dataset": results_dataset, "num_tests": num_tests, "success_rate": round(success_rate, 2), "avg_steps": round(avg_steps, 2), "total_tokens": total_tokens, "total_co2_g": round(total_co2, 4), "notes": f"Eval on {datetime.now().date()}; {len(trace_data)} traces"}

def update_leaderboard(leaderboard_repo: str, new_row: Dict, hf_token: Optional[str]):
    if not leaderboard_repo:
        print("No leaderboard repo; skipping update.")
        return
    token = hf_token or os.getenv("HF_TOKEN")
    if token:
        login(token)
    try:
        ds = load_dataset(leaderboard_repo, split="train")
        existing_data = [dict(row) for row in ds]
    except Exception as e:
        print(f"Creating new leaderboard: {e}")
        existing_data = []
    existing_data.append(new_row)
    new_ds = Dataset.from_list(existing_data)
    new_ds.push_to_hub(leaderboard_repo, split="train", commit_message=f"Update: {new_row['model']} {new_row['agent_type']}")
    print(f"✅ Updated leaderboard at {leaderboard_repo} (total rows: {len(existing_data)})")

def flatten_results_for_hf(all_results: Dict[str, List[Dict]], model_name: str) -> List[Dict[str, Any]]:
    flat_results = []
    for agent_type, results in all_results.items():
        for res in results:
            flat_row = {"model": model_name, "evaluation_date": datetime.now().isoformat(), "test_id": res["test_id"], "agent_type": res["agent_type"], "difficulty": res["difficulty"], "prompt": res["prompt"], "success": res["success"], "tool_called": res["tool_called"], "correct_tool": res["correct_tool"], "final_answer_called": res["final_answer_called"], "response_correct": res.get("response_correct"), "tools_used": res["tools_used"], "steps": res["steps"], "response": res["response"], "error": res.get("error"), "enhanced_trace_info": json.dumps(res.get("enhanced_trace_info", {}))}
            flat_results.append(flat_row)
    return flat_results

def push_results_to_hf(all_results: Dict, results_repo: str, model_name: str, hf_token: Optional[str], private: bool = False):
    if not results_repo:
        print("No results repo; skipping push.")
        return
    token = hf_token or os.getenv("HF_TOKEN")
    if token:
        login(token)
    flat_results = flatten_results_for_hf(all_results, model_name)
    results_ds = Dataset.from_list(flat_results)
    results_ds.push_to_hub(results_repo, private=private, commit_message=f"Eval results for {model_name}")
    print(f"✅ Pushed {len(flat_results)} results to {results_repo}")
