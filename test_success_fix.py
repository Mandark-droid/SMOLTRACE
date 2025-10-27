#!/usr/bin/env python
"""
Test script to demonstrate the success field calculation fix.

This script shows how the fix resolves the issue where success was
incorrectly set to False/None even when all conditions were met.
"""

from unittest.mock import Mock, patch


def test_old_behavior():
    """Demonstrates the OLD (broken) behavior."""
    print("=" * 70)
    print("OLD BEHAVIOR (BROKEN):")
    print("=" * 70)

    # Simulate the old logic
    result = {
        "tool_called": True,
        "correct_tool": True,
        "final_answer_called": True,
        "response_correct": None,  # No expected_keywords, so this stays None
    }

    # Old success calculation (BROKEN)
    # Using .get() with default True doesn't help when value is explicitly None
    success = (
        result["tool_called"]
        and result.get("correct_tool", True)
        and result["final_answer_called"]
        and result.get("response_correct", True)  # This returns None, not True!
    )

    print(f"tool_called: {result['tool_called']}")
    print(f"correct_tool: {result['correct_tool']}")
    print(f"final_answer_called: {result['final_answer_called']}")
    print(f"response_correct: {result['response_correct']}")
    print(f"success: {success}")
    print(f"Success is falsy: {not success}")
    print(f"\n[BUG] Even though tool_called, correct_tool, and final_answer_called")
    print(f"      are all True, success evaluates to {success} (falsy!)")
    print()


def test_new_behavior():
    """Demonstrates the NEW (fixed) behavior."""
    print("=" * 70)
    print("NEW BEHAVIOR (FIXED):")
    print("=" * 70)

    # Simulate the new logic
    result = {
        "tool_called": True,
        "correct_tool": True,
        "final_answer_called": True,
        "response_correct": True,  # Now initialized to True by default
    }

    # Simulate: No expected_keywords, so response_correct stays True
    # (In the actual code, we now have: else: result["response_correct"] = True)

    # New success calculation (FIXED)
    success = (
        result["tool_called"]
        and result.get("correct_tool", True)
        and result["final_answer_called"]
        and result["response_correct"]  # Now True!
    )

    print(f"tool_called: {result['tool_called']}")
    print(f"correct_tool: {result['correct_tool']}")
    print(f"final_answer_called: {result['final_answer_called']}")
    print(f"response_correct: {result['response_correct']}")
    print(f"success: {success}")
    print(f"\n[FIXED] success is now {success} as expected!")
    print()


def test_with_actual_function():
    """Test with the actual evaluate_single_test function."""
    print("=" * 70)
    print("TESTING WITH ACTUAL FUNCTION:")
    print("=" * 70)

    from smoltrace.core import evaluate_single_test

    # Mock agent
    mock_agent = Mock()
    mock_agent.run.return_value = "The weather is sunny"

    # Mock analyze_streamed_steps
    with patch("smoltrace.core.analyze_streamed_steps") as mock_analyze:
        mock_analyze.return_value = (["get_weather"], True, 2)

        test_case = {
            "id": "test_001",
            "difficulty": "easy",
            "prompt": "What's the weather?",
            "expected_tool": "get_weather",
            # Note: NO expected_keywords!
        }

        result = evaluate_single_test(
            mock_agent,
            test_case,
            "tool",
            verbose=False
        )

        print(f"Tool called: {result['tool_called']}")
        print(f"Correct tool: {result['correct_tool']}")
        print(f"Final answer called: {result['final_answer_called']}")
        print(f"Response correct: {result['response_correct']}")
        print(f"Success: {result['success']}")

        if result['success']:
            print(f"\n[SUCCESS] Test correctly marked as successful!")
        else:
            print(f"\n[FAILURE] Test incorrectly marked as failed!")

    print()


def test_leaderboard_impact():
    """Show how this affects leaderboard calculations."""
    print("=" * 70)
    print("LEADERBOARD IMPACT:")
    print("=" * 70)

    # Simulate results from dataset
    results_old = [
        {"success": None, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": None, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": None, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": False, "tool_called": False, "correct_tool": False, "final_answer_called": True},
    ]

    results_new = [
        {"success": True, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": True, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": True, "tool_called": True, "correct_tool": True, "final_answer_called": True},
        {"success": False, "tool_called": False, "correct_tool": False, "final_answer_called": True},
    ]

    # Calculate success rate
    num_tests = len(results_old)

    # OLD: None is falsy, so sum counts it as 0
    success_rate_old = sum(1 for r in results_old if r["success"]) / num_tests * 100

    # NEW: True is truthy, so sum counts it as 1
    success_rate_new = sum(1 for r in results_new if r["success"]) / num_tests * 100

    print(f"Number of tests: {num_tests}")
    print(f"OLD success rate: {success_rate_old:.1f}%")
    print(f"NEW success rate: {success_rate_new:.1f}%")
    print(f"\n[OLD] The old logic would show 0% accuracy on the leaderboard")
    print(f"[NEW] The new logic correctly shows 75% accuracy")
    print()


if __name__ == "__main__":
    test_old_behavior()
    test_new_behavior()
    test_with_actual_function()
    test_leaderboard_impact()

    print("=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    print("""
The fix involves two changes:

1. Initialize response_correct to True (not None) at line 285 in core.py
2. Set response_correct = True when no expected_keywords (line 336 in core.py)

This ensures that when there are no expected keywords to validate,
the response is considered correct by default, and success is
calculated correctly.

BEFORE: response_correct = None -> success evaluates to None/False
AFTER:  response_correct = True -> success evaluates to True

This fix resolves the leaderboard showing 0% accuracy for all evaluations.
    """)
