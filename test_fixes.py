#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick verification test for SMOLTRACE dataset structure fixes
Tests all 5 critical fixes to ensure TraceMind UI compatibility
"""

import json
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_force_flush_exists():
    """Test 1: Verify force_flush() was added to core.py"""
    print("\n=== Test 1: force_flush() Implementation ===")

    with open("smoltrace/core.py", "r", encoding='utf-8') as f:
        content = f.read()

    # Check for force_flush call
    assert "force_flush" in content, "❌ force_flush() not found in core.py"
    assert "meter_provider.force_flush" in content, "❌ meter_provider.force_flush not called"
    assert "timeout_millis=30000" in content, "❌ force_flush timeout not set correctly"

    print("✅ force_flush() correctly implemented")
    return True


def test_field_renames():
    """Test 2 & 4: Verify field renames in leaderboard and results"""
    print("\n=== Test 2 & 4: Field Renames ===")

    with open("smoltrace/utils.py", "r", encoding='utf-8') as f:
        content = f.read()

    # Check leaderboard renames
    assert '"timestamp": datetime.now()' in content, "❌ evaluation_date not renamed to timestamp"
    assert '"total_tests": num_tests' in content, "❌ num_tests not renamed to total_tests"

    # Check results rename
    assert '"task_id": res["test_id"]' in content, "❌ test_id not renamed to task_id"

    print("✅ timestamp (leaderboard)")
    print("✅ total_tests (leaderboard)")
    print("✅ task_id (results)")
    return True


def test_enhanced_trace_extraction():
    """Test 3: Verify fields extracted from enhanced_trace_info"""
    print("\n=== Test 3: enhanced_trace_info Field Extraction ===")

    with open("smoltrace/utils.py", "r", encoding='utf-8') as f:
        content = f.read()

    # Check extraction logic
    assert '"trace_id": trace_id' in content, "❌ trace_id not extracted"
    assert '"execution_time_ms": execution_time_ms' in content, "❌ execution_time_ms not extracted"
    assert '"total_tokens": total_tokens' in content, "❌ total_tokens not extracted"
    assert '"cost_usd": cost_usd' in content, "❌ cost_usd not extracted"

    # Check parsing logic
    assert 'enhanced_info.get("trace_id")' in content, "❌ trace_id not parsed"
    assert 'enhanced_info.get("duration_ms"' in content, "❌ duration_ms not parsed"
    assert 'enhanced_info.get("total_tokens"' in content, "❌ total_tokens not parsed"
    assert 'enhanced_info.get("cost_usd"' in content, "❌ cost_usd not parsed"

    print("✅ trace_id extracted")
    print("✅ execution_time_ms extracted (from duration_ms)")
    print("✅ total_tokens extracted")
    print("✅ cost_usd extracted")
    return True


def test_span_status_and_kind():
    """Test 5: Verify span status codes and kind format fixes"""
    print("\n=== Test 5: Span Status & Kind Format ===")

    with open("smoltrace/otel.py", "r", encoding='utf-8') as f:
        content = f.read()

    # Check status code mapping
    assert 'status_map = {0: "UNSET", 1: "OK", 2: "ERROR"}' in content, "❌ Status code mapping not found"
    assert '"code": status_code' in content, "❌ Status code not using mapped value"

    # Check kind prefix removal
    assert 'if kind_str.startswith("SpanKind.")' in content, "❌ SpanKind prefix removal not found"
    assert 'kind_str.replace("SpanKind.", "")' in content, "❌ SpanKind prefix not being removed"
    assert '"kind": kind_str' in content, "❌ Kind not using cleaned value"

    print("✅ Status codes mapped to strings (OK, ERROR, UNSET)")
    print("✅ SpanKind. prefix removed")
    return True


def test_integration():
    """Integration test: Verify complete data flow"""
    print("\n=== Integration Test: Complete Data Flow ===")

    try:
        # Import after fixes
        from smoltrace.utils import flatten_results_for_hf
        from smoltrace.otel import InMemorySpanExporter

        # Test 1: flatten_results_for_hf with enhanced_trace_info
        test_results = {
            "tool": [{
                "test_id": "test_001",
                "agent_type": "tool",
                "difficulty": "easy",
                "prompt": "Test prompt",
                "success": True,
                "tool_called": True,
                "correct_tool": True,
                "final_answer_called": True,
                "tools_used": ["get_weather"],
                "steps": 3,
                "response": "Test response",
                "enhanced_trace_info": {
                    "trace_id": "0xabc123",
                    "duration_ms": 1234.5,
                    "total_tokens": 500,
                    "cost_usd": 0.01
                }
            }]
        }

        flattened = flatten_results_for_hf(test_results, "test-model")

        # Verify extraction worked
        assert flattened[0]["task_id"] == "test_001", "❌ task_id not set correctly"
        assert flattened[0]["trace_id"] == "0xabc123", "❌ trace_id not extracted"
        assert flattened[0]["execution_time_ms"] == 1234.5, "❌ execution_time_ms not extracted"
        assert flattened[0]["total_tokens"] == 500, "❌ total_tokens not extracted"
        assert flattened[0]["cost_usd"] == 0.01, "❌ cost_usd not extracted"

        print("✅ Results dataset structure correct")
        print(f"  - task_id: {flattened[0]['task_id']}")
        print(f"  - trace_id: {flattened[0]['trace_id']}")
        print(f"  - execution_time_ms: {flattened[0]['execution_time_ms']}")
        print(f"  - total_tokens: {flattened[0]['total_tokens']}")
        print(f"  - cost_usd: {flattened[0]['cost_usd']}")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("SMOLTRACE Dataset Structure Fixes - Verification Tests")
    print("=" * 60)

    tests = [
        ("Force Flush Implementation", test_force_flush_exists),
        ("Field Renames", test_field_renames),
        ("Enhanced Trace Extraction", test_enhanced_trace_extraction),
        ("Span Status & Kind", test_span_status_and_kind),
        ("Integration Test", test_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except AssertionError as e:
            print(f"\n❌ {name} FAILED: {e}")
            results.append((name, False))
        except Exception as e:
            print(f"\n❌ {name} ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All fixes verified successfully!")
        print("\nNext steps:")
        print("1. Run SMOLTRACE evaluation to generate new datasets")
        print("2. Load datasets in TraceMind UI")
        print("3. Verify all 4 screens display correctly")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
