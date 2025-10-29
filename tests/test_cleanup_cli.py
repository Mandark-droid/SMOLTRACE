# tests/test_cleanup_cli.py
"""Tests for cleanup.py CLI functions."""

from unittest.mock import patch

import pytest

from smoltrace.cleanup import main, parse_older_than


class TestParseOlderThan:
    """Tests for parse_older_than function."""

    def test_parse_days_with_d_suffix(self):
        """Test parsing days with 'd' suffix."""
        assert parse_older_than("7d") == 7
        assert parse_older_than("30d") == 30
        assert parse_older_than("1d") == 1

    def test_parse_weeks_with_w_suffix(self):
        """Test parsing weeks with 'w' suffix."""
        assert parse_older_than("1w") == 7
        assert parse_older_than("2w") == 14
        assert parse_older_than("4w") == 28

    def test_parse_months_with_m_suffix(self):
        """Test parsing months with 'm' suffix."""
        assert parse_older_than("1m") == 30
        assert parse_older_than("2m") == 60
        assert parse_older_than("6m") == 180

    def test_parse_plain_number(self):
        """Test parsing plain numbers (defaults to days)."""
        assert parse_older_than("7") == 7
        assert parse_older_than("30") == 30
        assert parse_older_than("365") == 365

    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        assert parse_older_than("  7d  ") == 7
        assert parse_older_than("\t1w\n") == 7

    def test_parse_uppercase(self):
        """Test parsing uppercase formats."""
        assert parse_older_than("7D") == 7
        assert parse_older_than("1W") == 7
        assert parse_older_than("1M") == 30

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid --older-than format"):
            parse_older_than("abc")

        with pytest.raises(ValueError, match="Invalid --older-than format"):
            parse_older_than("7x")

        with pytest.raises(ValueError, match="Invalid --older-than format"):
            parse_older_than("")


class TestMainFunction:
    """Tests for main() CLI entry point."""

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("smoltrace.cleanup.os.getenv")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d", "--no-dry-run", "--yes"])
    def test_main_with_older_than(self, mock_getenv, mock_cleanup):
        """Test main with --older-than argument."""
        mock_getenv.return_value = "test_token"
        mock_cleanup.return_value = {"failed": []}

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_cleanup.assert_called_once()
        call_args = mock_cleanup.call_args[1]
        assert call_args["older_than_days"] == 7
        assert not call_args["dry_run"]

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("smoltrace.cleanup.os.getenv")
    @patch("sys.argv", ["smoltrace-cleanup", "--keep-recent", "5", "--no-dry-run", "--yes"])
    def test_main_with_keep_recent(self, mock_getenv, mock_cleanup):
        """Test main with --keep-recent argument."""
        mock_getenv.return_value = "test_token"
        mock_cleanup.return_value = {"failed": []}

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["keep_recent"] == 5

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("smoltrace.cleanup.os.getenv")
    @patch("sys.argv", ["smoltrace-cleanup", "--incomplete-only", "--no-dry-run", "--yes"])
    def test_main_with_incomplete_only(self, mock_getenv, mock_cleanup):
        """Test main with --incomplete-only argument."""
        mock_getenv.return_value = "test_token"
        mock_cleanup.return_value = {"failed": []}

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["incomplete_only"]

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d"])
    def test_main_default_dry_run(self, mock_cleanup):
        """Test that dry-run is enabled by default."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["dry_run"]

    @patch("sys.argv", ["smoltrace-cleanup"])
    def test_main_no_filter_exits_with_error(self):
        """Test that missing filter argument exits with error."""
        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d", "--no-dry-run"])
    def test_main_no_token_exits_with_error(self):
        """Test that missing token exits with error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch(
        "sys.argv",
        [
            "smoltrace-cleanup",
            "--older-than",
            "7d",
            "--token",
            "cli_token",
            "--no-dry-run",
            "--yes",
        ],
    )
    def test_main_token_from_cli_arg(self, mock_cleanup):
        """Test that token can be provided via CLI argument."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["hf_token"] == "cli_token"

    @patch("builtins.input", return_value="NO")
    @patch("sys.argv", ["smoltrace-cleanup", "--all", "--no-dry-run"])
    def test_main_all_requires_confirmation(self, mock_input):
        """Test that --all requires explicit confirmation."""
        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="YES DELETE ALL")
    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--all", "--no-dry-run"])
    def test_main_all_with_correct_confirmation(self, mock_cleanup, mock_input):
        """Test that --all works with correct confirmation."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        mock_cleanup.assert_called_once()

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--all", "--no-dry-run", "--yes"])
    def test_main_all_with_yes_flag(self, mock_cleanup):
        """Test that --all with --yes skips confirmation."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        mock_cleanup.assert_called_once()

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch(
        "sys.argv",
        ["smoltrace-cleanup", "--older-than", "7d", "--only", "results", "--no-dry-run", "--yes"],
    )
    def test_main_with_only_filter(self, mock_cleanup):
        """Test main with --only argument."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["only"] == "results"

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch(
        "sys.argv",
        [
            "smoltrace-cleanup",
            "--older-than",
            "7d",
            "--delete-leaderboard",
            "--no-dry-run",
            "--yes",
        ],
    )
    def test_main_with_delete_leaderboard(self, mock_cleanup):
        """Test main with --delete-leaderboard argument."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert not call_args["preserve_leaderboard"]

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d", "--no-dry-run", "--yes"])
    def test_main_preserve_leaderboard_by_default(self, mock_cleanup):
        """Test that leaderboard is preserved by default."""
        mock_cleanup.return_value = {"failed": []}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        call_args = mock_cleanup.call_args[1]
        assert call_args["preserve_leaderboard"]

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "invalid", "--no-dry-run", "--yes"])
    def test_main_invalid_older_than_format(self, mock_cleanup):
        """Test that invalid --older-than format exits with error."""
        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_cleanup.assert_not_called()

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d", "--no-dry-run", "--yes"])
    def test_main_cleanup_with_failures(self, mock_cleanup):
        """Test that main exits with code 1 if cleanup has failures."""
        mock_cleanup.return_value = {"failed": ["dataset1"]}

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    @patch("smoltrace.cleanup.cleanup_datasets")
    @patch("sys.argv", ["smoltrace-cleanup", "--older-than", "7d", "--no-dry-run", "--yes"])
    def test_main_cleanup_exception(self, mock_cleanup):
        """Test that main handles exceptions gracefully."""
        mock_cleanup.side_effect = Exception("Something went wrong")

        with patch.dict("os.environ", {"HF_TOKEN": "test_token"}):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
