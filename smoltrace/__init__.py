"""
SMOLTRACE - Comprehensive benchmarking and evaluation framework for smolagents.
"""

__version__ = "0.0.1"

# Export main functions
from .core import run_evaluation
from .utils import cleanup_datasets, discover_smoltrace_datasets, filter_runs, group_datasets_by_run

__all__ = [
    "run_evaluation",
    "cleanup_datasets",
    "discover_smoltrace_datasets",
    "group_datasets_by_run",
    "filter_runs",
]
