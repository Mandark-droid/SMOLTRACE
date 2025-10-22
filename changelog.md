# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `avg_duration_ms`, `total_duration_ms`, and `total_cost_usd` to leaderboard metrics.
- Added `gradio==6.0.0.dev0` to `requirements-dev.txt`.

### Changed
- Refactored `run_evaluation` in `smoltrace/core.py` to return raw evaluation data.
- Updated `push_results_to_hf` in `smoltrace/utils.py` to accept and push trace and metric data.
- Updated `compute_leaderboard_row` in `smoltrace/utils.py` to include new duration and cost metrics.
- Updated `run_evaluation_flow` in `smoltrace/main.py` to pass trace and metric data to `push_results_to_hf`.

### Fixed
- Removed unused imports in `smoltrace/cli.py`, `smoltrace/core.py`, and `tests/test_utils.py`.

## [0.1.0] - YYYY-MM-DD

### Added

- Initial release of smoltrace.
