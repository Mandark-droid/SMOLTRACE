# smoltrace/cleanup.py
"""
CLI command for cleaning up SMOLTRACE datasets from HuggingFace Hub.

Usage:
    smoltrace-cleanup --dry-run
    smoltrace-cleanup --older-than 7 --no-dry-run
    smoltrace-cleanup --keep-recent 5 --no-dry-run
    smoltrace-cleanup --incomplete-only --no-dry-run
"""

import argparse
import os
import sys

from .utils import cleanup_datasets


def parse_older_than(value: str) -> int:
    """
    Parse --older-than argument.

    Supports formats:
    - "7d" or "7" → 7 days
    - "30d" → 30 days
    - "1w" → 7 days
    - "1m" → 30 days

    Args:
        value: String value to parse

    Returns:
        Number of days
    """
    value = value.strip().lower()

    # Handle "Nd" format
    if value.endswith("d"):
        return int(value[:-1])

    # Handle "Nw" format (weeks)
    if value.endswith("w"):
        return int(value[:-1]) * 7

    # Handle "Nm" format (months - approximate as 30 days)
    if value.endswith("m"):
        return int(value[:-1]) * 30

    # Handle just a number (assume days)
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid --older-than format: {value}. Use format like: 7d, 30d, 1w, 1m")


def main():
    """Main entry point for smoltrace-cleanup CLI command."""
    parser = argparse.ArgumentParser(
        prog="smoltrace-cleanup",
        description="Cleanup SMOLTRACE datasets from HuggingFace Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run: Show what would be deleted (safe, default)
  smoltrace-cleanup

  # Delete datasets older than 7 days
  smoltrace-cleanup --older-than 7d --no-dry-run

  # Keep only 5 most recent evaluations
  smoltrace-cleanup --keep-recent 5 --no-dry-run

  # Delete incomplete runs (missing traces or metrics)
  smoltrace-cleanup --incomplete-only --no-dry-run

  # Delete only results datasets, keep traces and metrics
  smoltrace-cleanup --only results --older-than 30d --no-dry-run

  # Batch mode (no confirmation, for automation)
  smoltrace-cleanup --older-than 7d --no-dry-run --yes

For more information, see: https://github.com/Mandark-droid/SMOLTRACE#dataset-cleanup
        """,
    )

    # Filtering options
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--older-than", type=str, help="Delete datasets older than N days (e.g., 7d, 30d, 1w, 1m)"
    )
    filter_group.add_argument(
        "--keep-recent",
        type=int,
        metavar="N",
        help="Keep only N most recent evaluations, delete the rest",
    )
    filter_group.add_argument(
        "--incomplete-only",
        action="store_true",
        help="Delete only incomplete runs (missing traces or metrics)",
    )
    filter_group.add_argument(
        "--all",
        action="store_true",
        help="Delete ALL SMOLTRACE datasets (use with extreme caution!)",
    )

    # Dataset type selection
    parser.add_argument(
        "--only",
        choices=["results", "traces", "metrics"],
        help="Delete only specific dataset type (default: all)",
    )

    # Safety options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be deleted without actually deleting (default: enabled unless --no-dry-run)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete datasets (required for real deletion)",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompts (use with caution!)"
    )
    parser.add_argument(
        "--preserve-leaderboard",
        action="store_true",
        default=True,
        help="Preserve leaderboard dataset (default: enabled)",
    )
    parser.add_argument(
        "--delete-leaderboard",
        action="store_true",
        help="Also delete leaderboard dataset (use with extreme caution!)",
    )

    # Other options
    parser.add_argument("--token", help="HuggingFace token (or set HF_TOKEN environment variable)")

    args = parser.parse_args()

    # Determine dry-run mode
    # Default is dry-run=True unless --no-dry-run is specified
    if args.no_dry_run:
        dry_run = False
    else:
        dry_run = True

    # Parse older_than if provided
    older_than_days = None
    if args.older_than:
        try:
            older_than_days = parse_older_than(args.older_than)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Check if at least one filter is provided (unless --all)
    if not any([args.older_than, args.keep_recent, args.incomplete_only, args.all]):
        print("Error: Please specify a filter option:")
        print("  --older-than DAYS")
        print("  --keep-recent N")
        print("  --incomplete-only")
        print("  --all")
        print("\nRun 'smoltrace-cleanup --help' for more information.")
        sys.exit(1)

    # Warn if --all is used
    if args.all and not dry_run:
        print("\n⚠️  WARNING: --all will delete ALL SMOLTRACE datasets!")
        print("This includes all results, traces, and metrics from all evaluation runs.")
        if not args.yes:
            response = input("Are you absolutely sure? Type 'YES DELETE ALL' to confirm: ")
            if response != "YES DELETE ALL":
                print("\n[CANCELLED] No datasets were deleted.")
                sys.exit(0)

    # Get token
    token = args.token or os.getenv("HF_TOKEN")
    if not token:
        print("Error: HuggingFace token required.")
        print("Either set HF_TOKEN environment variable or use --token argument.")
        sys.exit(1)

    # Execute cleanup
    try:
        result = cleanup_datasets(
            older_than_days=older_than_days,
            keep_recent=args.keep_recent,
            incomplete_only=args.incomplete_only,
            delete_all=args.all,
            only=args.only,
            dry_run=dry_run,
            confirm=not args.yes,  # Skip confirmation if --yes
            preserve_leaderboard=not args.delete_leaderboard,
            hf_token=token,
        )

        # Exit code based on result
        if result["failed"]:
            sys.exit(1)  # Some deletions failed
        else:
            sys.exit(0)  # Success

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
