# Datasets

SMOLTRACE provides three ready-to-use benchmark datasets, and supports fully custom task datasets loaded from HuggingFace or local JSON.

## Dataset Cards

### 1. Default Task Dataset — `kshitijthakkar/smoltrace-tasks`

Small dataset for quick validation and testing (used by default, no flag needed).

- **Size**: 13 test cases
- **Purpose**: Quick validation and testing
- **Difficulty**: Easy to medium
- **Coverage**: Weather queries, calculations, multi-step reasoning

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

### 2. Comprehensive Benchmark — `kshitijthakkar/smoltrace-benchmark-v1`

Large dataset for production evaluation and leaderboard comparison.

- **Size**: 132 test cases
- **Source**: Transformed from `smolagents/benchmark-v1`
- **Categories**:
    - **GAIA** (32 rows) — hard difficulty, complex multi-step reasoning
    - **Math** (50 rows) — medium difficulty, mathematical problem-solving
    - **SimpleQA** (50 rows) — easy difficulty, general knowledge questions

```bash
# Full benchmark (all 132 test cases)
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --agent-type both \
  --enable-otel

# Filter by difficulty
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --difficulty easy \
  --agent-type both \
  --enable-otel
```

### 3. Operations Benchmark — `kshitijthakkar/smoltrace-ops-benchmark`

Evaluates agentic capabilities for infrastructure operations and site reliability (APM/AIOps/SRE/DevOps).

- **Size**: 24 test cases
- **Categories**: Log Analysis (2), Metrics Monitoring (3), Configuration Management (3), Incident Response (3), Performance Optimization (3), Infrastructure Automation (3), Security & Compliance (3), Multi-Service Debugging (2), Cost Optimization (2)
- **Difficulty distribution**: Easy 4 (17%), Medium 11 (46%), Hard 9 (37%)
- **Required tools**: File system tools (`read_file`, `write_file`, `list_directory`, `search_files`), `python_interpreter`

#### Set Up Sample Data (Required)

The ops benchmark requires sample data files (logs, metrics, configs) to function. SMOLTRACE provides a setup script:

```bash
# Generate sample data in the default ops_sample directory
python setup_ops_sample_data.py

# Or generate in a custom directory
python setup_ops_sample_data.py my_custom_dir
```

This creates a realistic directory structure — `logs/`, `metrics/`, `config/`, `k8s/`, `deployments/`, `backups/`, `security/`, `billing/`, `storage/`, and `state/`. The generated `ops_sample` directory is git-ignored automatically.

#### Run the Ops Benchmark

```bash
# STEP 1: Generate sample data first (required!)
python setup_ops_sample_data.py

# STEP 2: Run the full ops benchmark (all 24 tasks)
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-ops-benchmark \
  --enable-tools read_file write_file list_directory search_files \
  --working-directory ./ops_sample \
  --agent-type both \
  --enable-otel
```

## Schema

All three datasets follow the same base schema:

| Field | Description |
|-------|-------------|
| `id` | Unique test identifier |
| `prompt` | Test question/task |
| `difficulty` | `easy`, `medium`, or `hard` |
| `agent_type` | `tool`, `code`, or `both` |
| `expected_tool` | Tool(s) that should be called |
| `expected_tool_calls` | Number of expected tool invocations |
| `expected_keywords` | (optional) Keywords to validate in the response |
| `category` | Test category (`gaia`/`math`/`simpleqa`/`log_analysis`/`metrics_monitoring`/…) |
| `required_tools` | (ops benchmark only) List of tools needed for the task |

## Recommendations

- Use `smoltrace-tasks` for quick testing and development.
- Use `smoltrace-benchmark-v1` for comprehensive general evaluation and leaderboard submissions.
- Use `smoltrace-ops-benchmark` for infrastructure operations and SRE/DevOps capability assessment.

## Custom Tasks

Create a JSON dataset with tasks:

```json
[
  {
    "id": "custom-tool-test",
    "prompt": "What's the weather in Tokyo?",
    "expected_tool": "get_weather",
    "difficulty": "easy",
    "agent_type": "tool",
    "expected_keywords": ["18°C", "Clear"]
  }
]
```

Push it to the Hub and load it in an evaluation:

```python
from datasets import Dataset
Dataset.from_list(tasks).push_to_hub("your-username/custom-tasks")
```

```bash
smoltrace-eval --dataset-name your-username/custom-tasks ...
```

To copy the standard datasets into your own account for customization, see [Dataset Management](dataset-management.md).
