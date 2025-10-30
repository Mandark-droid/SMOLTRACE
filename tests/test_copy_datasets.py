"""Tests for dataset copy functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest

from smoltrace.utils import copy_standard_datasets


@pytest.fixture
def mock_hf_token():
    """Mock HF token."""
    return "hf_test_token_123"


@pytest.fixture
def mock_user_info():
    """Mock user info."""
    return {
        "username": "test_user",
        "type": "user",
        "fullname": "Test User",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_dataset():
    """Mock dataset."""
    mock_ds = MagicMock()
    mock_ds.__len__ = lambda self: 13
    return mock_ds


class TestCopyStandardDatasets:
    """Tests for copy_standard_datasets function."""

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_both_datasets_success(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test successful copy of both datasets."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        # Mock HfApi to simulate datasets don't exist
        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only=None,
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 2
        assert len(result["failed"]) == 0
        assert "test_user/smoltrace-benchmark-v1" in result["copied"]
        assert "test_user/smoltrace-tasks" in result["copied"]

        # Verify dataset loading was called
        assert mock_load_dataset.call_count == 2

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_only_benchmark(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test copying only benchmark dataset."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="benchmark",
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 1
        assert "test_user/smoltrace-benchmark-v1" in result["copied"]
        assert "test_user/smoltrace-tasks" not in result["copied"]

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_only_tasks(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test copying only tasks dataset."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 1
        assert "test_user/smoltrace-tasks" in result["copied"]
        assert "test_user/smoltrace-benchmark-v1" not in result["copied"]

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_with_existing_datasets(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test copying when datasets already exist (should overwrite)."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        # Mock HfApi to simulate datasets exist
        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.return_value = {"id": "test/dataset"}
        mock_hf_api.return_value = mock_api_instance

        # Execute with confirm=False to skip confirmation
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only=None,
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify - should still copy (overwrite)
        assert len(result["copied"]) == 2

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_with_private_flag(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test copying with private flag."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=True,  # Private flag
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 1
        # Verify push_to_hub was called with private=True
        mock_dataset.push_to_hub.assert_called_once()
        call_kwargs = mock_dataset.push_to_hub.call_args[1]
        assert call_kwargs["private"] is True

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_failure_loading_source(
        self, mock_hf_api, mock_load_dataset, mock_get_user_info, mock_hf_token, mock_user_info
    ):
        """Test handling of source dataset loading failure."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.side_effect = Exception("Failed to load source dataset")

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 0
        assert len(result["failed"]) == 1
        assert result["failed"][0]["dataset"] == "test_user/smoltrace-tasks"

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_failure_pushing_destination(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test handling of destination push failure."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset
        mock_dataset.push_to_hub.side_effect = Exception("Failed to push dataset")

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 0
        assert len(result["failed"]) == 1
        assert "Failed to push dataset" in result["failed"][0]["error"]

    @patch("smoltrace.utils.get_hf_user_info")
    @patch.dict(os.environ, {}, clear=True)  # Clear all env vars including HF_TOKEN
    def test_copy_no_token(self, mock_get_user_info):
        """Test error handling when no token provided."""
        # Execute and expect ValueError
        with pytest.raises(ValueError, match="HuggingFace token required"):
            copy_standard_datasets(
                source_user="kshitijthakkar",
                only=None,
                private=False,
                confirm=False,
                hf_token=None,
            )

    @patch("smoltrace.utils.get_hf_user_info")
    def test_copy_invalid_user_info(self, mock_get_user_info, mock_hf_token):
        """Test error handling when user info cannot be retrieved."""
        # Setup mock to return None
        mock_get_user_info.return_value = None

        # Execute and expect ValueError
        with pytest.raises(ValueError, match="Failed to get HuggingFace user info"):
            copy_standard_datasets(
                source_user="kshitijthakkar",
                only=None,
                private=False,
                confirm=False,
                hf_token=mock_hf_token,
            )

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    @patch("builtins.input")
    def test_copy_with_confirmation_cancelled(
        self,
        mock_input,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
    ):
        """Test cancellation when user doesn't confirm."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_input.return_value = "NO"  # User cancels

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute with confirm=True
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=False,
            confirm=True,  # Enable confirmation
            hf_token=mock_hf_token,
        )

        # Verify - nothing copied, everything skipped
        assert len(result["copied"]) == 0
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 1

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    @patch("builtins.input")
    def test_copy_with_confirmation_accepted(
        self,
        mock_input,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test successful copy when user confirms."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset
        mock_input.return_value = "COPY"  # User confirms

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute with confirm=True
        result = copy_standard_datasets(
            source_user="kshitijthakkar",
            only="tasks",
            private=False,
            confirm=True,  # Enable confirmation
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 1
        assert len(result["failed"]) == 0

    @patch("smoltrace.utils.get_hf_user_info")
    @patch("smoltrace.utils.load_dataset")
    @patch("smoltrace.utils.HfApi")
    def test_copy_custom_source_user(
        self,
        mock_hf_api,
        mock_load_dataset,
        mock_get_user_info,
        mock_hf_token,
        mock_user_info,
        mock_dataset,
    ):
        """Test copying from custom source user."""
        # Setup mocks
        mock_get_user_info.return_value = mock_user_info
        mock_load_dataset.return_value = mock_dataset

        mock_api_instance = MagicMock()
        mock_api_instance.dataset_info.side_effect = Exception("Dataset not found")
        mock_hf_api.return_value = mock_api_instance

        # Execute with custom source user
        result = copy_standard_datasets(
            source_user="custom_user",
            only="tasks",
            private=False,
            confirm=False,
            hf_token=mock_hf_token,
        )

        # Verify
        assert len(result["copied"]) == 1
        # Verify load_dataset was called with custom source
        mock_load_dataset.assert_called_once()
        source_dataset = mock_load_dataset.call_args[0][0]
        assert source_dataset == "custom_user/smoltrace-tasks"
