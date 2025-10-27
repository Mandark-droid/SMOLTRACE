# SMOLTRACE Dataset Cleanup Utility Design

## Problem Statement

Each SMOLTRACE evaluation creates **3 new datasets**:
1. `{username}/smoltrace-results-{timestamp}`
2. `{username}/smoltrace-traces-{timestamp}`
3. `{username}/smoltrace-metrics-{timestamp}`

Plus optionally:
4. `{username}/smoltrace-leaderboard` (shared, updated with each run)

**Impact**: After 10 evaluations = 30 datasets cluttering the HuggingFace Hub!

## Design Requirements

### 1. Safety First
- ✅ **Dry-run mode** by default - show what would be deleted without deleting
- ✅ **Explicit confirmation** required before actual deletion
- ✅ **Preserve leaderboard** by default (it's shared across runs)
- ✅ **Pattern matching** to avoid deleting user's other datasets
- ✅ **Logging** of all actions for audit trail

### 2. Flexibility
- ✅ Delete by **date range** (e.g., older than 7 days)
- ✅ Delete by **run_id** (specific evaluation run)
- ✅ Delete **all SMOLTRACE datasets** (nuclear option)
- ✅ Keep **N most recent** evaluations
- ✅ Delete **incomplete runs** (missing traces or metrics)
- ✅ **Selective deletion** (e.g., only results, keep traces)

### 3. User Experience
- ✅ **Interactive mode** with confirmation prompts
- ✅ **Batch mode** for automation (--yes flag)
- ✅ **Summary report** before and after deletion
- ✅ **Progress indicators** for bulk operations
- ✅ **Error handling** with partial success reporting

### 4. Integration
- ✅ **CLI command**: `smoltrace-cleanup`
- ✅ **Python API**: `from smoltrace import cleanup_datasets`
- ✅ **Works with** HuggingFace token authentication
- ✅ **Respects** private/public dataset settings

## Proposed API

### CLI Interface

```bash
# Dry-run: Show what would be deleted (default behavior)
smoltrace-cleanup --dry-run

# Delete datasets older than 7 days
smoltrace-cleanup --older-than 7d

# Keep only the 5 most recent evaluations
smoltrace-cleanup --keep-recent 5

# Delete specific run by run_id
smoltrace-cleanup --run-id abc-123-def

# Delete all SMOLTRACE datasets (with confirmation)
smoltrace-cleanup --all

# Delete incomplete runs (missing traces or metrics)
smoltrace-cleanup --incomplete-only

# Delete only results datasets, keep traces and metrics
smoltrace-cleanup --only results --older-than 30d

# Batch mode (no confirmation, for automation)
smoltrace-cleanup --older-than 7d --yes

# Interactive mode with step-by-step confirmation
smoltrace-cleanup --interactive
```

### Python API

```python
from smoltrace import cleanup_datasets

# Dry-run (returns list of datasets that would be deleted)
datasets_to_delete = cleanup_datasets(
    dry_run=True,
    older_than_days=7,
    hf_token="hf_..."
)

# Actual deletion
result = cleanup_datasets(
    older_than_days=7,
    dry_run=False,
    confirm=False,  # Skip confirmation (use with caution!)
    hf_token="hf_..."
)

# Keep only N most recent
result = cleanup_datasets(
    keep_recent=5,
    dry_run=False,
    hf_token="hf_..."
)

# Delete specific run
result = cleanup_datasets(
    run_id="abc-123-def",
    dry_run=False,
    hf_token="hf_..."
)

# Delete incomplete runs
result = cleanup_datasets(
    incomplete_only=True,
    dry_run=False,
    hf_token="hf_..."
)
```

## Implementation Details

### Dataset Discovery

```python
def discover_smoltrace_datasets(username: str, hf_token: str) -> Dict[str, List[str]]:
    """
    Discovers all SMOLTRACE datasets for a user.

    Returns:
        {
            "results": ["user/smoltrace-results-20250115_120000", ...],
            "traces": ["user/smoltrace-traces-20250115_120000", ...],
            "metrics": ["user/smoltrace-metrics-20250115_120000", ...],
            "leaderboard": ["user/smoltrace-leaderboard"]
        }
    """
```

### Run Grouping

```python
def group_by_run(datasets: Dict) -> List[Dict]:
    """
    Groups datasets by timestamp (run).

    Returns:
        [
            {
                "timestamp": "20250115_120000",
                "results": "user/smoltrace-results-20250115_120000",
                "traces": "user/smoltrace-traces-20250115_120000",
                "metrics": "user/smoltrace-metrics-20250115_120000",
                "complete": True,  # Has all 3 datasets
                "created_at": datetime(...),
            },
            ...
        ]
    """
```

### Filtering

```python
def filter_datasets(
    runs: List[Dict],
    older_than_days: Optional[int] = None,
    keep_recent: Optional[int] = None,
    run_id: Optional[str] = None,
    incomplete_only: bool = False,
) -> List[Dict]:
    """Filters runs based on criteria."""
```

### Deletion

```python
def delete_datasets(
    datasets: List[str],
    dry_run: bool = True,
    hf_token: str = None,
) -> Dict:
    """
    Deletes datasets from HuggingFace Hub.

    Returns:
        {
            "deleted": ["dataset1", "dataset2", ...],
            "failed": [{"dataset": "dataset3", "error": "..."}],
            "skipped": ["leaderboard"],
            "total_size_freed_mb": 123.45,
        }
    """
```

## Safety Features

### 1. Dry-Run Mode (Default)

```python
# Default behavior - SAFE
result = cleanup_datasets(older_than_days=7)
# Output:
# [DRY-RUN] Would delete 6 datasets (2 runs):
#   Run 1 (2025-01-08):
#     - user/smoltrace-results-20250108_120000
#     - user/smoltrace-traces-20250108_120000
#     - user/smoltrace-metrics-20250108_120000
#   Run 2 (2025-01-09):
#     - user/smoltrace-results-20250109_150000
#     - user/smoltrace-traces-20250109_150000
#     - user/smoltrace-metrics-20250109_150000
#
# Total: 6 datasets, ~234.5 MB
#
# To actually delete, run with: dry_run=False
```

### 2. Confirmation Prompts

```python
# Interactive confirmation
result = cleanup_datasets(older_than_days=7, dry_run=False)
# Output:
# About to delete 6 datasets (2 runs):
#   [List of datasets...]
#
# This action CANNOT be undone!
# Type 'DELETE' to confirm: _
```

### 3. Leaderboard Protection

```python
# Leaderboard is NEVER deleted by default
result = cleanup_datasets(all=True)
# Output:
# Deleting all SMOLTRACE datasets...
# Skipped: user/smoltrace-leaderboard (protected)
#
# To also delete leaderboard, use: preserve_leaderboard=False
```

### 4. Pattern Matching Safety

```python
# Only matches exact SMOLTRACE naming patterns
SMOLTRACE_PATTERNS = [
    r"{username}/smoltrace-results-\d{8}_\d{6}",
    r"{username}/smoltrace-traces-\d{8}_\d{6}",
    r"{username}/smoltrace-metrics-\d{8}_\d{6}",
    r"{username}/smoltrace-leaderboard",
]

# Will NOT match:
# - user/my-smoltrace-custom-dataset
# - user/smoltrace-results (missing timestamp)
# - user/smoltrace-results-2025  (incomplete timestamp)
```

## CLI Implementation

```python
# smoltrace/cleanup.py

import argparse
from .utils import cleanup_datasets

def main():
    parser = argparse.ArgumentParser(
        description="Cleanup SMOLTRACE datasets from HuggingFace Hub"
    )

    # Filtering options
    parser.add_argument("--older-than", help="Delete datasets older than N days (e.g., 7d, 30d)")
    parser.add_argument("--keep-recent", type=int, help="Keep only N most recent evaluations")
    parser.add_argument("--run-id", help="Delete specific run by run_id")
    parser.add_argument("--incomplete-only", action="store_true", help="Delete only incomplete runs")
    parser.add_argument("--all", action="store_true", help="Delete all SMOLTRACE datasets")

    # Dataset type selection
    parser.add_argument("--only", choices=["results", "traces", "metrics"],
                       help="Delete only specific dataset type")

    # Safety options
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Show what would be deleted without deleting (default)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--preserve-leaderboard", action="store_true", default=True,
                       help="Preserve leaderboard dataset (default)")

    # Other options
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--token", help="HuggingFace token (or set HF_TOKEN env var)")

    args = parser.parse_args()

    # Execute cleanup
    result = cleanup_datasets(
        older_than=args.older_than,
        keep_recent=args.keep_recent,
        run_id=args.run_id,
        incomplete_only=args.incomplete_only,
        delete_all=args.all,
        only=args.only,
        dry_run=args.dry_run,
        confirm=not args.yes,
        preserve_leaderboard=args.preserve_leaderboard,
        interactive=args.interactive,
        hf_token=args.token,
    )

    print_cleanup_report(result)
```

## Output Examples

### Example 1: Dry-Run (Default)

```bash
$ smoltrace-cleanup --older-than 7d

╔══════════════════════════════════════════════════════════════╗
║           SMOLTRACE Dataset Cleanup (DRY-RUN)                ║
╚══════════════════════════════════════════════════════════════╝

Scanning datasets for user: kshitij

Found 15 SMOLTRACE datasets (5 runs):
  ✓ 5 complete runs (all 3 datasets present)
  ✗ 0 incomplete runs

Filter: Older than 7 days (before 2025-01-18)

Would delete 2 runs (6 datasets):

  Run #1: 2025-01-08 12:00:00
    📊 kshitij/smoltrace-results-20250108_120000 (1.2 MB)
    🔍 kshitij/smoltrace-traces-20250108_120000 (3.4 MB)
    📈 kshitij/smoltrace-metrics-20250108_120000 (0.8 MB)

  Run #2: 2025-01-10 15:30:00
    📊 kshitij/smoltrace-results-20250110_153000 (1.1 MB)
    🔍 kshitij/smoltrace-traces-20250110_153000 (3.2 MB)
    📈 kshitij/smoltrace-metrics-20250110_153000 (0.7 MB)

Would keep 3 runs (9 datasets):
  • 2025-01-20 10:00:00 (3 days ago)
  • 2025-01-22 14:30:00 (1 day ago)
  • 2025-01-23 09:15:00 (today)

Summary:
  • Total to delete: 6 datasets (2 runs)
  • Total size: ~10.4 MB
  • Leaderboard: Preserved ✓

This is a DRY-RUN. No datasets will be deleted.

To actually delete, run:
  smoltrace-cleanup --older-than 7d --no-dry-run --yes
```

### Example 2: Actual Deletion with Confirmation

```bash
$ smoltrace-cleanup --older-than 7d --no-dry-run

[... same scan output as above ...]

╔══════════════════════════════════════════════════════════════╗
║                      ⚠️  WARNING  ⚠️                          ║
╚══════════════════════════════════════════════════════════════╝

You are about to PERMANENTLY DELETE 6 datasets (2 runs).

This action CANNOT be undone!

Datasets to be deleted:
  1. kshitij/smoltrace-results-20250108_120000
  2. kshitij/smoltrace-traces-20250108_120000
  3. kshitij/smoltrace-metrics-20250108_120000
  4. kshitij/smoltrace-results-20250110_153000
  5. kshitij/smoltrace-traces-20250110_153000
  6. kshitij/smoltrace-metrics-20250110_153000

Type 'DELETE' to confirm (or Ctrl+C to cancel): DELETE

Deleting datasets...
  ✓ Deleted kshitij/smoltrace-results-20250108_120000 (1.2 MB)
  ✓ Deleted kshitij/smoltrace-traces-20250108_120000 (3.4 MB)
  ✓ Deleted kshitij/smoltrace-metrics-20250108_120000 (0.8 MB)
  ✓ Deleted kshitij/smoltrace-results-20250110_153000 (1.1 MB)
  ✓ Deleted kshitij/smoltrace-traces-20250110_153000 (3.2 MB)
  ✓ Deleted kshitij/smoltrace-metrics-20250110_153000 (0.7 MB)

╔══════════════════════════════════════════════════════════════╗
║                    Cleanup Complete ✓                        ║
╚══════════════════════════════════════════════════════════════╝

Summary:
  • Deleted: 6 datasets
  • Failed: 0 datasets
  • Skipped: 1 dataset (leaderboard)
  • Total space freed: 10.4 MB

Remaining SMOLTRACE datasets: 9 (3 runs)
```

### Example 3: Keep Recent

```bash
$ smoltrace-cleanup --keep-recent 3

Scanning datasets...

Found 5 runs. Keeping 3 most recent.

Would delete 2 runs (6 datasets):
  • 2025-01-08 12:00:00 (oldest)
  • 2025-01-10 15:30:00

Would keep 3 runs (9 datasets):
  • 2025-01-20 10:00:00
  • 2025-01-22 14:30:00
  • 2025-01-23 09:15:00 (newest)

[... rest of output ...]
```

## Error Handling

```python
# Partial success scenario
result = {
    "deleted": [
        "kshitij/smoltrace-results-20250108_120000",
        "kshitij/smoltrace-traces-20250108_120000",
    ],
    "failed": [
        {
            "dataset": "kshitij/smoltrace-metrics-20250108_120000",
            "error": "Repository not found (may have been deleted manually)"
        }
    ],
    "skipped": ["kshitij/smoltrace-leaderboard"],
}
```

## Integration with pyproject.toml

```toml
[project.scripts]
smoltrace-eval = "smoltrace.cli:main"
smoltrace-cleanup = "smoltrace.cleanup:main"  # NEW
```

## Testing Strategy

```python
# tests/test_cleanup.py

def test_discover_datasets(mock_hf_api):
    """Test dataset discovery."""
    datasets = discover_smoltrace_datasets("test_user", "token")
    assert "results" in datasets
    assert "traces" in datasets
    assert "metrics" in datasets

def test_group_by_run():
    """Test run grouping logic."""
    runs = group_by_run(datasets)
    assert len(runs) == 5
    assert runs[0]["complete"] == True

def test_filter_older_than():
    """Test date filtering."""
    filtered = filter_datasets(runs, older_than_days=7)
    assert len(filtered) == 2

def test_filter_keep_recent():
    """Test keep recent filtering."""
    filtered = filter_datasets(runs, keep_recent=3)
    assert len(filtered) == 2

def test_dry_run_no_deletion(mock_hf_api):
    """Test dry-run doesn't delete."""
    result = cleanup_datasets(older_than_days=7, dry_run=True)
    assert len(result["deleted"]) == 0
    mock_hf_api.delete_repo.assert_not_called()

def test_actual_deletion(mock_hf_api):
    """Test actual deletion."""
    result = cleanup_datasets(older_than_days=7, dry_run=False, confirm=False)
    assert len(result["deleted"]) == 6
    assert mock_hf_api.delete_repo.call_count == 6

def test_preserve_leaderboard(mock_hf_api):
    """Test leaderboard preservation."""
    result = cleanup_datasets(delete_all=True, preserve_leaderboard=True)
    assert "smoltrace-leaderboard" in result["skipped"]
```

## Documentation

Add to README.md:

```markdown
## Dataset Cleanup

SMOLTRACE creates 3 datasets per evaluation run. Use the cleanup utility to manage them:

### Quick Start

```bash
# Preview what would be deleted (safe, no actual deletion)
smoltrace-cleanup --older-than 7d

# Delete datasets older than 30 days
smoltrace-cleanup --older-than 30d --no-dry-run --yes

# Keep only 5 most recent evaluations
smoltrace-cleanup --keep-recent 5 --no-dry-run

# Delete incomplete runs (missing traces or metrics)
smoltrace-cleanup --incomplete-only --no-dry-run
```

### Python API

```python
from smoltrace import cleanup_datasets

# Preview deletion
result = cleanup_datasets(older_than_days=7, dry_run=True)

# Actual deletion
result = cleanup_datasets(
    older_than_days=30,
    dry_run=False,
    confirm=False,  # Skip confirmation
)
```

See `smoltrace-cleanup --help` for all options.
```

## Summary

**Features:**
- ✅ Safe dry-run mode by default
- ✅ Multiple filtering options (date, count, run_id, incomplete)
- ✅ Interactive and batch modes
- ✅ Leaderboard protection
- ✅ Detailed reports and progress
- ✅ Error handling with partial success
- ✅ CLI and Python API
- ✅ Comprehensive testing

**Safety:**
- ✅ Dry-run default
- ✅ Confirmation prompts
- ✅ Pattern matching to avoid accidents
- ✅ Audit logging
- ✅ Leaderboard never deleted by default

**UX:**
- ✅ Clear output with emojis and formatting
- ✅ Size information
- ✅ Before/after summaries
- ✅ Progress indicators
- ✅ Helpful error messages
