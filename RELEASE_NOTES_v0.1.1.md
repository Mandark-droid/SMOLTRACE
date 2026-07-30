# SMOLTRACE v0.1.1

SMOLTRACE 0.1.1 fixes the link between a test-case result and the trace that
test case produced, and makes that link work in both directions.

## The bug

The result-to-trace link was never recorded while a test ran. It was
reconstructed afterwards by scanning every exported span for a `test.id`
attribute, first-match-wins.

A test case declared with `agent_type: "both"` is executed once per agent type
and emits two distinct traces — but `test.id` is identical for both, so both
result rows inherited the *first* trace's id. The code-agent row deep-linked
into the tool-agent's trace.

This is visible in published runs: in
`kshitijthakkar/smoltrace-results-20260402_051106`, the `shared_basic_weather`
and `shared_basic_search` rows each carry one `trace_id` shared across their
tool and code executions.

A second defect compounded it: `export_results` keyed OpenSearch documents on
`task_id`, which is not unique when a test case runs under both agent types, so
one of the two rows was silently overwritten.

## The fix

- `evaluate_single_test` reads `trace_id` and `span_id` off the root
  `test_evaluation` span as soon as the span opens — before the agent runs, so a
  test case that errors out keeps its trace link. These source-captured ids take
  precedence over the reconstructed summary.
- Every result carries `test_case_uid` (`"<agent_type>:<test_id>"`), a stable
  key identifying one execution of one test case. It is stamped on the span as
  `test.case_uid`, promoted onto the trace document, and used as the OpenSearch
  results document id.
- Trace documents carry the test-case identity at the top level (`test_ids`,
  `test_case_uids`, `root_span_id`, `agent_type`), so trace → test case no
  longer requires walking nested span attributes.

## New fields

| Where | Fields |
| --- | --- |
| Result records / flattened rows | `test_case_uid`, `span_id`, `run_id` |
| Trace documents | `test_ids`, `test_case_uids`, `root_span_id`, `agent_type` |
| Root span attributes | `test.case_uid` |
| OpenSearch mappings | results: `test_case_uid`, `span_id`; traces: `test_ids`, `test_case_uids`, `root_span_id` |

## Compatibility

All schema changes are additive — nothing was renamed or removed, and
`enhanced_trace_info` keeps its existing shape plus a `root_span_id` key.
Results produced by earlier versions still resolve through the
`enhanced_trace_info` fallback, and traces recorded before `test.case_uid`
existed still resolve by `test_id`.

The one behavioural change: OpenSearch results documents are now keyed on
`test_case_uid` instead of `task_id`. Each run writes to its own index, so this
only stops rows from overwriting each other.
