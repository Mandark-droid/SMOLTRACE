"""Base exporter interface for SMOLTRACE."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseExporter(ABC):
    """Abstract base class for SMOLTRACE data exporters."""

    @abstractmethod
    def export_results(
        self,
        flat_results: List[Dict[str, Any]],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export flattened evaluation results."""

    @abstractmethod
    def export_traces(
        self,
        trace_data: List[Dict],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export trace data."""

    @abstractmethod
    def export_metrics(
        self,
        flat_metrics: List[Dict[str, Any]],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export flattened metrics data."""

    @abstractmethod
    def export_leaderboard(
        self,
        leaderboard_row: Dict[str, Any],
        index_name: str,
        **kwargs,
    ) -> None:
        """Export a leaderboard entry."""
