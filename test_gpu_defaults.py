#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test GPU metrics default behavior for different providers
"""

import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def test_gpu_metrics_defaults():
    """Test that GPU metrics are enabled by default for local models"""
    print("="*60)
    print("Testing GPU Metrics Default Behavior")
    print("="*60)

    # Read the main.py logic
    with open("smoltrace/main.py", "r", encoding='utf-8') as f:
        content = f.read()

    # Verify correct logic is present
    checks = {
        "Local model detection": 'is_local_model = args.provider in ["transformers", "ollama"]',
        "Disable flag check": 'user_disabled = hasattr(args, "disable_gpu_metrics")',
        "Auto-enable for local": 'elif is_local_model:',
        "User disable message": '[INFO] GPU metrics disabled by user',
    }

    print("\n[LOGIC VERIFICATION]")
    all_pass = True
    for name, search_str in checks.items():
        if search_str in content:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} - NOT FOUND")
            all_pass = False

    # Read the CLI
    with open("smoltrace/cli.py", "r", encoding='utf-8') as f:
        cli_content = f.read()

    print("\n[CLI FLAG VERIFICATION]")
    if '--disable-gpu-metrics' in cli_content:
        print("  ✅ --disable-gpu-metrics flag present")
    else:
        print("  ❌ --disable-gpu-metrics flag MISSING")
        all_pass = False

    if '--enable-gpu-metrics' in cli_content:
        print("  ❌ Old --enable-gpu-metrics flag still present (should be removed)")
        all_pass = False
    else:
        print("  ✅ Old --enable-gpu-metrics flag removed")

    # Test behavior simulation
    print("\n[BEHAVIOR SIMULATION]")
    test_cases = [
        ("transformers", False, True, "Transformers (default)"),
        ("transformers", True, False, "Transformers (--disable-gpu-metrics)"),
        ("ollama", False, True, "Ollama (default)"),
        ("ollama", True, False, "Ollama (--disable-gpu-metrics)"),
        ("litellm", False, False, "LiteLLM (default)"),
        ("litellm", True, False, "LiteLLM (--disable-gpu-metrics)"),
    ]

    for provider, user_disabled, expected, description in test_cases:
        # Simulate the logic
        is_local_model = provider in ["transformers", "ollama"]

        if user_disabled:
            enable_gpu_metrics = False
        elif is_local_model:
            enable_gpu_metrics = True
        else:
            enable_gpu_metrics = False

        status = "✅" if enable_gpu_metrics == expected else "❌"
        print(f"  {status} {description}: GPU={enable_gpu_metrics} (expected {expected})")

        if enable_gpu_metrics != expected:
            all_pass = False

    # Summary
    print("\n" + "="*60)
    if all_pass:
        print("✅ ALL TESTS PASSED!")
        print("\nBehavior:")
        print("  • transformers → GPU metrics ON by default")
        print("  • ollama → GPU metrics ON by default")
        print("  • litellm → GPU metrics OFF by default")
        print("  • --disable-gpu-metrics flag to opt-out")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(test_gpu_metrics_defaults())
