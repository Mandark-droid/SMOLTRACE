"""
SMOLTRACE - Comprehensive benchmarking and evaluation framework for smolagents.
"""

__version__ = "0.2.0"

# Export main functions
from .core import run_evaluation
from .utils import (
    cleanup_datasets,
    compute_pass_at_1,
    discover_smoltrace_datasets,
    filter_runs,
    group_datasets_by_run,
)

__all__ = [
    "run_evaluation",
    "cleanup_datasets",
    "compute_pass_at_1",
    "discover_smoltrace_datasets",
    "group_datasets_by_run",
    "filter_runs",
    "exporters",
]
