# tests/test_dataset_card_upload.py
"""Test cases for dataset card upload functionality in smoltrace.utils."""

import os
import tempfile

from smoltrace.utils import upload_dataset_card


class TestUploadDatasetCard:
    """Test upload_dataset_card function."""

    def test_upload_success(self, mocker):
        """Test successful dataset card upload."""
        # Mock upload_file
        mock_upload = mocker.patch("smoltrace.utils.upload_file")

        card_content = "# Test Card\n\nThis is a test dataset card."
        result = upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content=card_content,
            token="test-token",
        )

        assert result is True
        mock_upload.assert_called_once()

        # Verify upload_file was called with correct parameters
        call_args = mock_upload.call_args
        assert call_args.kwargs["path_in_repo"] == "README.md"
        assert call_args.kwargs["repo_id"] == "testuser/test-dataset"
        assert call_args.kwargs["repo_type"] == "dataset"
        assert call_args.kwargs["token"] == "test-token"
        assert call_args.kwargs["commit_message"] == "Add SMOLTRACE dataset card"

    def test_upload_failure(self, mocker, capsys):
        """Test dataset card upload failure handling."""
        # Mock upload_file to raise an exception
        mocker.patch(
            "smoltrace.utils.upload_file",
            side_effect=Exception("Network error"),
        )

        result = upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content="# Test",
            token="test-token",
        )

        assert result is False

        # Check warning message was printed
        captured = capsys.readouterr()
        assert "[WARN]" in captured.out
        assert "Network error" in captured.out

    def test_upload_without_token(self, mocker):
        """Test upload without token uses None."""
        mock_upload = mocker.patch("smoltrace.utils.upload_file")

        result = upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content="# Test Card",
            token=None,
        )

        assert result is True
        call_args = mock_upload.call_args
        assert call_args.kwargs["token"] is None

    def test_temp_file_cleanup(self, mocker):
        """Test that temporary file is cleaned up after upload."""
        mocker.patch("smoltrace.utils.upload_file")  # Mock to prevent actual upload
        temp_files = []

        # Track temp file creation
        original_named_temp = tempfile.NamedTemporaryFile

        def track_temp_file(*args, **kwargs):
            # pylint: disable=consider-using-with
            f = original_named_temp(*args, **kwargs)
            temp_files.append(f.name)
            return f

        mocker.patch("tempfile.NamedTemporaryFile", side_effect=track_temp_file)

        upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content="# Test",
            token="test-token",
        )

        # Verify temp file was created and then deleted
        assert len(temp_files) == 1
        assert not os.path.exists(temp_files[0])  # File should be deleted

    def test_upload_with_unicode_content(self, mocker):
        """Test upload with unicode content in card."""
        mock_upload = mocker.patch("smoltrace.utils.upload_file")

        card_content = """# Test Card 🚀

Unicode content: émoji ñ 中文 日本語
"""
        result = upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content=card_content,
            token="test-token",
        )

        assert result is True
        mock_upload.assert_called_once()

    def test_upload_creates_md_file(self, mocker):
        """Test that upload creates a .md file."""
        created_files = []

        def capture_upload(path_or_fileobj, **_kwargs):
            created_files.append(path_or_fileobj)

        mocker.patch("smoltrace.utils.upload_file", side_effect=capture_upload)

        upload_dataset_card(
            repo_id="testuser/test-dataset",
            card_content="# Test",
            token="test-token",
        )

        assert len(created_files) == 1
        assert created_files[0].endswith(".md")


class TestUploadDatasetCardIntegration:
    """Integration tests for upload_dataset_card with other functions."""

    def test_card_upload_in_push_results_to_hf(self, mocker):
        """Test that push_results_to_hf calls upload_dataset_card."""
        from smoltrace.utils import push_results_to_hf

        # Mock all external calls
        mocker.patch("smoltrace.utils.login")
        mocker.patch("smoltrace.utils.Dataset.from_list")
        mock_ds = mocker.MagicMock()
        mocker.patch("smoltrace.utils.Dataset.from_list", return_value=mock_ds)
        mock_upload = mocker.patch("smoltrace.utils.upload_dataset_card", return_value=True)

        # Call push_results_to_hf
        push_results_to_hf(
            all_results={"tool": [], "code": []},
            trace_data=[],
            metric_data={},
            results_repo="testuser/results",
            traces_repo="testuser/traces",
            metrics_repo="testuser/metrics",
            model_name="test-model",
            hf_token="test-token",
            private=False,
            run_id="test-run",
            dataset_used="test-dataset",
            agent_type="both",
        )

        # Verify upload_dataset_card was called for results
        assert mock_upload.called
        # First call should be for results card
        first_call = mock_upload.call_args_list[0]
        assert first_call[0][0] == "testuser/results"

    def test_card_upload_in_update_leaderboard(self, mocker):
        """Test that update_leaderboard calls upload_dataset_card."""
        from smoltrace.utils import update_leaderboard

        # Mock external calls
        mocker.patch("smoltrace.utils.login")
        mocker.patch(
            "smoltrace.utils.load_dataset",
            side_effect=FileNotFoundError("Dataset not found"),
        )
        mock_ds = mocker.MagicMock()
        mocker.patch("smoltrace.utils.Dataset.from_list", return_value=mock_ds)
        mock_upload = mocker.patch("smoltrace.utils.upload_dataset_card", return_value=True)

        # Call update_leaderboard
        update_leaderboard(
            leaderboard_repo="testuser/smoltrace-leaderboard",
            new_row={"model": "test", "agent_type": "tool"},
            hf_token="test-token",
        )

        # Verify upload_dataset_card was called
        assert mock_upload.called
        call_args = mock_upload.call_args
        assert call_args[0][0] == "testuser/smoltrace-leaderboard"
