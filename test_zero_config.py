#!/usr/bin/env python
"""Test script to verify SMOLTRACE zero-config dataset creation."""

import os
import sys

from dotenv import load_dotenv

# Load .env file
load_dotenv()


def test_zero_config():
    """Test the zero-config functionality of SMOLTRACE."""

    print("=" * 80)
    print("SMOLTRACE Zero-Config Test")
    print("=" * 80)

    # Step 1: Check HF_TOKEN
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("\n[ERROR] HF_TOKEN environment variable not set!")
        print("Please set it with: export HF_TOKEN=your_token_here")
        return False

    print(f"\n[OK] HF_TOKEN found: {hf_token[:10]}...")

    # Step 2: Test get_hf_user_info
    print("\n" + "-" * 80)
    print("Testing get_hf_user_info()...")
    print("-" * 80)

    from smoltrace.utils import get_hf_user_info

    try:
        user_info = get_hf_user_info(hf_token)
        if not user_info:
            print("[ERROR] Unable to fetch user info from HF token")
            return False

        print(f"[OK] User info fetched successfully:")
        print(f"   Username: {user_info['username']}")
        print(f"   Type: {user_info['type']}")
        print(f"   Full name: {user_info.get('fullname', 'N/A')}")

        username = user_info["username"]

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 3: Test generate_dataset_names
    print("\n" + "-" * 80)
    print("Testing generate_dataset_names()...")
    print("-" * 80)

    from smoltrace.utils import generate_dataset_names

    try:
        results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(username)

        print("[OK] Dataset names generated successfully:")
        print(f"   Results:     {results_repo}")
        print(f"   Traces:      {traces_repo}")
        print(f"   Metrics:     {metrics_repo}")
        print(f"   Leaderboard: {leaderboard_repo}")

        # Verify format
        assert results_repo.startswith(f"{username}/smoltrace-results-")
        assert traces_repo.startswith(f"{username}/smoltrace-traces-")
        assert metrics_repo.startswith(f"{username}/smoltrace-metrics-")
        assert leaderboard_repo == f"{username}/smoltrace-leaderboard"

        print("\n[OK] All dataset name formats are correct!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 4: Check API key for LiteLLM (optional)
    print("\n" + "-" * 80)
    print("Checking API credentials...")
    print("-" * 80)

    api_key = os.getenv("LITELLM_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not any([api_key, openai_key, anthropic_key]):
        print("[WARNING] No API keys found for LiteLLM")
        print("   For real evaluation, set one of:")
        print("   - LITELLM_API_KEY")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("\n   The test will use default test cases instead.")
    else:
        print("[OK] API credentials found")

    # Summary
    print("\n" + "=" * 80)
    print("ZERO-CONFIG TEST SUMMARY")
    print("=" * 80)
    print("[OK] HF token validation: PASSED")
    print("[OK] User info extraction: PASSED")
    print("[OK] Dataset name generation: PASSED")
    print("\n[SUCCESS] Zero-config functionality is working correctly!")
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("To run a full evaluation with auto-generated datasets:")
    print("\n1. Set API key (if using API models):")
    print("   export OPENAI_API_KEY=your_key_here")
    print("\n2. Run evaluation:")
    print("   smoltrace-eval --model openai/gpt-4 --agent-type tool --enable-otel")
    print("\n3. Or use the Python API:")
    print('   python -c "from smoltrace import evaluate_agents; ..."')
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_zero_config()
    sys.exit(0 if success else 1)
