# SmolTrace v0.1.0 — Leaderboard grouping + multi-server MCP

**Status:** ready to implement · **Author:** spec handed to Codex · **Date:** 2026-07-26
**Base:** `main` @ `ac27c1b` (v0.0.16)
**Target version:** **0.1.0** (minor — new CLI flags + new public row fields; not a patch)

---

## 1. Why

Two downstream consumers are blocked on SmolTrace:

1. **TraceVerse Evaluation Leaderboard UI** (`services/tracemind-ui/src/app/evaluations/leaderboard`) needs to filter and group runs by **use case**, **team** and **user**. Today every run — regardless of domain — competes on one flat podium, so a food-ordering agent run and a banking-compliance run share a ranking that means nothing. The UI cannot filter on fields SmolTrace never emits, so **the fix has to start here.**

2. **Model-selection-as-evidence workflow.** We benchmark candidate models *before* building an agent and publish that as the justification for the pick. That requires distinguishing a pre-build **selection** run from routine CI, and scoping the leaderboard to the use case being decided.

A third, smaller need: evaluating an agent against **three MCP servers at once** (Swiggy Food / Instamart / Dineout).

---

## 2. Scope

### Bucket A — leaderboard grouping metadata (the blocker)
### Bucket B — repeatable `--mcp-server-url` (small)

Everything else is out of scope. See §8.

---

## 3. Bucket A — implementation

### 3.1 `smoltrace/utils.py` — `compute_leaderboard_row()`

Current signature (verified):

```python
def compute_leaderboard_row(
    model_name: str,
    all_results: Dict[str, List[Dict]],
    trace_data: List[Dict],
    metric_data: Dict,
    dataset_used: str,
    results_dataset: str,
    traces_dataset: str,
    metrics_dataset: str,
    agent_type: str = "both",
    run_id: str = None,
    provider: str = "litellm",
) -> Dict:
```

Add four **optional, keyword-only** params, all defaulting to `None`:

| Param | Type | Meaning |
|---|---|---|
| `use_case` | `str \| None` | Domain/suite this run belongs to, e.g. `swiggy-mcp-ordering`, `banking-compliance-qa` |
| `team` | `str \| None` | Owning team/org |
| `purpose` | `str \| None` | One of `selection` \| `regression` \| `monitoring` |
| `suite_version` | `str \| None` | Version of the task suite (`dataset_used` is currently unversioned) |

Emit all four into the returned dict.

**Hard rule: never fabricate.** If a caller does not supply a value, the field is `None` in the row. Do **not** infer `use_case` from `dataset_used`, do not default `purpose` to `"regression"`, do not derive `team` from `submitted_by`. An absent value must stay absent — the whole point of this platform's evidence story is that unsupplied means unsupplied.

Note `submitted_by` already exists: it is derived inside this function from HF whoami and falls back to `"unknown"`. Leave that logic alone; user-wise grouping is a UI concern (§3.4).

Validate `purpose` against the three allowed values and raise `ValueError` on anything else. The other three are free-form strings — but normalise to lowercase-kebab and strip whitespace so `"Swiggy MCP Ordering"` and `"swiggy-mcp-ordering"` don't become two buckets.

### 3.2 `smoltrace/cli.py`

Add four arguments alongside the existing ones (`--run-id` is at ~line 167 for reference):

```
--use-case       str, optional   Use case / domain this run belongs to
--team           str, optional   Owning team or org
--purpose        choice, optional  selection | regression | monitoring
--suite-version  str, optional   Version identifier of the task suite
```

Use `choices=[...]` for `--purpose` so argparse rejects bad values at parse time.

### 3.3 `smoltrace/main.py`

Thread all four through to the `compute_leaderboard_row(...)` call (~line 114). No other logic changes.

### 3.4 `smoltrace/exporters/opensearch.py` — index template

The leaderboard index template is at ~line 231 (`"leaderboard": {"index_patterns": [f"{self.index_prefix}-leaderboard*"], ...}`).

Add explicit mappings for the four new fields as **`keyword`**, plus `submitted_by` if it is not already keyword-mapped.

> **This matters more than it looks.** The UI must `terms`-aggregate on these to build filter dropdowns and group-by. A `text`-mapped field fails aggregation with `illegal_argument_exception: Text fields are not optimised for operations that require per-document field data`. If you want both, map as `keyword` with a `.text` sub-field — not the other way round.

#### Ownership boundary — read this

`_ensure_index_templates()` (line ~213) runs on exporter init and calls `client.indices.put_index_template(...)` (line ~245). So **SmolTrace installs its own templates automatically** on the next export run. There is no manual template-deployment step and Codex does not need cluster access.

**But index templates only apply to newly-created indices.** `smoltrace-leaderboard` is a singleton — the pattern is `{prefix}-leaderboard*` with no date suffix, so it is never rolled. The existing production index will keep its current mapping and the four new fields will land under OpenSearch **dynamic mapping**, i.e. `text` with a `.keyword` sub-field. Aggregating on `use_case` would then fail while `use_case.keyword` worked — and the field name would differ between old and new indices. That silently breaks the UI filters this whole change exists to enable.

Fix is a one-time `PUT /smoltrace-leaderboard/_mapping` adding the four fields as `keyword` (adding *new* fields to an existing mapping is permitted; changing existing field types is not).

| Piece | Owner |
|---|---|
| Template definition in `exporters/opensearch.py` | **Codex** — this spec |
| Installing the template on a cluster | **Automatic** on next SmolTrace export run |
| `PUT _mapping` on the existing `smoltrace-leaderboard` index | **TraceVerse platform side — not Codex.** Do not touch the production cluster |
| UI filters / group-by | **TraceVerse platform side** (repo issue #539) |

Codex: implement the template, add a test asserting the four fields are `keyword` in the template body, and stop there.

### 3.5 `smoltrace/cards.py` — `generate_leaderboard_card()`

Function at ~line 371; the column schema table is at ~line 406 (it already documents `submitted_by`). Add rows for the four new columns with type and meaning.

---

## 4. The backward-compatibility problem — decide before coding

**This is the real risk in this change.**

The existing published HF dataset `smoltrace-leaderboard` has rows *without* these four columns. `update_leaderboard()` appends to it. The `datasets` library raises on feature mismatch, so **the first post-upgrade run will fail** unless this is handled deliberately.

Pick one and state the choice in the PR description:

- **(a) Nullable features + explicit `None`.** Declare the four as nullable `Value("string")` in the dataset features and write `None` for older rows on next write. Lowest friction. Verify `load_dataset` still works against the *already published* dataset before shipping.
- **(b) One-off migration.** Rewrite the existing dataset with the columns added as `None`, then append normally. Cleaner long-term, needs a migration script and a HF write.
- **(c) Version the dataset.** New repo/revision for the v0.1.0 schema, leave history frozen. Most conservative, most disruptive to consumers.

**Recommendation: (a), with (b) as fallback if features can't be reconciled in place.**

Whichever you choose, add a regression test that appends a new-schema row to an old-schema fixture and asserts it round-trips.

---

## 5. Bucket B — repeatable `--mcp-server-url`

`smoltrace/tools.py` (~line 2041) is hard single-endpoint:

```python
mcp_client = MCPClient({"url": mcp_server_url})
```

Make `--mcp-server-url` **repeatable**, accepting either a bare URL or `name=url`:

```
--mcp-server-url food=http://127.0.0.1:8931/mcp/ \
--mcp-server-url dineout=http://127.0.0.1:8932/mcp/
```

Load tools from each and merge. When a `name=` prefix is supplied, prefix the resulting tool names (`food_search_restaurants`) so collisions across servers are impossible — `report_error` exists on all three Swiggy servers, so **collisions are guaranteed, not hypothetical**. Single bare URL must keep working unchanged.

### Scope note — why this is small

A FastMCP composite proxy already fronts N remote MCP servers behind one URL with server-prefixed tool names (verified working against two live HTTP servers on `fastmcp 3.4.4`). So the flat and tool-search agent topologies need **no SmolTrace change at all** — they point at one proxy URL. Only a supervisor topology, where each sub-agent holds exactly one server's tools, genuinely needs multiple clients. Don't over-build this.

### Also verify

CLI help currently says `e.g. http://localhost:8000/sse`. FastMCP serves streamable HTTP at `/mcp/`. Confirm `smolagents.mcp_client.MCPClient` handles both transports; if it needs an explicit transport hint, expose it and fix the help text.

---

## 6. Tests

- `compute_leaderboard_row` emits all four fields; `None` when unsupplied.
- **No inference:** given `dataset_used="…swiggy…"` and no `use_case`, the row's `use_case` is `None`.
- `purpose` rejects a value outside the three allowed.
- Normalisation: `"Swiggy MCP Ordering"` → `"swiggy-mcp-ordering"`.
- Old-schema dataset + new-schema row round-trips (§4).
- OpenSearch template: the four fields are `keyword`; a `terms` aggregation on `use_case` succeeds against a test index.
- Multi-server: two stub MCP servers both exposing `report_error` load without collision and are correctly prefixed.
- Single bare `--mcp-server-url` still works (regression).

Keep coverage at or above the current level — check `pytest.ini` / existing coverage config before opening the PR.

---

## 7. Release

1. Bump `version` in `pyproject.toml` (line 10) `0.0.16` → `0.1.0`.
2. Update `changelog.md`.
3. Tag-driven release: tag → pre-release-check → GitHub release → PyPI.

**Known environment gotcha:** two pre-commit hooks fail under Windows App Control with `WinError 4551`. The established workaround is a **targeted** `SKIP` for those specific hooks *after manually verifying what they would have checked* — do not blanket-skip all hooks. There is also a known failed-commit-then-tag ordering trap in this repo; make sure the commit lands before tagging.

---

## 8. Out of scope

- Any change to how `submitted_by` is derived.
- Scoring, normalisation or ranking logic.
- The TraceVerse UI work — separate, and it consumes this.
- Backfilling `use_case` onto historical runs. Those runs genuinely had no use case recorded; inventing one retroactively would corrupt exactly the evidence trail this change exists to create. Leave them `None` and let the UI show them as ungrouped.

---

## 9. Acceptance

- [ ] `smoltrace ... --use-case swiggy-mcp-ordering --purpose selection --team platform` writes a leaderboard row carrying all four fields
- [ ] Same command without those flags writes `None`, and nothing is inferred
- [ ] The row reaches the `smoltrace-leaderboard` OpenSearch index and `terms`-aggregates on `use_case`, `team`, `purpose`, `submitted_by`
- [ ] Appending to the existing published HF leaderboard dataset does not raise
- [ ] Two MCP servers sharing a `report_error` tool load without collision
- [ ] Single bare `--mcp-server-url` unchanged
- [ ] Dataset card documents the new columns
- [ ] v0.1.0 tagged, released, on PyPI
