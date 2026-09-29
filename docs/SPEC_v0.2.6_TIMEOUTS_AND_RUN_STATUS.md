# SPEC v0.2.6: task timeouts, stop reasons, run status, token split

Status: approved by the maintainer 2026-09-29. Target release: 0.2.6.

## Why

These are observed on the TraceVerse platform on 2026-09-28/29, not hypothetical:

1. **One stuck model call froze a whole run.** A DeepSeek-V4-Flash run on Nebius made one call that never
   returned. SMOLTRACE has no per-call or per-task limit, so the run sat silent for about 18 hours until
   the machine was stopped from outside. Everything it had done was lost.
2. **A looping model burns every step and still fails.** A model that keeps calling a tool with
   hallucinated arguments uses `max_steps`, paying for tokens on every step. smolagents then writes a
   summary answer, which SMOLTRACE counts as `final_answer_called`, and the run records nothing about
   why the task ended.
3. **A stopped or crashed run reports nothing.** Results live in memory and are pushed only after the
   last task (`main.run_evaluation_flow`). A run stopped at its deadline, or one that raised during
   setup, leaves no results, no traces and no leaderboard row, so the platform cannot say what happened.
4. **Cost estimates need the prompt/completion split.** Rows carry only `total_tokens`, so an estimator
   must assume the input/output ratio.

## Behaviour

### Per-call limit: `--request-timeout SECONDS` (default 120; 0 = the client's default)

This is passed to the model client where the client accepts one: `LiteLLMModel(timeout=...)` (the
`litellm` and `ollama` providers) and `InferenceClientModel(timeout=...)`. Local `transformers` models
have no network call, so it does not apply to them. A call that exceeds it raises. The task records the
error and the run moves on.

### Per-task limit: `--task-timeout SECONDS` (default 300; 0 = off)

The wall clock is checked after every event the agent streams. When it is exceeded, the agent is
interrupted, the task stops, and the run continues with the next task. A task can overrun its limit by
at most one in-flight model call (bounded by `--request-timeout`) or one tool call. A tool call that
never returns is still unbounded (see Limits).

### Per-task `stop_reason` (new result fields `stop_reason`, `timed_out`)

| `stop_reason` | Meaning |
|---|---|
| `final_answer` | The agent called `final_answer` itself |
| `max_steps` | The agent used every step without answering. smolagents records `AgentMaxStepsError` in `agent.memory` and generates a summary answer, which is **not** a final answer the agent chose |
| `timeout` | `--task-timeout` was exceeded |
| `error` | An exception ended the task (including a `--request-timeout`) |
| `run_stopped` | The run was stopped (see below) while this task was in flight |

Scoring is unchanged in 0.2.6, so old and new rows stay comparable. `success` still needs the right
tool, a final answer and a keyword. The new fields make the reason visible, and a later release may stop
counting a `max_steps` summary as a final answer.

### Run status: every run ends with a leaderboard row

New leaderboard fields:

- `run_status`: `completed` | `partial` | `failed`
- `run_stop_reason`: `completed` | `deadline` (SIGTERM) | `error: <message>`
- `planned_tests` and `completed_tests`
- `timed_out_tests`, `max_steps_tests`, `errored_tests`
- `task_timeout_s`, `request_timeout_s`: the limits the run ran under

How each outcome is recorded:

- **Stopped from outside (SIGTERM).** Platforms stop a run with `timeout -k 60 <deadline>`, which sends
  SIGTERM and then SIGKILL 60 s later. On SIGTERM, SMOLTRACE stops starting tasks and interrupts the
  one in flight, recording it as `run_stopped`. It then pushes results, traces and metrics for every
  task that ran, plus a leaderboard row with `run_status: partial` (or `failed` when no task finished)
  and `run_stop_reason: deadline`, and exits with code 124. The handler raises a `BaseException`
  subclass, so a blocked call is interrupted and the per-task `except Exception` cannot swallow it.
- **Raised during the run (dataset, MCP or model setup, or anything else).** SMOLTRACE pushes a
  **status-only** leaderboard row: `run_status: failed`, `run_stop_reason: error: <message>`, and
  `success_rate`, `pass_at_1` and the token/cost fields **null, not 0**. A run that measured nothing did
  not score 0%. It then re-raises, so the process still exits non-zero.
- **Completed normally.** `run_status: completed`, as before.

A leaderboard consumer must not rank a `partial` or `failed` row alongside `completed` ones.

**0.2.7:** tasks interrupted by the stop (`run_stopped`) are excluded from every score and from
`total_tests`, and counted as `interrupted_tests`. In 0.2.6 they counted as failures.

### Token split (new leaderboard fields `total_prompt_tokens`, `total_completion_tokens`)

These are summed from the same LLM spans that already feed `total_tokens`
(`llm.token_count.prompt|completion`, falling back to `gen_ai.usage.prompt_tokens|completion_tokens`).
They are **null** when no span carried a split, never 0 by assumption.

## Limits

- A tool call that never returns (for example an MCP server that stops answering mid-call) is not
  interrupted by `--task-timeout`: the check runs between agent events. The platform's run-level
  deadline remains the backstop for that case.
- With `--parallel-workers > 1`, SIGTERM stops new tasks and pushes the finished ones. Worker threads
  stuck in a call are abandoned, and SIGKILL ends the process after the push.
