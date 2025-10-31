# tests/test_cleanup.py
"""Tests for dataset cleanup functionality."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from smoltrace.utils import (
    cleanup_datasets,
    delete_datasets,
    discover_smoltrace_datasets,
    filter_runs,
    group_datasets_by_run,
)


class TestDiscoverDatasets:
    """Tests for discover_smoltrace_datasets function."""

    def test_discover_empty(self, mocker):
        """Test discovery when user has no datasets."""
        mock_api = mocker.patch("smoltrace.utils.HfApi")
        mock_api.return_value.list_datasets.return_value = []

        result = discover_smoltrace_datasets("test_user", "token")

        assert result == {"results": [], "traces": [], "metrics": [], "leaderboard": []}

    def test_discover_smoltrace_datasets(self, mocker):
        """Test discovery of SMOLTRACE datasets."""
        # Mock dataset objects
        mock_datasets = [
            Mock(
                id="test_user/smoltrace-results-20250115_120000",
                created_at=datetime.now(),
                private=False,
            ),
            Mock(
                id="test_user/smoltrace-traces-20250115_120000",
                created_at=datetime.now(),
                private=False,
            ),
            Mock(
                id="test_user/smoltrace-metrics-20250115_120000",
                created_at=datetime.now(),
                private=False,
            ),
            Mock(
                id="test_user/smoltrace-results-20250116_140000",
                created_at=datetime.now(),
                private=False,
            ),
            Mock(id="test_user/smoltrace-leaderboard", created_at=datetime.now(), private=False),
            Mock(
                id="test_user/other-dataset", created_at=datetime.now(), private=False
            ),  # Should be ignored
        ]

        mock_api = mocker.patch("smoltrace.utils.HfApi")
        mock_api.return_value.list_datasets.return_value = mock_datasets

        result = discover_smoltrace_datasets("test_user", "token")

        assert len(result["results"]) == 2
        assert len(result["traces"]) == 1
        assert len(result["metrics"]) == 1
        assert len(result["leaderboard"]) == 1

    def test_discover_handles_errors(self, mocker):
        """Test that errors are handled gracefully."""
        mock_api = mocker.patch("smoltrace.utils.HfApi")
        mock_api.return_value.list_datasets.side_effect = Exception("API Error")

        result = discover_smoltrace_datasets("test_user", "token")

        assert result == {"results": [], "traces": [], "metrics": [], "leaderboard": []}


class TestGroupDatasetsByRun:
    """Tests for group_datasets_by_run function."""

    def test_group_complete_run(self):
        """Test grouping a complete run with all 3 datasets."""
        datasets = {
            "results": [{"name": "user/smoltrace-results-20250115_120000"}],
            "traces": [{"name": "user/smoltrace-traces-20250115_120000"}],
            "metrics": [{"name": "user/smoltrace-metrics-20250115_120000"}],
            "leaderboard": [],
        }

        runs = group_datasets_by_run(datasets)

        assert len(runs) == 1
        assert runs[0]["timestamp"] == "20250115_120000"
        assert runs[0]["complete"]
        assert runs[0]["results"] == "user/smoltrace-results-20250115_120000"
        assert runs[0]["traces"] == "user/smoltrace-traces-20250115_120000"
        assert runs[0]["metrics"] == "user/smoltrace-metrics-20250115_120000"

    def test_group_incomplete_run(self):
        """Test grouping an incomplete run (missing metrics)."""
        datasets = {
            "results": [{"name": "user/smoltrace-results-20250115_120000"}],
            "traces": [{"name": "user/smoltrace-traces-20250115_120000"}],
            "metrics": [],  # Missing
            "leaderboard": [],
        }

        runs = group_datasets_by_run(datasets)

        assert len(runs) == 1
        assert not runs[0]["complete"]

    def test_group_multiple_runs(self):
        """Test grouping multiple runs."""
        datasets = {
            "results": [
                {"name": "user/smoltrace-results-20250115_120000"},
                {"name": "user/smoltrace-results-20250116_140000"},
            ],
            "traces": [
                {"name": "user/smoltrace-traces-20250115_120000"},
                {"name": "user/smoltrace-traces-20250116_140000"},
            ],
            "metrics": [
                {"name": "user/smoltrace-metrics-20250115_120000"},
                {"name": "user/smoltrace-metrics-20250116_140000"},
            ],
            "leaderboard": [],
        }

        runs = group_datasets_by_run(datasets)

        assert len(runs) == 2
        # Should be sorted by datetime (newest first)
        assert runs[0]["timestamp"] == "20250116_140000"
        assert runs[1]["timestamp"] == "20250115_120000"


class TestFilterRuns:
    """Tests for filter_runs function."""

    def test_filter_older_than(self):
        """Test filtering by older_than_days."""
        now = datetime.now()
        runs = [
            {"timestamp": "20250123_120000", "datetime": now - timedelta(days=1), "complete": True},
            {"timestamp": "20250120_120000", "datetime": now - timedelta(days=4), "complete": True},
            {"timestamp": "20250115_120000", "datetime": now - timedelta(days=9), "complete": True},
            {
                "timestamp": "20250110_120000",
                "datetime": now - timedelta(days=14),
                "complete": True,
            },
        ]

        to_delete, to_keep = filter_runs(runs, older_than_days=7)

        assert len(to_delete) == 2  # 9 days and 14 days old
        assert len(to_keep) == 2  # 1 day and 4 days old

    def test_filter_keep_recent(self):
        """Test filtering by keep_recent."""
        now = datetime.now()
        runs = [
            {"timestamp": "20250123_120000", "datetime": now - timedelta(days=1)},
            {"timestamp": "20250122_120000", "datetime": now - timedelta(days=2)},
            {"timestamp": "20250121_120000", "datetime": now - timedelta(days=3)},
            {"timestamp": "20250120_120000", "datetime": now - timedelta(days=4)},
            {"timestamp": "20250119_120000", "datetime": now - timedelta(days=5)},
        ]

        to_delete, to_keep = filter_runs(runs, keep_recent=3)

        assert len(to_keep) == 3  # Keep 3 most recent
        assert len(to_delete) == 2  # Delete the rest

    def test_filter_incomplete_only(self):
        """Test filtering incomplete runs only."""
        runs = [
            {"timestamp": "20250123_120000", "complete": True},
            {"timestamp": "20250122_120000", "complete": False},
            {"timestamp": "20250121_120000", "complete": True},
            {"timestamp": "20250120_120000", "complete": False},
        ]

        to_delete, to_keep = filter_runs(runs, incomplete_only=True)

        assert len(to_delete) == 2  # 2 incomplete runs
        assert len(to_keep) == 2  # 2 complete runs

    def test_filter_no_criteria(self):
        """Test that no filter returns all as kept."""
        runs = [
            {"timestamp": "20250123_120000"},
            {"timestamp": "20250122_120000"},
        ]

        to_delete, to_keep = filter_runs(runs)

        assert len(to_delete) == 0
        assert len(to_keep) == 2


class TestDeleteDatasets:
    """Tests for delete_datasets function."""

    def test_dry_run_no_deletion(self, mocker):
        """Test that dry-run doesn't actually delete."""
        mock_api = mocker.patch("smoltrace.utils.HfApi")
        datasets = ["user/smoltrace-results-20250115_120000"]

        result = delete_datasets(datasets, dry_run=True, hf_token="token")

        assert len(result["deleted"]) == 0
        assert len(result["failed"]) == 0
        mock_api.return_value.delete_repo.assert_not_called()

    def test_actual_deletion(self, mocker):
        """Test actual deletion."""
        mock_api = mocker.patch("smoltrace.utils.HfApi")
        datasets = [
            "user/smoltrace-results-20250115_120000",
            "user/smoltrace-traces-20250115_120000",
        ]

        result = delete_datasets(datasets, dry_run=False, hf_token="token")

        assert len(result["deleted"]) == 2
        assert len(result["failed"]) == 0
        assert mock_api.return_value.delete_repo.call_count == 2

    def test_deletion_with_errors(self, mocker):
        """Test deletion with some failures."""
        mock_api = mocker.patch("smoltrace.utils.HfApi")
        mock_api.return_value.delete_repo.side_effect = [
            None,  # First deletion succeeds
            Exception("Repository not found"),  # Second deletion fails
        ]

        datasets = [
            "user/smoltrace-results-20250115_120000",
            "user/smoltrace-traces-20250115_120000",
        ]

        result = delete_datasets(datasets, dry_run=False, hf_token="token")

        assert len(result["deleted"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["error"] == "Repository not found"


class TestCleanupDatasets:
    """Tests for main cleanup_datasets function."""

    def test_cleanup_requires_token(self, mocker):
        """Test that cleanup requires a token."""
        # Mock os.getenv to return None (no token in environment)
        mocker.patch("smoltrace.utils.os.getenv", return_value=None)

        with pytest.raises(ValueError, match="HuggingFace token required"):
            cleanup_datasets(older_than_days=7, hf_token=None)

    def test_cleanup_dry_run(self, mocker):
        """Test cleanup in dry-run mode."""
        mocker.patch("smoltrace.utils.os.getenv", return_value="test_token")
        mock_get_user_info = mocker.patch("smoltrace.utils.get_hf_user_info")
        mock_get_user_info.return_value = {"username": "test_user"}

        mock_discover = mocker.patch("smoltrace.utils.discover_smoltrace_datasets")
        mock_discover.return_value = {
            "results": [{"name": "test_user/smoltrace-results-20250115_120000"}],
            "traces": [{"name": "test_user/smoltrace-traces-20250115_120000"}],
            "metrics": [{"name": "test_user/smoltrace-metrics-20250115_120000"}],
            "leaderboard": [],
        }

        mock_group = mocker.patch("smoltrace.utils.group_datasets_by_run")
        now = datetime.now()
        mock_group.return_value = [
            {
                "timestamp": "20250115_120000",
                "datetime": now - timedelta(days=10),
                "results": "test_user/smoltrace-results-20250115_120000",
                "traces": "test_user/smoltrace-traces-20250115_120000",
                "metrics": "test_user/smoltrace-metrics-20250115_120000",
                "complete": True,
            }
        ]

        result = cleanup_datasets(
            older_than_days=7,
            dry_run=True,
            hf_token="test_token",
        )

        assert result["total_deleted"] == 0  # Dry-run doesn't delete
        assert result["total_scanned"] == 1


class TestCleanupWithConfirmation:
    """Tests for cleanup_datasets with confirmation flow."""

    def test_cleanup_with_confirmation_accepted(self, mocker):
        """Test cleanup with user confirmation accepted."""
        # Mock user input to confirm deletion
        mocker.patch("builtins.input", return_value="DELETE")
        mocker.patch("smoltrace.utils.get_hf_user_info", return_value={"username": "test_user"})

        # Mock dependencies
        mock_discover = mocker.patch("smoltrace.utils.discover_smoltrace_datasets")
        mock_discover.return_value = {
            "results": [{"name": "test_user/smoltrace-results-20250101_120000"}],
            "traces": [{"name": "test_user/smoltrace-traces-20250101_120000"}],
            "metrics": [{"name": "test_user/smoltrace-metrics-20250101_120000"}],
            "leaderboard": [],
        }

        mock_group = mocker.patch("smoltrace.utils.group_datasets_by_run")
        now = datetime.now()
        mock_group.return_value = [
            {
                "timestamp": "20250101_120000",
                "datetime": now - timedelta(days=10),
                "results": "test_user/smoltrace-results-20250101_120000",
                "traces": "test_user/smoltrace-traces-20250101_120000",
                "metrics": "test_user/smoltrace-metrics-20250101_120000",
                "complete": True,
            }
        ]

        mock_delete = mocker.patch("smoltrace.utils.delete_datasets")
        mock_delete.return_value = {
            "deleted": [
                "test_user/smoltrace-results-20250101_120000",
                "test_user/smoltrace-traces-20250101_120000",
                "test_user/smoltrace-metrics-20250101_120000",
            ],
            "failed": [],
        }

        # Execute with confirmation
        result = cleanup_datasets(
            older_than_days=7,
            hf_token="test_token",
            dry_run=False,
            confirm=True,  # Requires confirmation
            preserve_leaderboard=True,
        )

        # Verify deletion occurred
        assert result["total_deleted"] == 3
        assert len(result["deleted"]) == 3
        assert len(result["failed"]) == 0

    def test_cleanup_with_confirmation_rejected(self, mocker):
        """Test cleanup with user confirmation rejected."""
        # Mock user input to REJECT deletion
        mocker.patch("builtins.input", return_value="NO")
        mocker.patch("smoltrace.utils.get_hf_user_info", return_value={"username": "test_user"})

        mock_discover = mocker.patch("smoltrace.utils.discover_smoltrace_datasets")
        mock_discover.return_value = {
            "results": [{"name": "test_user/smoltrace-results-20250101_120000"}],
            "traces": [],
            "metrics": [],
            "leaderboard": [],
        }

        mock_group = mocker.patch("smoltrace.utils.group_datasets_by_run")
        now = datetime.now()
        mock_group.return_value = [
            {
                "timestamp": "20250101_120000",
                "datetime": now - timedelta(days=10),
                "results": "test_user/smoltrace-results-20250101_120000",
                "traces": None,  # No traces dataset
                "metrics": None,  # No metrics dataset
                "complete": False,
            }
        ]

        # Execute with confirmation (will be rejected)
        result = cleanup_datasets(
            older_than_days=7,
            hf_token="test_token",
            dry_run=False,
            confirm=True,  # User will reject
        )

        # Verify nothing was deleted (user rejected)
        assert result["total_deleted"] == 0
        assert len(result["deleted"]) == 0
        assert len(result["failed"]) == 0

    def test_cleanup_with_deletion_failures(self, mocker):
        """Test cleanup when some deletions fail."""
        mocker.patch("builtins.input", return_value="DELETE")
        mocker.patch("smoltrace.utils.get_hf_user_info", return_value={"username": "test_user"})

        mock_discover = mocker.patch("smoltrace.utils.discover_smoltrace_datasets")
        mock_discover.return_value = {
            "results": [{"name": "test_user/smoltrace-results-20250101_120000"}],
            "traces": [{"name": "test_user/smoltrace-traces-20250101_120000"}],
            "metrics": [],
            "leaderboard": [],
        }

        mock_group = mocker.patch("smoltrace.utils.group_datasets_by_run")
        now = datetime.now()
        mock_group.return_value = [
            {
                "timestamp": "20250101_120000",
                "datetime": now - timedelta(days=10),
                "results": "test_user/smoltrace-results-20250101_120000",
                "traces": "test_user/smoltrace-traces-20250101_120000",
                "metrics": None,  # No metrics dataset
                "complete": True,
            }
        ]

        mock_delete = mocker.patch("smoltrace.utils.delete_datasets")
        # Simulate one success, one failure
        mock_delete.return_value = {
            "deleted": ["test_user/smoltrace-results-20250101_120000"],
            "failed": [
                {
                    "dataset": "test_user/smoltrace-traces-20250101_120000",
                    "error": "Permission denied",
                }
            ],
        }

        # Execute
        result = cleanup_datasets(
            older_than_days=7,
            hf_token="test_token",
            dry_run=False,
            confirm=True,
        )

        # Verify partial success
        assert result["total_deleted"] == 1
        assert len(result["deleted"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["dataset"] == "test_user/smoltrace-traces-20250101_120000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
