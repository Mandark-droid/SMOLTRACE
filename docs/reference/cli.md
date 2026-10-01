# CLI Reference

The `smoltrace-eval` command runs agent evaluations. This page lists every flag. For narrative usage, see [Running Evaluations](../guides/running-evaluations.md).

!!! tip
    Dataset names (`results`, `traces`, `metrics`, `leaderboard`) are **automatically generated** from your HuggingFace username and a timestamp. You never need to specify repository names.

## Core Arguments

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--model` | Model ID (e.g. `mistral/mistral-small-latest`, `openai/gpt-4`) | **Required** | - |
| `--provider` | Model provider | `litellm` | `litellm`, `inference`, `transformers`, `ollama` |
| `--hf-token-file` | Read the HuggingFace credential from a file; preferred over a command-line value | None | - |
| `--hf-token` | HuggingFace token (or use `HF_TOKEN` env var) | From env | - |
| `--hf-inference-provider` | HF inference provider (for `--provider=inference`) | None | - |
| `--agent-type` | Agent type to evaluate | `both` | `tool`, `code`, `both` |

## Tool Configuration

| Flag | Description | Default |
|------|-------------|---------|
| `--enable-tools` | Enable optional smolagents tools (space-separated). See [Agent Tools](../guides/tools.md). | None |
| `--search-provider` | Web search provider for the `google_search` tool: `duckduckgo`, `serper` (`SERPER_API_KEY`), `brave` (`BRAVE_API_KEY`), `tavily` (`TAVILY_API_KEY`). A provider without its key stops the run (0.2.11) | `duckduckgo` |
| `--working-directory` | Working directory for file tools (restricts file operations) | Current dir |

## Task Configuration

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--difficulty` | Filter tasks by difficulty | All tasks | `easy`, `medium`, `hard` |
| `--dataset-name` | HF dataset for tasks | `kshitijthakkar/smoltrace-tasks` | Any HF dataset |
| `--dataset-revision` | Immutable commit SHA required for remote task datasets | None | - |
| `--split` | Dataset split to use | `train` | - |
| `--allow-test-fallback` | Developer-only fallback to built-in tasks after a load failure | `False` | - |

## Observability & Output

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--enable-otel` | Enable OpenTelemetry tracing/metrics | `False` | - |
| `--run-id` | Unique run identifier (UUID format) | Auto-generated | Any string |
| `--output-format` | Output destination | `hub` | `hub`, `json`, `opensearch` |
| `--output-dir` | Directory for JSON output (when `--output-format=json`) | `./smoltrace_results` | - |
| `--private` | Keep HuggingFace datasets private | `True` | - |
| `--public` | Explicitly publish prompts, responses, traces, and metrics publicly | `False` | - |
| `--disable-gpu-metrics` | Opt out of GPU metrics collection for local models | GPU metrics on for local models | - |
| `--use-case` | Normalized leaderboard use-case grouping | None | - |
| `--team` | Normalized leaderboard ownership grouping | None | - |
| `--purpose` | Leaderboard evaluation purpose | None | `selection`, `regression`, `monitoring` |
| `--suite-version` | Evaluated suite version | None | - |

## OpenSearch Configuration

Used with `--output-format=opensearch`. See [Output Formats](../guides/output-formats.md).

| Flag | Description | Default |
|------|-------------|---------|
| `--opensearch-url` | Full OpenSearch URL (overrides host/port/ssl) | None |
| `--opensearch-host` | OpenSearch host | `localhost` |
| `--opensearch-port` | OpenSearch port | `9200` |
| `--opensearch-user` | Username for basic auth | None |
| `--opensearch-password-file` | Read the OpenSearch credential from a file | None |
| `--opensearch-password` | Password for basic auth (also reads `OPENSEARCH_PASSWORD`) | None |
| `--opensearch-ssl` | Enable SSL/TLS | `False` |
| `--opensearch-no-verify-certs` | Skip SSL cert verification (dev/testing only) | `False` |
| `--opensearch-allow-insecure-remote` | Development-only remote plaintext/unverified override | `False` |
| `--opensearch-index-prefix` | Prefix for index names | `smoltrace` |

## Advanced Configuration

| Flag | Description | Default |
|------|-------------|---------|
| `--prompt-yml` | Path to a custom prompt configuration YAML | None |
| `--mcp-server-url` | Repeatable MCP URL; `name=URL` prefixes tools to prevent collisions | None |
| `--mcp-transport` | MCP transport selection | `auto` (`streamable-http`, `sse`) |
| `--additional-imports` | Additional Python modules for CodeAgent (space-separated) | None |
| `--trust-remote-code` | Permit custom Python shipped by a remote Transformers model | `False` |
| `--security-profile` | Runtime security policy | `standard` (`bfsi-closed`) |
| `--allow-local-code-execution` | Explicit acknowledgement for local CodeAgent execution | `False` |
| `--model-args` | `key=value` pairs handed to the agent as smolagents `additional_args` (task variables). They do **not** reach the model; use the generation flags below | None |
| `--temperature` | Sampling temperature (>= 0), sent to the model on every call (0.2.11) | Provider default |
| `--top-p` | Nucleus sampling, 0 < p <= 1 | Provider default |
| `--top-k` | Top-k sampling (>= 1) | Provider default |
| `--max-new-tokens` | Maximum tokens generated per model call | Provider default |
| `--reasoning-effort` | `none`, `minimal`, `low`, `medium`, `high`, for models with a reasoning control | Provider default |
| `--enable-thinking` | `true` / `false`: the chat-template thinking switch of open-weight models. A setting the provider cannot apply is printed as `[GENERATION] not applied for <provider>: ...`. See [SPEC v0.2.11](../SPEC_v0.2.11_GENERATION_SETTINGS_AND_SEARCH.md) | Provider default |
| `--parallel-workers` | Number of parallel workers (recommended: 8 for API models) | `1` |
| `--task-timeout` | Wall-clock limit per task in seconds; the task stops, the run continues (`0` = off). See [SPEC v0.2.6](../SPEC_v0.2.6_TIMEOUTS_AND_RUN_STATUS.md) | `300` |
| `--request-timeout` | Limit per model call in seconds, for clients that accept one (`0` = client default) | `120` |
| `--tool-timeout` | Limit per tool call in seconds; a call that does not answer becomes a tool error (`0` = off) | `120` |
| `--quiet` | Reduce output verbosity | `False` |
| `--debug` | Enable debug output | `False` |

## Other Commands

| Command | Purpose | Reference |
|---------|---------|-----------|
| `smoltrace-cleanup` | Manage/delete old evaluation datasets | [Dataset Management](../guides/dataset-management.md#cleanup-smoltrace-cleanup) |
| `smoltrace-copy-datasets` | Copy standard benchmark/tasks datasets to your account | [Dataset Management](../guides/dataset-management.md#copy-datasets-smoltrace-copy-datasets) |
