# SMOLTRACE Dataset Enrichment Analysis

## Executive Summary

This document analyzes the current SMOLTRACE dataset schemas against the comprehensive set of attributes available from `genai-otel-instrument` version 0.1.7.dev0. It identifies missing critical fields and proposes enhanced schemas to maximize observability and insight value.

---

## Table of Contents

1. [Current vs. Available Attributes](#current-vs-available-attributes)
2. [Missing Critical Fields by Dataset](#missing-critical-fields-by-dataset)
3. [Proposed Enhanced Schemas](#proposed-enhanced-schemas)
4. [Implementation Plan](#implementation-plan)

---

## Current vs. Available Attributes

### 1. Results Dataset

#### Currently Captured ✅
```python
{
    "model": str,
    "evaluation_date": datetime,
    "test_id": str,
    "agent_type": str,
    "difficulty": str,
    "prompt": str,
    "success": bool,
    "tool_called": bool,
    "correct_tool": bool,
    "final_answer_called": bool,
    "response_correct": bool,
    "tools_used": List[str],
    "steps": int,
    "response": str,
    "error": Optional[str],
    "enhanced_trace_info": str (JSON),
}
```

#### Missing from OTEL Attributes ❌
```python
{
    # LLM Request Parameters
    "gen_ai.request.temperature": float,           # CRITICAL
    "gen_ai.request.top_p": float,                 # CRITICAL
    "gen_ai.request.max_tokens": int,              # CRITICAL
    "gen_ai.request.frequency_penalty": float,
    "gen_ai.request.presence_penalty": float,

    # Response Metadata
    "gen_ai.response.id": str,                     # CRITICAL for debugging
    "gen_ai.response.finish_reasons": List[str],   # CRITICAL for understanding completion
    "gen_ai.response.model": str,                  # Actual model used (may differ from request)

    # Performance Metrics (Per Test)
    "execution_time_ms": float,                    # CRITICAL - missing!
    "gen_ai.usage.prompt_tokens": int,             # CRITICAL
    "gen_ai.usage.completion_tokens": int,         # CRITICAL
    "gen_ai.usage.total_tokens": int,              # Currently only in enhanced_trace_info

    # Cost Breakdown (Per Test)
    "gen_ai.usage.cost.total": float,              # CRITICAL
    "gen_ai.usage.cost.prompt": float,
    "gen_ai.usage.cost.completion": float,
    "gen_ai.usage.cost.reasoning": float,          # For OpenAI o1 models
    "gen_ai.usage.cost.cache_read": float,         # For Anthropic cache
    "gen_ai.usage.cost.cache_write": float,        # For Anthropic cache

    # Streaming Metrics (Per Test)
    "gen_ai.server.ttft": float,                   # Time to first token (seconds)
    "gen_ai.server.tbt": float,                    # Time between tokens (seconds)

    # Advanced Token Types
    "completion_tokens_details.reasoning_tokens": int,  # OpenAI o1
    "cache_read_input_tokens": int,                     # Anthropic
    "cache_creation_input_tokens": int,                 # Anthropic

    # Trace Linking
    "trace_id": str,                               # CRITICAL - links to traces dataset
    "run_id": str,                                 # CRITICAL - links all datasets
    "start_time": datetime,                        # Start timestamp
    "end_time": datetime,                          # End timestamp
    "start_time_unix_nano": str,                   # For metrics timeframe lookup
    "end_time_unix_nano": str,                     # For metrics timeframe lookup

    # Error Classification
    "error_type": str,                             # "timeout", "tool_not_found", "llm_error", etc.
}
```

**Impact**: Missing **28 critical fields** that would enable:
- Cost analysis per test case
- Performance profiling (TTFT, latency)
- Parameter tracking for reproducibility
- Advanced token usage analysis (reasoning, caching)
- Proper trace linking

---

### 2. Traces Dataset

#### Currently Captured ✅
```python
{
    "trace_id": str,
    "model": str,
    "agent_type": str,
    "total_tokens": int,
    "total_duration_ms": float,
    "total_cost_usd": float,
    "spans": List[{
        "span_id": str,
        "parent_span_id": str,
        "name": str,
        "start_time": int (nanoseconds),
        "end_time": int (nanoseconds),
        "duration_ms": float,
        "attributes": Dict,
        "events": List[Dict],
        "status": Dict,
        "kind": str,
        "resource": Dict,
    }],
    "timestamp": datetime,
}
```

#### Missing from OTEL Attributes ❌
```python
{
    # Linking Fields
    "run_id": str,                                 # CRITICAL - missing link to leaderboard
    "test_id": str,                                # CRITICAL - link to results dataset

    # Provider Information
    "gen_ai.system": str,                          # CRITICAL - "openai", "anthropic", etc.
    "provider": str,                               # "litellm" or "transformers"

    # Granular Cost Breakdown (Trace Level)
    "gen_ai.usage.cost.prompt": float,
    "gen_ai.usage.cost.completion": float,
    "gen_ai.usage.cost.reasoning": float,
    "gen_ai.usage.cost.cache_read": float,
    "gen_ai.usage.cost.cache_write": float,

    # Token Breakdown (Trace Level)
    "gen_ai.usage.prompt_tokens": int,
    "gen_ai.usage.completion_tokens": int,
    "completion_tokens_details.reasoning_tokens": int,
    "cache_read_input_tokens": int,
    "cache_creation_input_tokens": int,

    # Streaming Aggregates
    "gen_ai.server.ttft": float,                   # First token timing
    "avg_tbt": float,                              # Average time between tokens

    # Tool/Function Calls (Span Attributes)
    "llm.tools": str (JSON),                       # Tool definitions
    "tool_call_count": int,                        # Total tool calls in trace

    # Request Parameters (from spans)
    "gen_ai.request.temperature": float,
    "gen_ai.request.top_p": float,
    "gen_ai.request.max_tokens": int,

    # Response Metadata
    "gen_ai.response.id": str,
    "gen_ai.response.finish_reasons": List[str],
    "gen_ai.response.model": str,
}
```

**Impact**: Missing **23 critical fields** that would enable:
- Cross-dataset linking (run_id, test_id)
- Provider/system identification
- Granular cost analysis
- Advanced token tracking (reasoning, caching)
- Streaming performance analysis

---

### 3. Metrics Dataset

#### Currently Captured ✅
```python
{
    # Aggregate Metrics (from TraceMetricsAggregator)
    "aggregates": [
        {
            "name": "tests.successful",
            "type": "counter",
            "data_points": [{"value": int, "attributes": {...}}]
        },
        {
            "name": "tests.tool_calls",
            "type": "histogram",
            "data_points": [{"value": {"sum": int, "count": int, "avg": float}}]
        },
        {
            "name": "tests.steps",
            "type": "histogram",
            ...
        },
        {
            "name": "llm.token_count.total",
            "type": "sum",
            "unit": "tokens",
            ...
        },
        {
            "name": "gen_ai.usage.cost.total",
            "type": "sum",
            "unit": "USD",
            ...
        },
        {
            "name": "gen_ai.co2.emissions",
            "type": "sum",
            "unit": "gCO2e",
            ...
        },
    ],

    # GPU Time-Series Metrics (from genai_otel)
    "resourceMetrics": [{
        "resource": {"attributes": [...]},
        "scopeMetrics": [{
            "scope": {"name": "genai.gpu"},
            "metrics": [
                {
                    "name": "gen_ai.gpu.utilization",
                    "unit": "%",
                    "gauge": {"dataPoints": [...]}
                },
                {
                    "name": "gen_ai.gpu.memory.used",
                    "unit": "MiB",
                    ...
                },
                {
                    "name": "gen_ai.gpu.temperature",
                    "unit": "Cel",
                    ...
                },
                # Missing: gen_ai.gpu.power
                # Missing: gen_ai.gpu.memory.total
            ]
        }]
    }]
}
```

#### Missing from OTEL Attributes ❌
```python
{
    # Linking Fields
    "run_id": str,                                 # CRITICAL - missing!
    "test_id": str,                                # For per-test metrics (optional)
    "trace_id": str,                               # For per-trace metrics (optional)

    # Missing GPU Metrics (NEW in 0.1.7.dev0!)
    "gen_ai.gpu.power": {                          # CRITICAL - power consumption
        "unit": "Watts",
        "gauge": {"dataPoints": [...]}
    },
    "gen_ai.gpu.memory.total": {                   # CRITICAL - total GPU memory
        "unit": "MiB",
        "gauge": {"dataPoints": [...]}
    },

    # Missing Cost Metrics (Granular)
    "gen_ai.usage.cost.prompt": {
        "type": "counter",
        "unit": "USD",
        "data_points": [...]
    },
    "gen_ai.usage.cost.completion": {...},
    "gen_ai.usage.cost.reasoning": {...},         # OpenAI o1
    "gen_ai.usage.cost.cache_read": {...},        # Anthropic
    "gen_ai.usage.cost.cache_write": {...},       # Anthropic

    # Missing Token Metrics (Granular)
    "gen_ai.client.token.usage": {                 # Separate prompt/completion counters
        "type": "counter",
        "attributes": {"token_type": "prompt|completion"}
    },

    # Missing Performance Metrics
    "gen_ai.client.operation.duration": {          # Operation latency histogram
        "type": "histogram",
        "unit": "seconds",
        "buckets": [...]
    },
    "gen_ai.server.ttft": {                        # TTFT histogram
        "type": "histogram",
        "unit": "seconds",
        ...
    },
    "gen_ai.server.tbt": {                         # TBT histogram
        "type": "histogram",
        "unit": "seconds",
        ...
    },

    # Missing Request Metrics
    "gen_ai.requests": {                           # Request counter by operation
        "type": "counter",
        "attributes": {"operation": str, "provider": str}
    },

    # Missing Error Metrics
    "gen_ai.client.errors": {                      # Error counter
        "type": "counter",
        "attributes": {"operation": str, "error_type": str}
    },

    # Environmental Metrics
    "gen_ai.power.cost": {                         # Electricity cost from GPU
        "type": "counter",
        "unit": "USD",
        ...
    },
}
```

**Impact**: Missing **15+ metric types** that would enable:
- GPU power tracking (NEW in 0.1.7.dev0)
- Total GPU memory capacity
- Granular cost breakdowns (prompt, completion, reasoning, cache)
- Performance histograms (latency, TTFT, TBT)
- Error tracking and classification
- Environmental cost tracking

---

### 4. Leaderboard Dataset

#### Currently Captured ✅
```python
{
    # Identification
    "run_id": str,
    "model": str,
    "agent_type": str,
    "provider": str,
    "evaluation_date": datetime,
    "submitted_by": str,

    # Dataset References
    "results_dataset": str,
    "traces_dataset": str,
    "metrics_dataset": str,
    "dataset_used": str,

    # Aggregate Statistics
    "num_tests": int,
    "successful_tests": int,
    "failed_tests": int,
    "success_rate": float,
    "avg_steps": float,
    "avg_duration_ms": float,
    "total_duration_ms": float,
    "total_tokens": int,
    "avg_tokens_per_test": int,
    "total_cost_usd": float,
    "avg_cost_per_test_usd": float,

    # Environmental Impact
    "co2_emissions_g": float,

    # GPU Metrics (Aggregated)
    "gpu_utilization_avg": float,
    "gpu_utilization_max": float,
    "gpu_memory_avg_mib": float,
    "gpu_memory_max_mib": float,
    "gpu_temperature_avg": float,
    "gpu_temperature_max": float,
    "gpu_power_avg_w": float,

    # Metadata
    "notes": str,
}
```

#### Missing from OTEL Attributes ❌
```python
{
    # Provider/System Information
    "gen_ai.system": str,                          # CRITICAL - "openai", "anthropic", "ollama", etc.

    # Token Breakdown (Aggregates)
    "total_prompt_tokens": int,                    # CRITICAL
    "total_completion_tokens": int,                # CRITICAL
    "avg_prompt_tokens": int,
    "avg_completion_tokens": int,
    "total_reasoning_tokens": int,                 # For OpenAI o1
    "total_cache_read_tokens": int,                # For Anthropic
    "total_cache_write_tokens": int,               # For Anthropic

    # Cost Breakdown (Aggregates)
    "total_cost_prompt_usd": float,                # CRITICAL
    "total_cost_completion_usd": float,            # CRITICAL
    "total_cost_reasoning_usd": float,             # For OpenAI o1
    "total_cost_cache_read_usd": float,            # For Anthropic
    "total_cost_cache_write_usd": float,           # For Anthropic
    "avg_cost_prompt_per_test_usd": float,
    "avg_cost_completion_per_test_usd": float,

    # Streaming Performance (Aggregates)
    "avg_ttft_seconds": float,                     # CRITICAL - streaming performance
    "p50_ttft_seconds": float,
    "p95_ttft_seconds": float,
    "p99_ttft_seconds": float,
    "avg_tbt_seconds": float,

    # Request Parameters (Most Common)
    "common_temperature": float,                   # Most used temperature
    "common_top_p": float,                         # Most used top_p
    "common_max_tokens": int,                      # Most used max_tokens

    # Error Statistics
    "total_errors": int,
    "error_rate": float,
    "error_types": Dict[str, int],                 # {"timeout": 2, "llm_error": 1, ...}

    # GPU Metrics (Additional)
    "gpu_memory_total_mib": float,                 # Total GPU capacity (NEW in 0.1.7.dev0)
    "gpu_power_max_w": float,                      # Peak power consumption
    "total_gpu_energy_wh": float,                  # Total energy consumed (Watt-hours)
    "electricity_cost_usd": float,                 # Cost of electricity

    # Tool Usage Statistics
    "total_tool_calls": int,
    "avg_tool_calls_per_test": float,
    "unique_tools_used": int,
    "most_used_tool": str,

    # Version Tracking
    "smoltrace_version": str,                      # CRITICAL for reproducibility
    "genai_otel_version": str,                     # CRITICAL for reproducibility
    "smolagents_version": str,

    # HF Jobs Integration
    "hf_job_id": str,                              # HF Job reference
    "job_type": str,                               # "cpu|gpu_a10|gpu_h200"
    "hardware": str,                               # Hardware specification
}
```

**Impact**: Missing **38 critical fields** that would enable:
- Detailed cost analysis (granular breakdown)
- Token usage insights (prompt vs. completion vs. reasoning)
- Streaming performance metrics (TTFT, TBT)
- Error analysis and classification
- GPU power and energy tracking
- Version tracking for reproducibility
- HuggingFace Jobs integration metadata

---

## Missing Critical Fields by Dataset

### Priority 1: CRITICAL (Must Add) 🔴

#### Results Dataset
1. **`run_id`** - Links to leaderboard and all other datasets
2. **`trace_id`** - Links to traces dataset
3. **`execution_time_ms`** - Performance metric
4. **`gen_ai.usage.prompt_tokens`** - Token breakdown
5. **`gen_ai.usage.completion_tokens`** - Token breakdown
6. **`gen_ai.usage.total_tokens`** - Total tokens (currently only in enhanced_trace_info)
7. **`gen_ai.usage.cost.total`** - Cost per test
8. **`gen_ai.request.temperature`** - Reproducibility
9. **`gen_ai.request.top_p`** - Reproducibility
10. **`gen_ai.request.max_tokens`** - Reproducibility
11. **`gen_ai.response.finish_reasons`** - Understanding completion
12. **`start_time_unix_nano`** - Metrics timeframe lookup
13. **`end_time_unix_nano`** - Metrics timeframe lookup

#### Traces Dataset
1. **`run_id`** - Link to leaderboard
2. **`test_id`** - Link to results dataset
3. **`gen_ai.system`** - Provider identification
4. **`provider`** - "litellm" or "transformers"

#### Metrics Dataset
1. **`run_id`** - Link to leaderboard
2. **`gen_ai.gpu.power`** - Power consumption (NEW!)
3. **`gen_ai.gpu.memory.total`** - GPU capacity (NEW!)

#### Leaderboard Dataset
1. **`gen_ai.system`** - Provider/system identification
2. **`total_prompt_tokens`** - Token breakdown
3. **`total_completion_tokens`** - Token breakdown
4. **`total_cost_prompt_usd`** - Cost breakdown
5. **`total_cost_completion_usd`** - Cost breakdown
6. **`smoltrace_version`** - Version tracking
7. **`genai_otel_version`** - Version tracking

### Priority 2: HIGH (Should Add) 🟠

#### Results Dataset
1. **`gen_ai.usage.cost.prompt`** - Granular cost
2. **`gen_ai.usage.cost.completion`** - Granular cost
3. **`gen_ai.server.ttft`** - Streaming performance
4. **`gen_ai.response.id`** - Response tracking
5. **`error_type`** - Error classification

#### Traces Dataset
1. **`gen_ai.usage.cost.prompt`** - Cost breakdown
2. **`gen_ai.usage.cost.completion`** - Cost breakdown
3. **`gen_ai.usage.prompt_tokens`** - Token breakdown
4. **`gen_ai.usage.completion_tokens`** - Token breakdown
5. **`gen_ai.server.ttft`** - Streaming timing

#### Leaderboard Dataset
1. **`avg_ttft_seconds`** - Streaming performance
2. **`total_errors`** - Error tracking
3. **`error_rate`** - Error analysis
4. **`hf_job_id`** - HF Jobs integration
5. **`job_type`** - Hardware used

### Priority 3: NICE-TO-HAVE (Can Add) 🟢

- Advanced token types (reasoning, cache)
- Percentile metrics (p50, p95, p99)
- Tool usage statistics
- Detailed error type breakdowns

---

## Proposed Enhanced Schemas

See next section for detailed schemas with ALL fields included.

---

## Implementation Plan

### Phase 1: Critical Fields (Week 1)
1. Add linking fields (`run_id`, `trace_id`, `test_id`) across all datasets
2. Add token breakdown fields to Results and Leaderboard
3. Add cost fields to Results and Leaderboard
4. Add LLM request parameters to Results (temperature, top_p, max_tokens)
5. Add execution timing to Results
6. Add provider/system identification to Traces and Leaderboard

### Phase 2: GPU & Metrics Enhancement (Week 1)
1. Add `gen_ai.gpu.power` metric collection (NEW in 0.1.7.dev0)
2. Add `gen_ai.gpu.memory.total` metric collection (NEW in 0.1.7.dev0)
3. Update metrics extraction to capture granular cost metrics
4. Update leaderboard to aggregate GPU power metrics

### Phase 3: Performance Metrics (Week 2)
1. Add TTFT tracking to Results and Traces
2. Add TBT metrics to Traces
3. Add streaming performance aggregates to Leaderboard
4. Add latency histograms to Metrics

### Phase 4: Advanced Features (Week 2)
1. Add reasoning token tracking (OpenAI o1)
2. Add cache token tracking (Anthropic)
3. Add granular cost breakdown (prompt, completion, reasoning, cache)
4. Add error classification and tracking
5. Add version tracking fields
6. Add HF Jobs integration metadata

### Phase 5: Testing & Validation (Week 2)
1. Update tests to validate new fields
2. Test with all supported providers (OpenAI, Anthropic, HuggingFace, Ollama)
3. Test with GPU models (transformers provider)
4. Test with API models (litellm provider)
5. Validate cross-dataset consistency
6. Document all new fields

---

## Summary

### Current State
- **Results Dataset**: 14 fields → **Missing 28 critical fields**
- **Traces Dataset**: 10 fields → **Missing 23 critical fields**
- **Metrics Dataset**: 6 metric types → **Missing 15+ metric types**
- **Leaderboard Dataset**: 29 fields → **Missing 38 critical fields**

### Target State (After Enhancement)
- **Results Dataset**: 42 fields (3x increase)
- **Traces Dataset**: 33 fields (3.3x increase)
- **Metrics Dataset**: 21+ metric types (3.5x increase)
- **Leaderboard Dataset**: 67 fields (2.3x increase)

### Value Proposition
1. **Complete Observability**: Capture every critical metric from OTEL
2. **Cross-Dataset Consistency**: Proper linking via run_id, trace_id, test_id
3. **Cost Transparency**: Granular cost breakdown (prompt, completion, reasoning, cache)
4. **Performance Insights**: TTFT, TBT, latency distributions
5. **Reproducibility**: Request parameters and version tracking
6. **GPU Awareness**: Power consumption, energy usage, environmental impact
7. **HF Jobs Integration**: Job metadata for seamless cloud execution
8. **TraceMind UI Ready**: All fields needed for 4-screen navigation
