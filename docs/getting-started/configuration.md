# Configuration

SMOLTRACE is designed for **zero configuration** when publishing to the Hub.
Local JSON and OpenSearch output do not require a HuggingFace identity. Dataset
names are generated automatically from your HuggingFace username and a
timestamp when Hub output is selected.

## Environment Variables

Create a `.env` file (or export the variables in your shell).

### Hub output

| Variable | Purpose |
|----------|---------|
| `HF_TOKEN` | HuggingFace token — used for reading task datasets and pushing results/traces/metrics/leaderboard. |

Prefer `HF_TOKEN` or `--hf-token-file` over putting a credential directly in
the command line. Remote task datasets must also specify an immutable
`--dataset-revision`; local `.json` and `.jsonl` task files are parsed directly.

### Provider API Keys

At least one is required when using `--provider=litellm`. LiteLLM reads the standard provider keys:

| Variable | Provider |
|----------|----------|
| `MISTRAL_API_KEY` | Mistral |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GROQ_API_KEY` | Groq |
| `TOGETHER_API_KEY` | Together AI |

Additional providers supported by LiteLLM work the same way — see `.env.example` in the repository for the full list.

### Optional

| Variable | Purpose |
|----------|---------|
| `SERPER_API_KEY` | API key for `google_search` when using the `serper` search provider (see [Agent Tools](../guides/tools.md)). |
| `OPENSEARCH_PASSWORD` | Password for the OpenSearch exporter (alternative to `--opensearch-password`; see [Output Formats](../guides/output-formats.md)). |

## Security Profiles

The default `standard` profile supports the complete feature set. Use
`--security-profile bfsi-closed` for a fail-closed deployment policy. It rejects
Hub output, external model providers, MCP, optional network/system tools,
CodeAgent execution, remote model code, fallback tasks, and insecure remote
OpenSearch. Local task files and approved local model endpoints remain
available, and the run writes an effective-policy artifact for review.

## Auto-Generated Dataset Names

Every evaluation run generates dataset names automatically from your username and a timestamp:

- `{username}/smoltrace-results-{timestamp}`
- `{username}/smoltrace-traces-{timestamp}`
- `{username}/smoltrace-metrics-{timestamp}`
- `{username}/smoltrace-leaderboard` (persistent, updated each run)

You do not need to specify repository names on the command line.

## First-Time Dataset Setup

New users can copy the standard benchmark and tasks datasets into their own account so they can customize them and guarantee availability:

```bash
smoltrace-copy-datasets
```

See [Dataset Management](../guides/dataset-management.md) for options, and [Datasets](../guides/datasets.md) for a description of each dataset.

## Configuration Precedence

Most settings can be provided either as an environment variable or as a CLI flag. CLI flags take precedence. For example, the HuggingFace token is read from `--hf-token` if provided, otherwise from `HF_TOKEN`.

See the [CLI Reference](../reference/cli.md) for the complete list of flags.
