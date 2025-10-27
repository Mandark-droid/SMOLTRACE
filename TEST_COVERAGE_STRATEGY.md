# Test Coverage Strategy for SMOLTRACE

## Current Status

```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
smoltrace\__init__.py       0      0   100%   ✅
smoltrace\cli.py           26     26     0%   ❌
smoltrace\core.py         272    272     0%   ❌
smoltrace\main.py          44     44     0%   ❌
smoltrace\otel.py         251    164    35%   ⚠️
smoltrace\tools.py         31     31     0%   ❌
smoltrace\utils.py        206    146    29%   ⚠️
-----------------------------------------------------
TOTAL                     830    683    18%
```

## Goal: 100% Coverage

This document outlines the strategy to achieve 100% test coverage.

## Module-by-Module Strategy

### 1. ✅ __init__.py (100% - Already Done)
- Empty module, nothing to test

### 2. ❌ cli.py (0% → 100%)

**Lines: 93 | Priority: HIGH**

**Testing Approach:**
- Mock `argparse` to test argument parsing
- Mock `run_evaluation_flow` to avoid running actual evaluations
- Test all CLI argument combinations

**Test File:** `tests/test_cli.py`

**Test Cases:**
1. `test_cli_minimal_args()` - Test with just --model
2. `test_cli_all_args()` - Test with all possible arguments
3. `test_cli_invalid_provider()` - Test validation
4. `test_cli_invalid_agent_type()` - Test validation
5. `test_cli_env_var_fallback()` - Test HF_TOKEN from environment
6. `test_cli_help()` - Test --help output

**Mocking Strategy:**
```python
@pytest.fixture
def mock_run_evaluation_flow(mocker):
    return mocker.patch('smoltrace.cli.run_evaluation_flow')

def test_cli_minimal_args(mock_run_evaluation_flow):
    sys.argv = ['smoltrace-eval', '--model', 'gpt-4']
    main()
    mock_run_evaluation_flow.assert_called_once()
```

### 3. ❌ core.py (0% → 100%)

**Lines: 642 | Priority: CRITICAL**

**Testing Approach:**
- This is the largest module - requires comprehensive mocking
- Mock external dependencies: smolagents, LiteLLM, transformers
- Test both API and GPU model paths
- Test error handling extensively

**Test File:** `tests/test_core.py`

**Key Functions to Test:**
1. `evaluate_agent_on_task()` - Core evaluation logic
2. `run_agent_iteration()` - Single iteration logic
3. `check_final_answer_called()` - Answer validation
4. `check_tool_called()` - Tool usage validation
5. `get_tools_for_agent()` - Tool retrieval
6. Provider-specific functions

**Test Cases (Sample):**
1. `test_evaluate_agent_success()` - Successful evaluation
2. `test_evaluate_agent_timeout()` - Timeout handling
3. `test_evaluate_agent_error()` - Error handling
4. `test_evaluate_agent_litellm_provider()` - LiteLLM path
5. `test_evaluate_agent_transformers_provider()` - Transformers path
6. `test_tool_calling_agent()` - Tool agent specifics
7. `test_code_agent()` - Code agent specifics
8. `test_multimodal_agent()` - Multimodal specifics

**Mocking Strategy:**
```python
@pytest.fixture
def mock_litellm_chat(mocker):
    mock_response = {
        "choices": [{
            "message": {"content": "Test response"},
            "finish_reason": "stop"
        }]
    }
    return mocker.patch('litellm.completion', return_value=mock_response)

@pytest.fixture
def mock_smolagents(mocker):
    mock_agent = mocker.Mock()
    mock_agent.run.return_value = "final_answer(42)"
    return mocker.patch('smolagents.ToolCallingAgent', return_value=mock_agent)
```

### 4. ❌ main.py (0% → 100%)

**Lines: 132 | Priority: HIGH**

**Testing Approach:**
- Mock all I/O operations (HuggingFace Hub, file operations)
- Mock `evaluate_agents` from core.py
- Test the orchestration flow

**Test File:** `tests/test_main.py`

**Key Functions to Test:**
1. `run_evaluation_flow()` - Main orchestration
2. Dataset creation logic
3. HuggingFace Hub interactions
4. Error handling and fallbacks

**Test Cases:**
1. `test_run_evaluation_flow_success()` - Full happy path
2. `test_run_evaluation_flow_with_custom_repos()` - Custom dataset names
3. `test_run_evaluation_flow_no_hf_token()` - Missing token handling
4. `test_run_evaluation_flow_hf_upload_failure()` - Upload error handling
5. `test_run_evaluation_flow_otel_enabled()` - OTEL integration
6. `test_run_evaluation_flow_gpu_metrics()` - GPU metrics path

**Mocking Strategy:**
```python
@pytest.fixture
def mock_evaluate_agents(mocker):
    return mocker.patch('smoltrace.main.evaluate_agents', return_value=(
        {"tool": [], "code": []},  # results
        [],  # traces
        {},  # metrics
        "test-dataset"
    ))

@pytest.fixture
def mock_hf_operations(mocker):
    mocker.patch('huggingface_hub.login')
    mocker.patch('datasets.Dataset.push_to_hub')
    mocker.patch('smoltrace.main.get_hf_user_info', return_value={"username": "test-user"})
```

### 5. ⚠️ otel.py (35% → 100%)

**Lines: 623 | Priority: HIGH**

**Testing Approach:**
- Mock OpenTelemetry components
- Mock genai_otel_instrument
- Test trace collection and metrics aggregation
- Test GPU metrics collection (mock pynvml)

**Test File:** `tests/test_otel.py`

**Key Functions to Test:**
1. `init_tracing()` - OTEL initialization
2. `collect_traces_for_test()` - Trace collection
3. `collect_metrics_for_test()` - Metrics collection
4. `aggregate_trace_data()` - Trace aggregation
5. `export_traces_to_dataset_format()` - Dataset export
6. GPU metrics functions

**Test Cases:**
1. `test_init_tracing_success()` - Successful initialization
2. `test_init_tracing_disabled()` - Disabled path
3. `test_collect_traces()` - Trace collection
4. `test_collect_metrics()` - Metrics collection
5. `test_aggregate_trace_data()` - Aggregation logic
6. `test_export_traces_otel_format()` - Format conversion
7. `test_gpu_metrics_collection()` - GPU metrics (mock pynvml)
8. `test_gpu_metrics_no_gpu()` - No GPU handling

**Mocking Strategy:**
```python
@pytest.fixture
def mock_otel(mocker):
    mocker.patch('genai_otel.instrument')
    mock_tracer = mocker.Mock()
    mocker.patch('opentelemetry.trace.get_tracer', return_value=mock_tracer)
    return mock_tracer

@pytest.fixture
def mock_gpu_metrics(mocker):
    mock_nvml = mocker.Mock()
    mock_nvml.nvmlDeviceGetCount.return_value = 1
    mock_nvml.nvmlDeviceGetHandleByIndex.return_value = "mock_handle"
    mocker.patch('pynvml', mock_nvml)
    return mock_nvml
```

### 6. ❌ tools.py (0% → 100%)

**Lines: 84 | Priority: MEDIUM**

**Testing Approach:**
- Test tool initialization
- Mock external tool dependencies
- Test tool calling logic

**Test File:** `tests/test_tools.py`

**Test Cases:**
1. `test_get_available_tools()` - Tool discovery
2. `test_initialize_duckduckgo_search()` - DuckDuckGo tool
3. `test_initialize_hf_api_tool()` - HF API tool
4. `test_tool_error_handling()` - Error cases

**Mocking Strategy:**
```python
@pytest.fixture
def mock_duckduckgo(mocker):
    return mocker.patch('duckduckgo_search.DDGS')

@pytest.fixture
def mock_hf_tool(mocker):
    return mocker.patch('smolagents.HfApiModel')
```

### 7. ⚠️ utils.py (29% → 100%)

**Lines: 527 | Priority: HIGH**

**Testing Approach:**
- Current tests cover `compute_leaderboard_row`
- Need to add tests for ALL other functions
- Mock HuggingFace Hub operations
- Test dataset generation and manipulation

**Test File:** `tests/test_utils.py` (extend existing)

**Functions Needing Tests:**
1. ✅ `compute_leaderboard_row()` - Already tested
2. ❌ `get_hf_user_info()` - HF user lookup
3. ❌ `generate_dataset_names()` - Name generation
4. ❌ `push_results_to_hf()` - Result upload
5. ❌ `update_leaderboard()` - Leaderboard update
6. ❌ `aggregate_gpu_metrics()` - GPU aggregation
7. ❌ `safe_avg()`, `safe_max()` - Utility functions

**Additional Test Cases:**
1. `test_get_hf_user_info_success()` - Successful lookup
2. `test_get_hf_user_info_failure()` - API failure
3. `test_generate_dataset_names()` - Timestamp format
4. `test_push_results_to_hf_success()` - Successful push
5. `test_push_results_to_hf_failure()` - Push failure
6. `test_update_leaderboard_new()` - New leaderboard
7. `test_update_leaderboard_existing()` - Append to existing
8. `test_aggregate_gpu_metrics()` - GPU data processing
9. `test_safe_avg_with_data()` - Average calculation
10. `test_safe_avg_empty()` - Empty list handling

## Implementation Priority

### Phase 1: Critical Path (Weeks 1-2)
1. **utils.py** (extend existing tests) - DONE: 29% → 60%+
2. **core.py** (evaluation engine) - 0% → 70%+
3. **main.py** (orchestration) - 0% → 80%+

### Phase 2: Integration (Week 3)
4. **otel.py** (telemetry) - 35% → 85%+
5. **cli.py** (entry point) - 0% → 95%+
6. **tools.py** (agent tools) - 0% → 90%+

### Phase 3: Edge Cases (Week 4)
- Increase all modules to 95%+
- Test error paths extensively
- Test all edge cases
- Final push to 100%

## Testing Best Practices

### 1. Use Fixtures Extensively
```python
@pytest.fixture
def sample_results():
    return {
        "tool": [{"test_id": "t1", "success": True}],
        "code": [{"test_id": "c1", "success": False}]
    }
```

### 2. Parameterize Where Possible
```python
@pytest.mark.parametrize("provider", ["litellm", "transformers", "ollama"])
def test_evaluation_with_provider(provider):
    # Test all providers with same logic
    pass
```

### 3. Mock External Dependencies
- Always mock: HuggingFace Hub, OpenTelemetry, LiteLLM, transformers
- Never make real API calls in tests
- Use `pytest-mock` for clean mocking

### 4. Test Error Paths
```python
def test_function_with_network_error(mocker):
    mocker.patch('requests.get', side_effect=ConnectionError())
    # Verify error handling
```

### 5. Use Coverage Reports
```bash
# After each test run
pytest --cov=smoltrace --cov-report=html
# Open htmlcov/index.html to see which lines are missing
```

## Coverage Exemptions

Some lines may be excluded from coverage with `# pragma: no cover`:

```python
# Defensive code that's hard to trigger
try:
    import optional_library
except ImportError:  # pragma: no cover
    optional_library = None

# CLI entry points
if __name__ == "__main__":  # pragma: no cover
    main()

# Fallback error handling
except Exception as e:  # pragma: no cover
    logger.error(f"Unexpected error: {e}")
    raise
```

## Continuous Monitoring

### In CI/CD (Already Configured)
- All workflows now enforce `--cov-fail-under=100`
- Coverage reports uploaded to Codecov
- Build fails if coverage drops below 100%

### Locally
```bash
# Before committing
pytest --cov=smoltrace --cov-report=term-missing --cov-fail-under=100

# To see what's missing
pytest --cov=smoltrace --cov-report=html
open htmlcov/index.html
```

## Realistic Timeline

**Current:** 18% coverage (830 statements, 683 missing)

**Target Milestones:**
- Week 1: 40-50% (focus on utils + main)
- Week 2: 65-75% (add core.py tests)
- Week 3: 85-90% (add otel, cli, tools)
- Week 4: 95-100% (edge cases, error paths)

**Estimated Effort:**
- ~40-60 hours of focused test writing
- ~200-300 test cases needed
- Heavy use of mocking required

## Next Steps

1. ✅ Fix failing tests (DONE)
2. Start with `tests/test_utils.py` expansion
3. Create `tests/test_main.py`
4. Create `tests/test_core.py` (largest effort)
5. Create `tests/test_otel.py`
6. Create `tests/test_cli.py`
7. Create `tests/test_tools.py`
8. Iterate until 100%

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Remember:** 100% coverage doesn't mean bug-free code, but it does mean every line has been executed at least once in tests, giving us confidence in the codebase.
