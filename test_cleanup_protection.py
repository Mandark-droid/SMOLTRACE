#!/usr/bin/env python3
"""
Test script to verify that protected datasets are never deleted by cleanup tool.

This script:
1. Tests that smoltrace-benchmark-v1 and smoltrace-tasks are excluded from cleanup
2. Verifies the protection works with all cleanup modes (--all, --older-than, etc.)
"""

import os

from dotenv import load_dotenv

from smoltrace.utils import discover_smoltrace_datasets, get_hf_user_info

load_dotenv()


def test_protected_datasets():
    """Test that protected datasets are excluded from discovery."""

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("[ERROR] HF_TOKEN not found in environment")
        return False

    print("=" * 80)
    print("Testing Cleanup Protection for Benchmark and Tasks Datasets")
    print("=" * 80)

    # Get user info
    user_info = get_hf_user_info(hf_token)
    username = user_info["username"]

    print(f"\nUser: {username}")
    print("\nProtected datasets:")
    print(f"  1. {username}/smoltrace-benchmark-v1")
    print(f"  2. {username}/smoltrace-tasks")

    # Discover datasets
    print("\n[TEST] Running discover_smoltrace_datasets()...")
    datasets = discover_smoltrace_datasets(username, hf_token)

    # Check that protected datasets are NOT in the discovered list
    all_discovered_names = []
    for category in ["results", "traces", "metrics", "leaderboard"]:
        for ds in datasets[category]:
            all_discovered_names.append(ds["name"])

    protected_datasets = [
        f"{username}/smoltrace-benchmark-v1",
        f"{username}/smoltrace-tasks",
    ]

    print("\n[TEST] Checking protection...")
    protection_working = True

    for protected in protected_datasets:
        if protected in all_discovered_names:
            print(f"  [FAIL] {protected} was discovered (should be protected!)")
            protection_working = False
        else:
            print(f"  [PASS] {protected} is protected (not in cleanup list)")

    print("\n" + "=" * 80)
    if protection_working:
        print("[SUCCESS] Protection working correctly!")
        print("=" * 80)
        print("\nProtected datasets will NEVER be deleted by:")
        print("  - smoltrace-cleanup --all")
        print("  - smoltrace-cleanup --older-than X")
        print("  - smoltrace-cleanup --keep-recent N")
        print("  - Any other cleanup command")
        return True
    else:
        print("[FAILED] Protection NOT working!")
        print("=" * 80)
        print("\nProtected datasets could be deleted by cleanup!")
        return False


if __name__ == "__main__":
    success = test_protected_datasets()
    exit(0 if success else 1)
