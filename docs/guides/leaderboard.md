# Leaderboard

Every evaluation run aggregates its results into a leaderboard row and updates a persistent leaderboard dataset. This lets you compare models and agent types by success rate, efficiency, and environmental cost.

## Leaderboard Dataset

Each run updates `{username}/smoltrace-leaderboard` (on the HuggingFace Hub) or the `smoltrace-leaderboard` index (in OpenSearch). Community rankings are published at [huggingface.co/datasets/huggingface/smolagents-leaderboard](https://huggingface.co/datasets/huggingface/smolagents-leaderboard).

## Metrics Tracked

The leaderboard aggregates the following per model/agent-type:

| Column | Description |
|--------|-------------|
| Model | Model ID evaluated |
| Agent Type | `tool`, `code`, or `both` |
| Success Rate | Percentage of tasks passed |
| Avg Steps | Average agent steps per task |
| Avg Duration (ms) | Average per-task duration |
| Total Duration (ms) | Total run duration |
| Total Tokens | Prompt + completion tokens |
| CO2 (g) | Estimated CO2 emissions |
| Total Cost (USD) | Estimated cost |

Example rows:

| Model | Agent Type | Success Rate | Avg Steps | Avg Duration (ms) | Total Duration (ms) | Total Tokens | CO2 (g) | Total Cost (USD) |
|-------|------------|--------------|-----------|-------------------|---------------------|--------------|---------|------------------|
| mistral/mistral-large | both | 92.5% | 2.5 | 500.0 | 15000 | 15k | 0.22 | 0.005 |
| meta-llama/Llama-3.1-8B | tool | 88.0% | 2.1 | 450.0 | 12000 | 12k | 0.18 | 0.004 |

## How Rows Are Computed

The leaderboard row is produced by `compute_leaderboard_row(...)` and appended by `update_leaderboard(...)`. When running with the default Hub output, this happens automatically. For manual control, see the [Manual Dataset Management](running-evaluations.md#advanced-manual-dataset-management) example and the [Python API reference](../reference/python-api.md).

In OpenSearch, the leaderboard index uses `run_id` as the document ID, so re-running the same `run_id` upserts the row rather than duplicating it. See [Output Formats](output-formats.md).

## Contributing Runs

Run an evaluation with the comprehensive benchmark and push to the Hub to contribute your results:

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --agent-type both \
  --enable-otel
```
