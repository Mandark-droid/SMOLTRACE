# SMOLTRACE v0.1.0

SMOLTRACE 0.1.0 adds structured leaderboard grouping, multi-server MCP support,
and a substantial security and performance hardening pass.

## Highlights

- Group leaderboard runs with `use_case`, `team`, `purpose`, and
  `suite_version`; historical rows remain schema-compatible.
- Connect multiple MCP servers with repeatable `--mcp-server-url` arguments,
  optional `name=URL` tool prefixes, and automatic SSE/streamable-HTTP
  transport selection.
- Run local JSON/JSONL evaluations without HuggingFace authentication, including
  local Ollama workflows.
- Use the new `bfsi-closed` fail-closed profile to deny external providers,
  Hub publishing, MCP, optional network/system tools, CodeAgent, remote model
  code, fallback tasks, and insecure remote OpenSearch.
- Benefit from private-by-default Hub output, credential-file inputs, bounded
  and redacted OTEL attributes, safe arithmetic evaluation, SSRF/redirect
  defenses, immutable remote dataset revisions, and verified remote
  OpenSearch transport defaults.
- Use functional bounded parallel evaluation for API providers, shared model
  initialization across agent types, amortized GPU cleanup, single-pass trace
  indexing, and cheaper OpenSearch writes.
- Upgrade to `genai-otel-instrument>=1.6.1,<2.0.0` for the current tracing,
  privacy, security, and performance improvements.

## Compatibility and behavior changes

- Hub datasets are private unless `--public` is explicitly supplied.
- Remote HuggingFace task datasets require `--dataset-revision`.
- Transformers custom repository code is disabled unless
  `--trust-remote-code` is supplied.
- Remote OpenSearch requires authenticated, verified TLS unless the explicit
  development override is supplied. Loopback development remains supported.
- Dataset load failures stop the run unless the developer-only fallback flag is
  explicitly supplied.

## Validation status

- The main local suite passed with 569 tests and 6 skips at 88.58% coverage
  before the final run-ID propagation and dependency-floor edits.
- Black and Ruff passed that validated source snapshot.
- A wheel and source distribution were built and an installed-wheel Ollama run
  completed one tool evaluation successfully.
- GitHub release validation rebuilds and retests the final tagged source across
  the supported operating-system and Python matrix before publication.

The repository-internal security audit working document is intentionally not
included in this release.
