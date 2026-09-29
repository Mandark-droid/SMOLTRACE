"""SPEC v0.2.6: task/request timeouts, per-task stop_reason, run status, token split."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from smolagents.memory import ActionStep, FinalAnswerStep
from smolagents.utils import AgentMaxStepsError

from smoltrace import core
from smoltrace.core import (
    RunStopped,
    _run_agent_tests,
    analyze_streamed_steps,
    evaluate_single_test,
    extract_traces,
    reset_run_stop,
    run_stop_requested,
)
from smoltrace.utils import build_status_row, compute_leaderboard_row


@pytest.fixture(autouse=True)
def _clean_stop_state():
    reset_run_stop()
    yield
    reset_run_stop()


def _step(tool=None):
    step = Mock(spec=ActionStep)
    step.code = None
    step.tool_calls = [SimpleNamespace(name=tool)] if tool else None
    return step


def _agent(events, memory_steps=()):
    agent = Mock()
    agent.tools = []
    agent.run.return_value = iter(events)
    agent.memory = SimpleNamespace(steps=list(memory_steps))
    return agent


# ------------------------------------------------------------------ per-task limit


def test_a_task_over_its_limit_is_stopped_and_the_agent_interrupted(monkeypatch):
    clock = iter([0.0, 10.0, 400.0, 800.0])
    monkeypatch.setattr(core.time, "monotonic", lambda: next(clock))
    agent = _agent([_step("lookup"), _step("lookup"), _step("lookup")])
    outcome = {}
    _tools, answered, steps, _resp = analyze_streamed_steps(
        agent, "t", "tool", task_timeout=300, outcome=outcome
    )
    assert outcome == {"stop_reason": "timeout", "timed_out": True}
    assert steps == 2 and answered is False  # the third step is never consumed
    agent.interrupt.assert_called_once()


def test_no_limit_means_the_stream_runs_to_its_end():
    agent = _agent([_step("lookup"), _step("final_answer")])
    outcome = {}
    analyze_streamed_steps(agent, "t", "tool", task_timeout=None, outcome=outcome)
    assert outcome == {"stop_reason": "final_answer", "timed_out": False}


def test_running_out_of_steps_is_not_a_final_answer_the_agent_chose():
    """smolagents writes a summary answer at max_steps; memory holds AgentMaxStepsError."""
    final = Mock(spec=FinalAnswerStep)
    final.output = "summary written by smolagents"
    maxed = SimpleNamespace(error=AgentMaxStepsError("Reached max steps.", Mock()))
    agent = _agent([_step("lookup"), _step("lookup"), final], memory_steps=[maxed])
    outcome = {}
    _tools, answered, _steps, response = analyze_streamed_steps(agent, "t", "tool", outcome=outcome)
    assert outcome["stop_reason"] == "max_steps"
    assert (
        answered is True and response == "summary written by smolagents"
    )  # scoring unchanged in 0.2.6


# ------------------------------------------------------------------ evaluate_single_test


def _case():
    return {"id": "t1", "prompt": "p", "difficulty": "easy", "expected_tool": "lookup"}


def test_a_timed_out_task_says_so(monkeypatch):
    clock = iter([0.0, 400.0])
    monkeypatch.setattr(core.time, "monotonic", lambda: next(clock))
    result = evaluate_single_test(
        _agent([_step("lookup")]), _case(), "tool", verbose=False, task_timeout=300
    )
    assert result["stop_reason"] == "timeout" and result["timed_out"] is True
    assert result["error"] == "task exceeded its 300s limit" and result["success"] is False


def test_an_exception_is_recorded_as_error():
    agent = Mock()
    agent.tools = []
    agent.run.side_effect = RuntimeError("litellm.Timeout: request timed out")
    result = evaluate_single_test(agent, _case(), "tool", verbose=False)
    assert result["stop_reason"] == "error" and "timed out" in result["error"]


def test_a_run_stop_during_a_task_marks_it_run_stopped_and_is_not_swallowed_as_error():
    agent = Mock()
    agent.tools = []
    agent.run.side_effect = RunStopped("run stopped by SIGTERM (deadline)")
    result = evaluate_single_test(agent, _case(), "tool", verbose=False)
    assert result["stop_reason"] == "run_stopped" and "SIGTERM" in result["error"]
    assert core._RUN_STOP.in_task is False


# ------------------------------------------------------------------ SIGTERM


def test_sigterm_during_a_task_raises_once_and_between_tasks_only_flags():
    core._RUN_STOP.in_task = True
    with pytest.raises(RunStopped):
        core._on_sigterm(15, None)
    assert run_stop_requested()
    core._on_sigterm(
        15, None
    )  # a second signal never raises again (the push must not be interrupted)
    reset_run_stop()
    core._RUN_STOP.in_task = False
    core._on_sigterm(15, None)
    assert run_stop_requested()


def test_a_stop_request_ends_the_task_loop_and_keeps_what_ran(monkeypatch):
    calls = []

    def fake_eval(agent, tc, *args, **kwargs):
        calls.append(tc["id"])
        if len(calls) == 2:
            core._RUN_STOP.event.set()
        return {"test_id": tc["id"], "success": True, "stop_reason": "final_answer"}

    monkeypatch.setattr(core, "evaluate_single_test", fake_eval)
    monkeypatch.setattr(core, "initialize_agent", lambda *a, **k: Mock())
    cases = [
        {"id": f"t{i}", "prompt": "p", "difficulty": "easy", "agent_type": "tool"} for i in range(5)
    ]
    results = _run_agent_tests("tool", "m", "litellm", None, None, cases, None, None, False, False)
    assert [r["test_id"] for r in results] == ["t0", "t1"]


# ------------------------------------------------------------------ request timeout


def test_the_request_timeout_reaches_the_litellm_client(monkeypatch):
    seen = {}
    monkeypatch.setattr(core, "LiteLLMModel", lambda **kw: seen.update(kw) or Mock())
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    core._initialize_model("openai/gpt-4.1-nano", "litellm", request_timeout=120)
    assert seen == {"model_id": "openai/gpt-4.1-nano", "timeout": 120}
    seen.clear()
    core._initialize_model("openai/gpt-4.1-nano", "litellm")
    assert seen == {"model_id": "openai/gpt-4.1-nano"}


# ------------------------------------------------------------------ leaderboard row


def _results(*reasons):
    return {
        "tool": [
            {"test_id": f"t{i}", "success": r == "final_answer", "steps": 2, "stop_reason": r}
            for i, r in enumerate(reasons)
        ],
        "code": [],
    }


def _row(results, run_state=None, traces=None):
    return compute_leaderboard_row(
        "m",
        results,
        traces or [],
        {},
        "ds",
        "r",
        "tr",
        "me",
        "tool",
        "run-1",
        run_state=run_state,
        task_timeout=300,
        request_timeout=120,
    )


def test_a_completed_run_counts_why_tasks_ended():
    row = _row(
        _results("final_answer", "timeout", "max_steps", "error"),
        {"planned_tests": 4, "stopped": False},
    )
    assert (row["run_status"], row["run_stop_reason"]) == ("completed", "completed")
    assert (row["planned_tests"], row["completed_tests"]) == (4, 4)
    assert (row["timed_out_tests"], row["max_steps_tests"], row["errored_tests"]) == (1, 1, 1)
    assert (row["task_timeout_s"], row["request_timeout_s"]) == (300, 120)


def test_a_stopped_run_with_results_is_partial():
    row = _row(
        _results("final_answer", "run_stopped"),
        {"planned_tests": 15, "stopped": True, "stop_reason": "deadline"},
    )
    assert (row["run_status"], row["run_stop_reason"]) == ("partial", "deadline")
    assert (row["planned_tests"], row["completed_tests"]) == (15, 1)


def test_a_stopped_run_where_nothing_finished_is_failed():
    row = _row(
        _results("run_stopped"), {"planned_tests": 15, "stopped": True, "stop_reason": "deadline"}
    )
    assert row["run_status"] == "failed"


def test_the_token_split_is_summed_and_absent_is_null_not_zero():
    split = [{"total_tokens": 150, "total_prompt_tokens": 100, "total_completion_tokens": 50}]
    row = _row(_results("final_answer"), traces=split)
    assert (row["total_prompt_tokens"], row["total_completion_tokens"]) == (100, 50)
    row = _row(_results("final_answer"), traces=[{"total_tokens": 150}])
    assert row["total_prompt_tokens"] is None and row["total_completion_tokens"] is None


def test_extract_traces_sums_the_split_from_llm_spans():
    exporter = Mock()
    exporter.get_finished_spans.return_value = [
        {
            "trace_id": "a",
            "span_id": "1",
            "attributes": {
                "llm.token_count.total": 30,
                "llm.token_count.prompt": 20,
                "llm.token_count.completion": 10,
            },
        },
        {
            "trace_id": "a",
            "span_id": "2",
            "attributes": {
                "llm.token_count.total": 5,
                "gen_ai.usage.prompt_tokens": 4,
                "gen_ai.usage.completion_tokens": 1,
            },
        },
        {"trace_id": "b", "span_id": "3", "attributes": {"llm.token_count.total": 7}},
    ]
    traces = {t["trace_id"]: t for t in extract_traces(exporter, "run")}
    assert (traces["a"]["total_prompt_tokens"], traces["a"]["total_completion_tokens"]) == (24, 11)
    assert traces["b"]["total_prompt_tokens"] is None


def test_a_status_only_row_has_null_scores_not_zero():
    row = build_status_row(
        "m",
        agent_type="tool",
        run_id="r",
        provider="litellm",
        dataset_used="ds",
        error="MCPToolsUnavailableError: no tools",
        planned_tests=15,
    )
    assert row["run_status"] == "failed" and row["run_stop_reason"].startswith(
        "error: MCPToolsUnavailableError"
    )
    assert (
        row["success_rate"] is None and row["pass_at_1"] is None and row["total_cost_usd"] is None
    )
    assert row["total_tests"] == 0 and row["planned_tests"] == 15


# ------------------------------------------------------------------ the whole flow: every run ends with a row


def _flow_args():
    from argparse import Namespace

    return Namespace(
        hf_token="test_token",
        model="m",
        provider="litellm",
        agent_type="tool",
        quiet=True,
        debug=False,
        enable_otel=True,
        prompt_yml=None,
        mcp_server_url=None,
        difficulty=None,
        dataset_name="org/ds",
        split="train",
        private=True,
        output_format="hub",
        output_dir="./out",
        run_id="run-9",
        use_case=None,
        team=None,
        purpose=None,
        suite_version=None,
        task_timeout=300.0,
        request_timeout=120.0,
    )


def _patch_flow(mocker):
    mocker.patch("smoltrace.main.get_hf_user_info", return_value={"username": "u"})
    mocker.patch(
        "smoltrace.main.generate_dataset_names",
        return_value=("u/results", "u/traces", "u/metrics", "u/leaderboard"),
    )
    mocker.patch("smoltrace.main.load_prompt_config", return_value=None)
    return mocker.patch("smoltrace.main.update_leaderboard")


def test_a_run_that_raises_still_records_a_failed_row_then_fails(mocker):
    from smoltrace.main import run_evaluation_flow

    update = _patch_flow(mocker)
    mocker.patch(
        "smoltrace.main.run_evaluation", side_effect=RuntimeError("MCP server refused: 502")
    )
    with pytest.raises(RuntimeError, match="502"):
        run_evaluation_flow(_flow_args())
    row = update.call_args.args[1]
    assert (
        row["run_status"] == "failed" and row["run_stop_reason"] == "error: MCP server refused: 502"
    )
    assert row["run_id"] == "run-9" and row["success_rate"] is None


def test_a_stopped_run_pushes_what_ran_then_exits_124(mocker):
    from smoltrace.main import run_evaluation_flow

    update = _patch_flow(mocker)
    push = mocker.patch("smoltrace.main.push_results_to_hf")

    def fake_run(**kwargs):
        kwargs["run_state"].update(
            {"planned_tests": 15, "stopped": True, "stop_reason": "deadline"}
        )
        return (_results("final_answer", "run_stopped"), [], {}, "org/ds", "run-9")

    mocker.patch("smoltrace.main.run_evaluation", side_effect=fake_run)
    with pytest.raises(SystemExit) as stop:
        run_evaluation_flow(_flow_args())
    assert stop.value.code == 124
    push.assert_called_once()
    row = update.call_args.args[1]
    assert (row["run_status"], row["planned_tests"], row["completed_tests"]) == ("partial", 15, 1)
