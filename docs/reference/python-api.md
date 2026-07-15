# Python API Reference

SMOLTRACE exposes its evaluation, dataset-management, and cleanup functions as a Python API. This page summarizes the public functions; see the [source on GitHub](https://github.com/Mandark-droid/SMOLTRACE/tree/main/smoltrace) for full signatures and the [Running Evaluations](../guides/running-evaluations.md) guide for worked examples.

## Evaluation Functions

**`run_evaluation(...)`** — the main evaluation function.

- Returns `(results_dict, traces_list, metrics_dict, dataset_name, run_id)`.
- Automatically handles dataset creation and the HuggingFace Hub push.
- Common parameters: `model`, `provider`, `agent_type`, `difficulty`, `enable_otel`, `enable_gpu_metrics`, `hf_token`, and more.

**`run_evaluation_flow(args)`** — CLI wrapper for `run_evaluation()` that handles argument parsing.

## Dataset Management Functions

**`generate_dataset_names(username)`** — auto-generates dataset names from a username and timestamp. Returns `(results_repo, traces_repo, metrics_repo, leaderboard_repo)`.

**`get_hf_user_info(token)`** — fetches HuggingFace user info from a token. Returns `{"username": str, "type": str, ...}`.

**`push_results_to_hf(...)`** — exports results, traces, and metrics to the HuggingFace Hub; creates 3 timestamped datasets automatically.

**`compute_leaderboard_row(...)`** — aggregates metrics into a leaderboard entry. Returns a dict with success rate, tokens, CO2, GPU stats, duration, cost, etc.

**`update_leaderboard(...)`** — appends a new row to the leaderboard dataset.

## Cleanup Functions

**`cleanup_datasets(...)`** — clean up old SMOLTRACE datasets from the HuggingFace Hub. Parameters include `older_than_days`, `keep_recent`, `incomplete_only`, `dry_run`, and more. See [Dataset Management](../guides/dataset-management.md).

**`discover_smoltrace_datasets(...)`** — discover all SMOLTRACE datasets for a user. Returns a dict categorized by type (results, traces, metrics, leaderboard).

**`group_datasets_by_run(...)`** — group datasets by evaluation run (timestamp). Returns a list of run dictionaries with completeness status.

**`filter_runs(...)`** — filter runs by age, count, or completeness. Returns `(runs_to_delete, runs_to_keep)`.

## Module Layout

The public API is spread across the `smoltrace` package:

| Module | Contents |
|--------|----------|
| `smoltrace.core` | `run_evaluation`, `run_evaluation_flow`, evaluation orchestration |
| `smoltrace.utils` | Dataset naming, HF user info, push helpers, leaderboard computation, `load_prompt_config` |
| `smoltrace.cleanup` | `cleanup_datasets` and discovery/grouping/filtering helpers |
| `smoltrace.copy_datasets` | Standard dataset copy command |
| `smoltrace.exporters` | `BaseExporter` abstraction and the OpenSearch exporter |
| `smoltrace.tools` | Custom and optional agent tools |
| `smoltrace.otel` | OpenTelemetry integration |
| `smoltrace.cards` | HuggingFace dataset card generation |

For the authoritative, up-to-date signatures, browse the [`smoltrace/` package on GitHub](https://github.com/Mandark-droid/SMOLTRACE/tree/main/smoltrace).
