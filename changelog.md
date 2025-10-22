# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
