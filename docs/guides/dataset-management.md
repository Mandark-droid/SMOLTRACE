# Dataset Management

Each evaluation creates three new timestamped datasets on the HuggingFace Hub (`results`, `traces`, `metrics`). Over many runs these accumulate, so SMOLTRACE ships two utilities: `smoltrace-cleanup` to remove old datasets safely, and `smoltrace-copy-datasets` to copy the standard benchmark/tasks datasets into your account.

## Cleanup — `smoltrace-cleanup`

### Quick Start

```bash
# Preview what would be deleted (safe, no actual deletion)
smoltrace-cleanup --older-than 7d

# Delete datasets older than 30 days
smoltrace-cleanup --older-than 30d --no-dry-run

# Keep only the 5 most recent evaluations
smoltrace-cleanup --keep-recent 5 --no-dry-run

# Delete incomplete runs (missing traces or metrics)
smoltrace-cleanup --incomplete-only --no-dry-run
```

### Options

| Flag | Description |
|------|-------------|
| `--older-than DAYS` | Delete datasets older than N days (e.g. `--older-than 7d`) |
| `--keep-recent N` | Keep only the N most recent evaluations |
| `--incomplete-only` | Delete only incomplete runs (missing datasets) |
| `--all` | Delete ALL SMOLTRACE datasets (⚠️ use with caution) |
| `--only TYPE` | Delete only a specific dataset type (e.g. `--only results`) |
| `--no-dry-run` | Actually delete (required for real deletion) |
| `--yes` | Skip confirmation prompts (for automation) |
| `--preserve-leaderboard` | Preserve the leaderboard dataset (default: true) |

### Safety Features

- **Dry-run by default** — shows what would be deleted without deleting.
- **Confirmation prompts** — requires typing `DELETE` to confirm.
- **Leaderboard protection** — never deletes your leaderboard by default.
- **Protected datasets** — benchmark and tasks datasets are never deleted.
- **Pattern matching** — only deletes datasets matching the exact SMOLTRACE naming patterns.
- **Error handling** — continues on errors and reports partial success.

### Protected Datasets (Never Deleted)

The following are permanently protected from every cleanup command (including `--all`):

- `{username}/smoltrace-benchmark-v1` — comprehensive benchmark (132 test cases)
- `{username}/smoltrace-tasks` — default tasks dataset (13 test cases)

When running cleanup you will see:

```
[INFO] Protected datasets (never deleted): smoltrace-benchmark-v1, smoltrace-tasks
```

### Python API

```python
from smoltrace import cleanup_datasets

# Preview deletion (dry-run)
result = cleanup_datasets(
    older_than_days=7,
    dry_run=True,
    hf_token="hf_...",
)
print(f"Would delete {result['total_deleted']} datasets from {result['total_scanned']} runs")

# Actual deletion, skipping confirmation
result = cleanup_datasets(
    older_than_days=30,
    dry_run=False,
    confirm=False,
    hf_token="hf_...",
)

# Keep only the N most recent evaluations
result = cleanup_datasets(keep_recent=5, dry_run=False, hf_token="hf_...")

# Delete incomplete runs
result = cleanup_datasets(incomplete_only=True, dry_run=False, hf_token="hf_...")
```

### Automation Example

```bash
#!/bin/bash
# cleanup_old_datasets.sh — delete datasets older than 30 days, keep leaderboard
smoltrace-cleanup \
  --older-than 30d \
  --no-dry-run \
  --yes \
  --preserve-leaderboard

exit $?
```

## Copy Datasets — `smoltrace-copy-datasets`

Copy the standard benchmark and tasks datasets from the main repository into your own HuggingFace account. Once copied, they are automatically protected from `smoltrace-cleanup`.

### Usage

```bash
# Copy both datasets (default)
smoltrace-copy-datasets

# Copy only the benchmark dataset
smoltrace-copy-datasets --only benchmark

# Copy only the tasks dataset
smoltrace-copy-datasets --only tasks

# Make copies private
smoltrace-copy-datasets --private

# Skip confirmation prompts (for automation)
smoltrace-copy-datasets --yes
```

### Options

| Flag | Description |
|------|-------------|
| `--only {benchmark,tasks}` | Copy only a specific dataset |
| `--private` | Make copied datasets private |
| `--yes`, `-y` | Skip confirmation prompts |
| `--source-user USER` | Source username (default: `kshitijthakkar`) |
| `--token TOKEN` | HuggingFace token |

### What Gets Copied

- **`smoltrace-benchmark-v1`** — 132 test cases (GAIA 32 hard, Math 50 medium, SimpleQA 50 easy). `kshitijthakkar/smoltrace-benchmark-v1` → `{your_username}/smoltrace-benchmark-v1`.
- **`smoltrace-tasks`** — 13 test cases, easy to medium. `kshitijthakkar/smoltrace-tasks` → `{your_username}/smoltrace-tasks`.

### Why Copy?

- **Customization** — modify datasets for your specific testing needs.
- **Availability** — ensure datasets remain accessible for your workflows.
- **Defaults** — set your copies as default datasets.
- **Version control** — maintain specific dataset versions for reproducibility.
- **Independence** — not affected by changes to the originals.
