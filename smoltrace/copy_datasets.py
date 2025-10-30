#!/usr/bin/env python3
# smoltrace/copy_datasets.py
"""
CLI command for copying SMOLTRACE benchmark and tasks datasets to user's account.

This allows new users to get their own copy of the standard datasets:
- kshitijthakkar/smoltrace-benchmark-v1 → {username}/smoltrace-benchmark-v1
- kshitijthakkar/smoltrace-tasks → {username}/smoltrace-tasks

Usage:
    smoltrace-copy-datasets
    smoltrace-copy-datasets --private
    smoltrace-copy-datasets --only benchmark
"""

import argparse
import os
import sys

from .utils import copy_standard_datasets


def main():
    """Main entry point for smoltrace-copy-datasets CLI command."""
    parser = argparse.ArgumentParser(
        prog="smoltrace-copy-datasets",
        description="Copy SMOLTRACE benchmark and tasks datasets to your HuggingFace account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy both benchmark and tasks datasets (public)
  smoltrace-copy-datasets

  # Copy as private datasets
  smoltrace-copy-datasets --private

  # Copy only benchmark dataset
  smoltrace-copy-datasets --only benchmark

  # Copy only tasks dataset
  smoltrace-copy-datasets --only tasks

  # Skip confirmation prompt
  smoltrace-copy-datasets --yes

For more information, see: https://github.com/Mandark-droid/SMOLTRACE#dataset-setup
        """,
    )

    # Options
    parser.add_argument(
        "--only",
        choices=["benchmark", "tasks"],
        help="Copy only specific dataset (default: both)",
    )
    parser.add_argument(
        "--private", action="store_true", help="Make copied datasets private (default: public)"
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")
    parser.add_argument(
        "--source-user",
        type=str,
        default="kshitijthakkar",
        help="Source username to copy from (default: kshitijthakkar)",
    )
    parser.add_argument("--token", help="HuggingFace token (or set HF_TOKEN environment variable)")

    args = parser.parse_args()

    # Get token
    token = args.token or os.getenv("HF_TOKEN")
    if not token:
        print("Error: HuggingFace token required.")
        print("Either set HF_TOKEN environment variable or use --token argument.")
        sys.exit(1)

    # Execute copy
    try:
        result = copy_standard_datasets(
            source_user=args.source_user,
            only=args.only,
            private=args.private,
            confirm=not args.yes,
            hf_token=token,
        )

        # Exit code based on result
        if result["failed"]:
            sys.exit(1)  # Some copies failed
        else:
            sys.exit(0)  # Success

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
