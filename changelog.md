# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Data Schema Improvements (2025-10-23)
- **Complete data schema overhaul with run_id support**:
  - Added `InMemoryMetricExporter` class in `smoltrace/otel.py` for capturing GPU metrics in OpenTelemetry format
  - Renamed `InMemoryMetricReaderCollector` to `TraceMetricsAggregator` for clarity
  - All datasets now include `run_id` for linking and filtering across datasets
  - Results dataset includes `test_index`, `start_time_unix_nano`, `end_time_unix_nano` fields
  - Metrics dataset restructured to OpenTelemetry `resourceMetrics` format with time-series data
  - Leaderboard includes 7 new GPU metric fields: `gpu_utilization_avg/max`, `gpu_memory_avg/max_mib`, `gpu_temperature_avg/max`, `gpu_power_avg_w`
  - Leaderboard includes `run_id`, `provider`, `submitted_by`, `successful_tests`, `failed_tests` fields

- **New CLI argument**: `--run-id` for specifying custom run identifiers (auto-generates UUID if not provided)

- **GPU metrics aggregation**: New `aggregate_gpu_metrics()` helper function in `smoltrace/utils.py`
  - Extracts time-series data from OpenTelemetry resourceMetrics
  - Computes avg and max values for utilization, memory, temperature, power

- **Sample data generation**: New `generate_sample_metrics.py` script in `MockTraceMind/sample_data/`
  - Generates GPU metrics sample (`metrics_llama31.json`)
  - Generates API metrics sample (`metrics_gpt4.json`)

- **Comprehensive documentation**:
  - `IMPLEMENTATION_PLAN.md` - Detailed implementation guide
  - `IMPLEMENTATION_COMPLETE.md` - Complete feature summary and testing guide
  - `REMAINING_IMPLEMENTATION.md` - Mid-implementation status
  - `METRICS_DATASET_FIX.md` - Post-implementation fixes documentation
  - `smoltrace_dataset_structure.md` - Updated complete schema documentation

- **Test files**:
  - `tests/test_otel_fix.py` - Verifies InMemoryMetricExporter works correctly
  - `tests/test_metrics_dataset_creation.py` - Verifies metrics dataset creation logic

### Added
- **Local JSON output option**: New `--output-format {hub,json}` CLI argument to save results locally instead of pushing to HuggingFace Hub
  - New `--output-dir` argument for specifying local output directory (default: `./smoltrace_results`)
  - Automatically creates timestamped directories with 5 JSON files: `results.json`, `traces.json`, `metrics.json`, `leaderboard_row.json`, `metadata.json`
  - Implemented `save_results_locally()` function in `smoltrace/utils.py`
- **Explicit provider selection**: New `--provider {litellm,transformers,ollama}` CLI argument
  - Supports multiple API keys: `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`
  - Clearer error messages for missing API keys
- **OpenTelemetry integration**: Added `smoltrace/otel.py` with in-memory OTEL exporters and metrics aggregation
  - `InMemorySpanExporter` for collecting traces
  - `InMemoryMetricReaderCollector` for aggregating metrics from traces
  - Support for genai_otel_instrument auto-instrumentation
- **Tool definitions**: Added `smoltrace/tools.py` with custom tools
  - `WeatherTool`: Mock weather data for testing
  - `CalculatorTool`: Basic math calculations
  - `TimeTool`: Current time in specified timezone
  - `DuckDuckGoSearchTool`: Web search functionality
- **Cost metric**: Added `gen_ai.usage.cost.total` to metrics dataset
- **Environment file loading**: Added `.env` file loading via `python-dotenv` at CLI startup
- **Package discovery**: Added explicit package configuration in `pyproject.toml` to exclude test directories
- Added `duckduckgo-search` as main dependency
- Made `genai-otel-instrument` a default dependency (moved from optional)
- Added `avg_duration_ms`, `total_duration_ms`, and `total_cost_usd` to leaderboard metrics
- Added `gradio==6.0.0.dev0` to `requirements-dev.txt`

### Changed - Data Schema Improvements (2025-10-23)
- **Core evaluation flow** (`smoltrace/core.py`):
  - `run_evaluation()` now accepts `run_id` and `enable_gpu_metrics` parameters
  - Returns 5 values: `(all_results, trace_data, metric_data, dataset_name, run_id)`
  - Adds `run_id` and `test_index` to all results
  - `extract_traces()` now accepts `run_id` and adds it to each trace
  - `extract_metrics()` completely rewritten to return Dict with `run_id`, `resourceMetrics`, `aggregates`
  - Added comprehensive debug logging for metric extraction

- **OTEL setup** (`smoltrace/otel.py`):
  - `setup_inmemory_otel()` now accepts `run_id` and `enable_gpu_metrics` parameters
  - Returns 6 values: `(tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id)`
  - Creates Resource with run_id attribute
  - Uses `PeriodicExportingMetricReader` with 10-second intervals

- **Main evaluation flow** (`smoltrace/main.py`):
  - Updated to handle 5-value return from `run_evaluation()`
  - Auto-enables GPU metrics when provider is "transformers"
  - Displays run_id to user
  - Passes run_id to all dataset functions

- **Dataset generation** (`smoltrace/utils.py`):
  - `compute_leaderboard_row()` now accepts `metric_data` as Dict (was List)
  - Accepts `run_id` and `provider` parameters
  - Extracts HuggingFace username from token for `submitted_by` field
  - Aggregates GPU metrics and includes in leaderboard row
  - `push_results_to_hf()` now accepts `metric_data` as Dict
  - Changed condition to always create metrics dataset (even with empty resourceMetrics)
  - Pushes metrics in OpenTelemetry resourceMetrics format
  - Single row per run containing all time-series data

### Changed
- Refactored `run_evaluation` in `smoltrace/core.py` to return raw evaluation data
- Updated `push_results_to_hf` in `smoltrace/utils.py` to accept and push trace and metric data
- Updated `compute_leaderboard_row` in `smoltrace/utils.py` to include new duration and cost metrics
- Updated `run_evaluation_flow` in `smoltrace/main.py` to:
  - Pass trace and metric data to `push_results_to_hf`
  - Branch based on `--output-format` (hub vs json)
  - Remove unicode emoji characters (replaced with text markers for Windows compatibility)
- Updated `initialize_agent()` in `smoltrace/core.py` to support three providers with explicit configuration
- Enhanced `_aggregate_from_traces()` in `smoltrace/otel.py` to correctly collect metrics from span attributes

### Fixed - Data Schema Improvements (2025-10-23)
- **Critical: Fixed InMemoryMetricExporter missing attributes** (`smoltrace/otel.py`):
  - Error: `AttributeError: 'InMemoryMetricExporter' object has no attribute '_preferred_temporality'`
  - Added `_preferred_temporality` and `_preferred_aggregation` attributes required by `PeriodicExportingMetricReader`
  - Now properly implements OpenTelemetry MetricExporter interface

- **Critical: Fixed metrics dataset not being created** (`smoltrace/utils.py`):
  - Issue: Dataset wasn't created for API models because `resourceMetrics` was an empty list
  - Changed condition from `if metric_data.get("resourceMetrics"):` to `if "resourceMetrics" in metric_data:`
  - Now checks for key existence rather than truthiness
  - Dataset is always created (with empty resourceMetrics for API models, populated for GPU models)
  - Added informative logging to distinguish between GPU and API model metrics

### Fixed
- **Critical: Fixed OpenTelemetry tracer error**: `'Tracer' object has no attribute 'trace'`
  - Changed from `tracer.trace.get_current_span()` to `trace.get_current_span()` (lines 186, 227 in `core.py`)
  - Added proper import: `from opentelemetry import trace`
  - Added safety checks for span recording: `if current_span and current_span.is_recording()`
- **Critical: Fixed metrics aggregation returning all zeros**
  - Now correctly collects token counts, costs, and metrics from span attributes
  - Token counts properly captured from trace-level aggregated data
  - Test-specific metrics collected from individual spans (lines 146-242 in `otel.py`)
- **Security: Removed sensitive argument printing from CLI**
  - CLI no longer prints command-line arguments that may contain tokens
- Removed unused imports in `smoltrace/cli.py`, `smoltrace/core.py`, and `tests/test_utils.py`
- Fixed unicode encoding errors by replacing emoji characters with text markers

## [0.1.0] - YYYY-MM-DD

### Added

- Initial release of smoltrace.
