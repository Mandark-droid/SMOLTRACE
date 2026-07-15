# Output Formats

Choose where evaluation data goes with `--output-format`: the HuggingFace Hub (default), local JSON files, or OpenSearch.

| `--output-format` | Destination |
|-------------------|-------------|
| `hub` (default) | HuggingFace Hub — 4 datasets (results, traces, metrics, leaderboard) |
| `json` | Local directory — 5 JSON files |
| `opensearch` | OpenSearch — 4 indexes mirroring the HF datasets |

## HuggingFace Hub (default)

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

Creates and pushes four datasets:

- `{username}/smoltrace-results-{timestamp}` — test case results
- `{username}/smoltrace-traces-{timestamp}` — OpenTelemetry traces
- `{username}/smoltrace-metrics-{timestamp}` — GPU metrics time-series
- `{username}/smoltrace-leaderboard` — aggregate leaderboard (updated each run)

Use `--private` to make the datasets private.

## Local JSON

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format json \
  --output-dir ./my_results
```

Creates a timestamped directory with five files:

- `results.json` — test case results
- `traces.json` — OpenTelemetry traces
- `metrics.json` — aggregated metrics
- `leaderboard_row.json` — leaderboard entry
- `metadata.json` — run metadata

## OpenSearch Exporter

Export evaluation data to OpenSearch indexes equivalent to the four HuggingFace datasets, enabling the same drill-down navigation (leaderboard → results → traces with metrics overlay). Requires the OpenSearch extra:

```bash
pip install smoltrace[opensearch]
```

### Basic Usage

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format opensearch \
  --opensearch-host localhost \
  --opensearch-port 9200
```

This creates 4 indexes mirroring the HF dataset structure:

- `smoltrace-results-{timestamp}` — test case results
- `smoltrace-traces-{timestamp}` — OpenTelemetry traces with nested spans
- `smoltrace-metrics-{timestamp}` — GPU metrics time-series
- `smoltrace-leaderboard` — aggregate leaderboard (persistent, upserted by `run_id`)

### Authenticated / Remote Clusters

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --output-format opensearch \
  --opensearch-url https://search-my-domain.us-east-1.es.amazonaws.com \
  --opensearch-user admin \
  --opensearch-password $OPENSEARCH_PASSWORD \
  --opensearch-index-prefix myproject
```

### OpenSearch Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--opensearch-url` | Full OpenSearch URL (overrides host/port/ssl, e.g. an AWS endpoint) | None |
| `--opensearch-host` | OpenSearch host | `localhost` |
| `--opensearch-port` | OpenSearch port | `9200` |
| `--opensearch-user` | Username for basic auth | None |
| `--opensearch-password` | Password for basic auth (also reads `OPENSEARCH_PASSWORD`) | None |
| `--opensearch-ssl` | Enable SSL/TLS | `False` |
| `--opensearch-no-verify-certs` | Skip SSL certificate verification (dev/testing only) | `False` |
| `--opensearch-index-prefix` | Prefix for index names (e.g. `myproject` → `myproject-results-*`) | `smoltrace` |

### How It Works

The OpenSearch exporter is part of the `smoltrace/exporters/` package, which is built on a `BaseExporter` abstraction so additional backends can be added in the future. Key properties:

- **Typed mappings** — each of the 4 index types has an OpenSearch mapping with proper field types (keyword, text, nested, float, date, etc.).
- **Bulk indexing** — efficient bulk document indexing via `opensearch-py` helpers.
- **Idempotent leaderboard** — the leaderboard index uses `run_id` as the document ID, so re-runs upsert rather than duplicate.
- **Cross-index navigation** — leaderboard documents store `results_index`, `traces_index`, and `metrics_index` references, parallel to the HF dataset references.
