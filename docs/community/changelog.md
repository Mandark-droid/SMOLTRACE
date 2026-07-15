# Changelog

SMOLTRACE follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See the full changelog on GitHub: [changelog.md](https://github.com/Mandark-droid/SMOLTRACE/blob/main/changelog.md).

## Recent Highlights

- **0.0.15** — Relicensed from AGPL-3.0 to **Apache-2.0** (LICENSE, pyproject classifier, README badge, and generated HF dataset-card frontmatter updated to match).
- **0.0.14** — Added the **OpenSearch exporter** (`--output-format=opensearch`): creates OpenSearch indexes equivalent to the 4 HuggingFace datasets, with typed mappings, bulk indexing, and idempotent leaderboard upserts. Introduced the `smoltrace/exporters/` package with a `BaseExporter` abstraction. See [Output Formats](../guides/output-formats.md).

For the complete history, read [changelog.md on GitHub](https://github.com/Mandark-droid/SMOLTRACE/blob/main/changelog.md).
