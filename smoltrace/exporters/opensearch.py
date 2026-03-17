"""OpenSearch exporter for SMOLTRACE evaluation data.

Creates OpenSearch indexes equivalent to the HuggingFace datasets:
- smoltrace-results-{timestamp}  → evaluation results per test case
- smoltrace-traces-{timestamp}   → OpenTelemetry trace spans
- smoltrace-metrics-{timestamp}  → GPU/CO2 time-series metrics
- smoltrace-leaderboard          → aggregate leaderboard entries
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseExporter

# Index mappings that mirror the HF dataset schemas
RESULTS_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "model": {"type": "keyword"},
            "evaluation_date": {"type": "date"},
            "task_id": {"type": "keyword"},
            "agent_type": {"type": "keyword"},
            "difficulty": {"type": "keyword"},
            "prompt": {"type": "text"},
            "success": {"type": "boolean"},
            "tool_called": {"type": "boolean"},
            "correct_tool": {"type": "boolean"},
            "final_answer_called": {"type": "boolean"},
            "response_correct": {"type": "boolean"},
            "tools_used": {"type": "keyword"},
            "steps": {"type": "integer"},
            "response": {"type": "text"},
            "error": {"type": "text"},
            "trace_id": {"type": "keyword"},
            "execution_time_ms": {"type": "float"},
            "total_tokens": {"type": "integer"},
            "cost_usd": {"type": "float"},
            "enhanced_trace_info": {"type": "text", "index": False},
            "run_id": {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
}

TRACES_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "trace_id": {"type": "keyword"},
            "model": {"type": "keyword"},
            "agent_type": {"type": "keyword"},
            "total_tokens": {"type": "integer"},
            "total_duration_ms": {"type": "float"},
            "total_cost_usd": {"type": "float"},
            "spans": {
                "type": "nested",
                "properties": {
                    "span_id": {"type": "keyword"},
                    "parent_span_id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "start_time": {"type": "long"},
                    "end_time": {"type": "long"},
                    "duration_ms": {"type": "float"},
                    "attributes": {"type": "object", "enabled": True},
                    "events": {"type": "nested"},
                    "status": {"type": "object"},
                },
            },
            "timestamp": {"type": "date"},
            "run_id": {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
}

METRICS_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "run_id": {"type": "keyword"},
            "service_name": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "timestamp_unix_nano": {"type": "keyword"},
            "gpu_id": {"type": "keyword"},
            "gpu_name": {"type": "keyword"},
            "co2_emissions_gco2e": {"type": "float"},
            "power_cost_usd": {"type": "float"},
            "gpu_utilization_percent": {"type": "float"},
            "gpu_memory_used_mib": {"type": "float"},
            "gpu_memory_total_mib": {"type": "float"},
            "gpu_temperature_celsius": {"type": "float"},
            "gpu_power_watts": {"type": "float"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
}

LEADERBOARD_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "run_id": {"type": "keyword"},
            "model": {"type": "keyword"},
            "agent_type": {"type": "keyword"},
            "provider": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "submitted_by": {"type": "keyword"},
            "results_dataset": {"type": "keyword"},
            "traces_dataset": {"type": "keyword"},
            "metrics_dataset": {"type": "keyword"},
            "dataset_used": {"type": "keyword"},
            "total_tests": {"type": "integer"},
            "successful_tests": {"type": "integer"},
            "failed_tests": {"type": "integer"},
            "success_rate": {"type": "float"},
            "avg_steps": {"type": "float"},
            "avg_duration_ms": {"type": "float"},
            "total_duration_ms": {"type": "float"},
            "total_tokens": {"type": "integer"},
            "total_cost_usd": {"type": "float"},
            "gpu_utilization_avg": {"type": "float"},
            "gpu_memory_max_mib": {"type": "float"},
            "co2_emissions_g": {"type": "float"},
            "power_cost_total_usd": {"type": "float"},
            "notes": {"type": "text"},
            # OpenSearch index references (parallel to HF dataset references)
            "results_index": {"type": "keyword"},
            "traces_index": {"type": "keyword"},
            "metrics_index": {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
}


class OpenSearchExporter(BaseExporter):
    """Exports SMOLTRACE data to OpenSearch indexes.

    Creates indexes that mirror the HuggingFace dataset structure,
    enabling the same drill-down navigation pattern:
        leaderboard → results → traces (with metrics overlay)

    Args:
        host: OpenSearch host (default: localhost)
        port: OpenSearch port (default: 9200)
        auth: Tuple of (username, password) for basic auth
        use_ssl: Whether to use SSL/TLS
        verify_certs: Whether to verify SSL certificates
        ssl_show_warn: Whether to show SSL warnings
        index_prefix: Prefix for all index names (default: "smoltrace")
        opensearch_url: Full OpenSearch URL (overrides host/port/ssl settings)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        auth: Optional[tuple] = None,
        use_ssl: bool = False,
        verify_certs: bool = True,
        ssl_show_warn: bool = True,
        index_prefix: str = "smoltrace",
        opensearch_url: Optional[str] = None,
    ):
        try:
            from opensearchpy import OpenSearch
        except ImportError:
            raise ImportError(
                "opensearch-py is required for OpenSearch export. "
                "Install it with: pip install smoltrace[opensearch]"
            )

        self.index_prefix = index_prefix

        if opensearch_url:
            self.client = OpenSearch(
                hosts=[opensearch_url],
                http_auth=auth,
                verify_certs=verify_certs,
                ssl_show_warn=ssl_show_warn,
            )
        else:
            scheme = "https" if use_ssl else "http"
            host_url = f"{scheme}://{host}:{port}"
            self.client = OpenSearch(
                hosts=[host_url],
                http_auth=auth,
                use_ssl=use_ssl,
                verify_certs=verify_certs,
                ssl_show_warn=ssl_show_warn,
            )

        # Verify connection
        info = self.client.info()
        print(f"[OK] Connected to OpenSearch {info['version']['number']}")

    def _create_index_if_not_exists(self, index_name: str, mapping: Dict) -> None:
        """Create an index with the given mapping if it doesn't already exist."""
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=mapping)
            print(f"[OK] Created OpenSearch index: {index_name}")

    def _bulk_index(
        self, index_name: str, documents: List[Dict], id_field: Optional[str] = None
    ) -> int:
        """Bulk index documents into OpenSearch.

        Args:
            index_name: Target index name
            documents: List of documents to index
            id_field: Optional field to use as document _id

        Returns:
            Number of successfully indexed documents
        """
        from opensearchpy import helpers

        actions = []
        for doc in documents:
            action = {
                "_index": index_name,
                "_source": _serialize_doc(doc),
            }
            if id_field and id_field in doc:
                action["_id"] = doc[id_field]
            actions.append(action)

        success, errors = helpers.bulk(self.client, actions, raise_on_error=False)
        if errors:
            print(f"[WARN] {len(errors)} documents failed to index in {index_name}")
            for err in errors[:3]:
                print(f"  Error: {err}")
        return success

    def _get_index_name(self, dataset_type: str, timestamp: Optional[str] = None) -> str:
        """Generate index name matching the HF dataset naming convention.

        Args:
            dataset_type: One of "results", "traces", "metrics", "leaderboard"
            timestamp: Optional timestamp string (YYYYMMDD_HHMMSS format)

        Returns:
            Index name like "smoltrace-results-20251116-142301"
        """
        if dataset_type == "leaderboard":
            return f"{self.index_prefix}-leaderboard"

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        else:
            # Convert underscore format to dash for valid index names
            timestamp = timestamp.replace("_", "-")

        return f"{self.index_prefix}-{dataset_type}-{timestamp}"

    def export_results(
        self,
        flat_results: List[Dict[str, Any]],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export flattened evaluation results to OpenSearch.

        Creates an index equivalent to the HF results dataset with one
        document per test case.
        """
        if not flat_results:
            print("[SKIP] No results to export to OpenSearch.")
            return

        # Add run_id to each document
        for doc in flat_results:
            doc["run_id"] = run_id

        self._create_index_if_not_exists(index_name, RESULTS_INDEX_MAPPING)
        count = self._bulk_index(index_name, flat_results, id_field="task_id")
        print(f"[OK] Indexed {count} results to OpenSearch index: {index_name}")

    def export_traces(
        self,
        trace_data: List[Dict],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export trace data to OpenSearch.

        Creates an index equivalent to the HF traces dataset with one
        document per trace (containing nested spans).
        """
        if not trace_data:
            print("[SKIP] No traces to export to OpenSearch.")
            return

        # Add run_id to each document
        for doc in trace_data:
            doc["run_id"] = run_id

        self._create_index_if_not_exists(index_name, TRACES_INDEX_MAPPING)
        count = self._bulk_index(index_name, trace_data, id_field="trace_id")
        print(f"[OK] Indexed {count} traces to OpenSearch index: {index_name}")

    def export_metrics(
        self,
        flat_metrics: List[Dict[str, Any]],
        model_name: str,
        run_id: str,
        index_name: str,
        **kwargs,
    ) -> None:
        """Export flattened metrics to OpenSearch.

        Creates an index equivalent to the HF metrics dataset with one
        document per timestamp (time-series data).
        """
        if not flat_metrics:
            # Create empty metrics document for API models (mirrors HF behavior)
            empty_doc = {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "service_name": "smoltrace-eval",
                "gpu_id": None,
                "gpu_name": None,
                "co2_emissions_gco2e": 0.0,
                "power_cost_usd": 0.0,
                "gpu_utilization_percent": 0.0,
                "gpu_memory_used_mib": 0.0,
                "gpu_memory_total_mib": 0.0,
                "gpu_temperature_celsius": 0.0,
                "gpu_power_watts": 0.0,
            }
            flat_metrics = [empty_doc]
            print(f"[INFO] Creating empty metrics index for API model (run_id: {run_id})")

        self._create_index_if_not_exists(index_name, METRICS_INDEX_MAPPING)
        count = self._bulk_index(index_name, flat_metrics)
        print(f"[OK] Indexed {count} metric time-series rows to OpenSearch index: {index_name}")

    def export_leaderboard(
        self,
        leaderboard_row: Dict[str, Any],
        index_name: str,
        **kwargs,
    ) -> None:
        """Export a leaderboard entry to OpenSearch.

        Appends to a persistent leaderboard index (equivalent to the
        HF leaderboard dataset). Uses run_id as document ID to allow
        upserts on re-runs.
        """
        self._create_index_if_not_exists(index_name, LEADERBOARD_INDEX_MAPPING)

        doc = _serialize_doc(leaderboard_row)
        doc_id = leaderboard_row.get("run_id", None)

        self.client.index(
            index=index_name,
            body=doc,
            id=doc_id,
            refresh="wait_for",
        )
        print(f"[OK] Indexed leaderboard entry to OpenSearch index: {index_name}")

    def export_all(
        self,
        flat_results: List[Dict[str, Any]],
        trace_data: List[Dict],
        flat_metrics: List[Dict[str, Any]],
        leaderboard_row: Dict[str, Any],
        model_name: str,
        run_id: str,
        timestamp: Optional[str] = None,
    ) -> Dict[str, str]:
        """Export all datasets to OpenSearch in one call.

        This is the primary entry point, equivalent to calling
        push_results_to_hf() + update_leaderboard() for the HF exporter.

        Args:
            flat_results: Flattened results from flatten_results_for_hf()
            trace_data: Raw trace data list
            flat_metrics: Flattened metrics from flatten_metrics_for_hf()
            leaderboard_row: Computed leaderboard row
            model_name: Model identifier
            run_id: Unique run identifier
            timestamp: Optional timestamp for index naming

        Returns:
            Dict mapping dataset type to index name
        """
        results_index = self._get_index_name("results", timestamp)
        traces_index = self._get_index_name("traces", timestamp)
        metrics_index = self._get_index_name("metrics", timestamp)
        leaderboard_index = self._get_index_name("leaderboard")

        # Add index references to leaderboard row (parallel to HF dataset refs)
        leaderboard_row["results_index"] = results_index
        leaderboard_row["traces_index"] = traces_index
        leaderboard_row["metrics_index"] = metrics_index

        self.export_results(flat_results, model_name, run_id, results_index)
        self.export_traces(trace_data, model_name, run_id, traces_index)
        self.export_metrics(flat_metrics, model_name, run_id, metrics_index)
        self.export_leaderboard(leaderboard_row, leaderboard_index)

        return {
            "results": results_index,
            "traces": traces_index,
            "metrics": metrics_index,
            "leaderboard": leaderboard_index,
        }


def _serialize_doc(doc: Dict) -> Dict:
    """Prepare a document for OpenSearch indexing.

    Converts non-serializable types (lists of dicts stored as strings, etc.)
    to proper types for OpenSearch.
    """
    serialized = {}
    for key, value in doc.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, (list, dict)):
            # Keep structured data as-is for OpenSearch nested/object types
            serialized[key] = value
        elif value is None:
            serialized[key] = None
        else:
            serialized[key] = value
    return serialized
