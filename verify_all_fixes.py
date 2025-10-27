#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete verification against DATASET_GAP_ANALYSIS.md
Checks EVERY issue identified in the original analysis
"""

import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_leaderboard_fixes():
    """Verify all leaderboard dataset fixes"""
    print("\n" + "="*60)
    print("1. LEADERBOARD DATASET FIXES")
    print("="*60)

    with open("smoltrace/utils.py", "r", encoding='utf-8') as f:
        content = f.read()

    issues = []

    # PRIORITY 1 - CRITICAL
    print("\n[CRITICAL] Missing Fields:")

    # 1. run_id
    if '"run_id": run_id' in content:
        print("  ✅ run_id - Present in leaderboard")
    else:
        print("  ❌ run_id - MISSING")
        issues.append("run_id missing from leaderboard")

    # 2. submitted_by
    if '"submitted_by": submitted_by' in content:
        print("  ✅ submitted_by - Present in leaderboard")
    else:
        print("  ❌ submitted_by - MISSING")
        issues.append("submitted_by missing from leaderboard")

    # 3. GPU metrics aggregation
    if '"gpu_utilization_avg"' in content:
        print("  ✅ gpu_utilization_avg - Present")
    else:
        print("  ❌ gpu_utilization_avg - MISSING")
        issues.append("gpu_utilization_avg missing")

    if '"gpu_memory_max_mib"' in content or '"gpu_memory_avg_mib"' in content:
        print("  ✅ gpu_memory metrics - Present")
    else:
        print("  ❌ gpu_memory metrics - MISSING")
        issues.append("gpu_memory metrics missing")

    # PRIORITY 2 - MODERATE (Naming)
    print("\n[MODERATE] Field Renames:")

    # 1. num_tests → total_tests
    if '"total_tests": num_tests' in content:
        print("  ✅ num_tests → total_tests - FIXED")
    else:
        print("  ❌ num_tests → total_tests - NOT FIXED")
        issues.append("num_tests not renamed to total_tests")

    # 2. total_co2_g → co2_emissions_g
    if '"co2_emissions_g"' in content and '"total_co2_g"' not in content:
        print("  ✅ total_co2_g → co2_emissions_g - FIXED")
    elif '"total_co2_g"' in content:
        print("  ⚠️  total_co2_g → co2_emissions_g - NOT RENAMED (still using old name)")
        issues.append("total_co2_g not renamed to co2_emissions_g")
    else:
        print("  ❌ co2_emissions_g - MISSING entirely")
        issues.append("co2_emissions_g missing")

    # 3. evaluation_date → timestamp
    if '"timestamp": datetime.now()' in content:
        print("  ✅ evaluation_date → timestamp - FIXED")
    else:
        print("  ❌ evaluation_date → timestamp - NOT FIXED")
        issues.append("evaluation_date not renamed to timestamp")

    return issues


def check_results_fixes():
    """Verify all results dataset fixes"""
    print("\n" + "="*60)
    print("2. RESULTS DATASET FIXES")
    print("="*60)

    with open("smoltrace/utils.py", "r", encoding='utf-8') as f:
        content = f.read()

    issues = []

    # PRIORITY 1 - CRITICAL
    print("\n[CRITICAL] Missing Fields (extracted from enhanced_trace_info):")

    checks = [
        ("trace_id", '"trace_id": trace_id'),
        ("execution_time_ms", '"execution_time_ms": execution_time_ms'),
        ("total_tokens", '"total_tokens": total_tokens'),
        ("cost_usd", '"cost_usd": cost_usd')
    ]

    for field_name, search_str in checks:
        if search_str in content:
            print(f"  ✅ {field_name} - Extracted to top level")
        else:
            print(f"  ❌ {field_name} - NOT extracted")
            issues.append(f"{field_name} not extracted from enhanced_trace_info")

    # Verify parsing logic
    print("\n[VERIFICATION] Parsing logic for enhanced_trace_info:")
    if 'enhanced_info.get("trace_id")' in content:
        print("  ✅ trace_id parsing - Present")
    else:
        print("  ❌ trace_id parsing - MISSING")
        issues.append("trace_id parsing logic missing")

    if 'enhanced_info.get("duration_ms"' in content:
        print("  ✅ duration_ms → execution_time_ms mapping - Present")
    else:
        print("  ❌ duration_ms parsing - MISSING")
        issues.append("duration_ms parsing logic missing")

    # PRIORITY 2 - MODERATE (Naming)
    print("\n[MODERATE] Field Renames:")

    # test_id → task_id
    if '"task_id": res["test_id"]' in content:
        print("  ✅ test_id → task_id - FIXED")
    else:
        print("  ❌ test_id → task_id - NOT FIXED")
        issues.append("test_id not renamed to task_id")

    return issues


def check_traces_fixes():
    """Verify all traces dataset fixes"""
    print("\n" + "="*60)
    print("3. TRACES DATASET FIXES")
    print("="*60)

    with open("smoltrace/otel.py", "r", encoding='utf-8') as f:
        content = f.read()

    issues = []

    # PRIORITY 1 - Status codes
    print("\n[HIGH] Span Status & Kind Format:")

    # Status code mapping
    if 'status_map = {0: "UNSET", 1: "OK", 2: "ERROR"}' in content:
        print("  ✅ Status codes - Mapped to strings (OK, ERROR, UNSET)")
    else:
        print("  ❌ Status codes - NOT mapped to strings")
        issues.append("Status codes not mapped to strings")

    # SpanKind prefix removal
    if 'if kind_str.startswith("SpanKind.")' in content:
        print("  ✅ SpanKind prefix - Removal logic present")
    else:
        print("  ❌ SpanKind prefix - NOT removed")
        issues.append("SpanKind prefix not removed")

    # KNOWN ISSUE - Not fixed (lower priority)
    print("\n[KNOWN ISSUE - Not Fixed]:")
    print("  ⚠️  Null span attributes (tokens, model names) - Requires genai_otel investigation")

    return issues


def check_metrics_fixes():
    """Verify metrics dataset fix"""
    print("\n" + "="*60)
    print("4. METRICS DATASET FIXES")
    print("="*60)

    with open("smoltrace/core.py", "r", encoding='utf-8') as f:
        content = f.read()

    issues = []

    # PRIORITY 1 - CRITICAL
    print("\n[CRITICAL] GPU Metrics Collection:")

    # force_flush()
    if "meter_provider.force_flush" in content:
        print("  ✅ force_flush() - Added before metric extraction")
    else:
        print("  ❌ force_flush() - NOT added")
        issues.append("force_flush() not added before metric extraction")

    if "timeout_millis=30000" in content:
        print("  ✅ force_flush timeout - Set to 30 seconds")
    else:
        print("  ⚠️  force_flush timeout - May not be optimal")

    return issues


def main():
    """Run complete verification"""
    print("="*60)
    print("COMPLETE VERIFICATION vs DATASET_GAP_ANALYSIS.md")
    print("="*60)

    all_issues = []

    # Check all datasets
    all_issues.extend(check_leaderboard_fixes())
    all_issues.extend(check_results_fixes())
    all_issues.extend(check_traces_fixes())
    all_issues.extend(check_metrics_fixes())

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    if not all_issues:
        print("\n🎉 ALL CRITICAL & MODERATE ISSUES FIXED!")
        print("\nFixed issues:")
        print("  ✅ GPU metrics force_flush()")
        print("  ✅ run_id in leaderboard")
        print("  ✅ submitted_by in leaderboard")
        print("  ✅ GPU metrics aggregation")
        print("  ✅ timestamp (was evaluation_date)")
        print("  ✅ total_tests (was num_tests)")
        print("  ✅ task_id (was test_id)")
        print("  ✅ trace_id extracted")
        print("  ✅ execution_time_ms extracted")
        print("  ✅ total_tokens extracted")
        print("  ✅ cost_usd extracted")
        print("  ✅ Status codes to strings")
        print("  ✅ SpanKind prefix removed")
        return 0
    else:
        print(f"\n⚠️  {len(all_issues)} issue(s) still need attention:\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
