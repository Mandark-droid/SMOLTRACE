# tests/test_cards.py
"""Test cases for smoltrace.cards module - Dataset card generation with SMOLTRACE branding."""

import importlib.util
from pathlib import Path

import pytest

# Load cards module directly without going through smoltrace __init__.py
# This avoids the otel/cryptography dependency chain issues in test environments
_cards_path = Path(__file__).parent.parent / "smoltrace" / "cards.py"
_spec = importlib.util.spec_from_file_location("cards", _cards_path)
_cards = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cards)

# Import functions from loaded module
SMOLTRACE_DOCS_URL = _cards.SMOLTRACE_DOCS_URL
SMOLTRACE_LOGO_URL = _cards.SMOLTRACE_LOGO_URL
SMOLTRACE_PYPI_URL = _cards.SMOLTRACE_PYPI_URL
SMOLTRACE_REPO_URL = _cards.SMOLTRACE_REPO_URL
generate_benchmark_card = _cards.generate_benchmark_card
generate_leaderboard_card = _cards.generate_leaderboard_card
generate_metrics_card = _cards.generate_metrics_card
generate_results_card = _cards.generate_results_card
generate_tasks_card = _cards.generate_tasks_card
generate_traces_card = _cards.generate_traces_card


class TestBrandingConstants:
    """Test branding constants are correctly defined."""

    def test_logo_url_is_github_raw(self):
        """Test logo URL points to GitHub raw content."""
        assert "raw.githubusercontent.com" in SMOLTRACE_LOGO_URL
        assert "Logo.png" in SMOLTRACE_LOGO_URL
        assert "Mandark-droid/SMOLTRACE" in SMOLTRACE_LOGO_URL

    def test_repo_url_is_github(self):
        """Test repo URL points to GitHub."""
        assert "github.com/Mandark-droid/SMOLTRACE" in SMOLTRACE_REPO_URL

    def test_pypi_url_is_pypi(self):
        """Test PyPI URL points to pypi.org."""
        assert "pypi.org/project/smoltrace" in SMOLTRACE_PYPI_URL

    def test_docs_url_exists(self):
        """Test documentation URL is defined."""
        assert SMOLTRACE_DOCS_URL is not None
        assert len(SMOLTRACE_DOCS_URL) > 0


class TestGenerateResultsCard:
    """Test generate_results_card function."""

    def test_basic_generation(self):
        """Test basic results card generation."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_results=10,
        )

        assert isinstance(card, str)
        assert len(card) > 1000  # Should be substantial content

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_results=10,
        )

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card
        assert "Tiny Agents. Total Visibility." in card

    def test_contains_metadata(self):
        """Test card contains dataset metadata."""
        card = generate_results_card(
            model_name="claude-3-opus",
            run_id="run-456",
            num_results=50,
            agent_type="tool",
            dataset_used="test-benchmark",
        )

        assert "claude-3-opus" in card
        assert "run-456" in card
        assert "50" in card
        assert "tool" in card
        assert "test-benchmark" in card

    def test_contains_schema_documentation(self):
        """Test card contains schema documentation."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run",
            num_results=10,
        )

        # Check for schema columns
        assert "model" in card
        assert "task_id" in card
        assert "success" in card
        assert "trace_id" in card
        assert "execution_time_ms" in card

    def test_contains_yaml_frontmatter(self):
        """Test card contains YAML frontmatter."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run",
            num_results=10,
        )

        assert card.startswith("---")
        assert "license: agpl-3.0" in card
        assert "tags:" in card
        assert "smoltrace" in card

    def test_contains_usage_example(self):
        """Test card contains usage example."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run",
            num_results=10,
        )

        assert "from datasets import load_dataset" in card
        assert "```python" in card

    def test_default_agent_type(self):
        """Test default agent type is 'both'."""
        card = generate_results_card(
            model_name="gpt-4",
            run_id="test-run",
            num_results=10,
        )

        assert "both" in card


class TestGenerateTracesCard:
    """Test generate_traces_card function."""

    def test_basic_generation(self):
        """Test basic traces card generation."""
        card = generate_traces_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_traces=5,
        )

        assert isinstance(card, str)
        assert len(card) > 1000

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_traces_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_traces=5,
        )

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card

    def test_contains_trace_schema(self):
        """Test card contains trace schema documentation."""
        card = generate_traces_card(
            model_name="gpt-4",
            run_id="test-run",
            num_traces=5,
        )

        assert "trace_id" in card
        assert "span_id" in card
        assert "span_name" in card
        assert "duration_ms" in card

    def test_contains_otel_info(self):
        """Test card contains OpenTelemetry information."""
        card = generate_traces_card(
            model_name="gpt-4",
            run_id="test-run",
            num_traces=5,
        )

        assert "OpenTelemetry" in card

    def test_contains_metadata(self):
        """Test card contains trace metadata."""
        card = generate_traces_card(
            model_name="llama-3-70b",
            run_id="trace-run-789",
            num_traces=100,
        )

        assert "llama-3-70b" in card
        assert "trace-run-789" in card
        assert "100" in card


class TestGenerateMetricsCard:
    """Test generate_metrics_card function."""

    def test_basic_generation_with_gpu(self):
        """Test basic metrics card generation with GPU metrics."""
        card = generate_metrics_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_metrics=100,
            has_gpu_metrics=True,
        )

        assert isinstance(card, str)
        assert len(card) > 1000

    def test_basic_generation_without_gpu(self):
        """Test metrics card generation without GPU metrics."""
        card = generate_metrics_card(
            model_name="gpt-4",
            run_id="test-run-123",
            num_metrics=1,
            has_gpu_metrics=False,
        )

        assert isinstance(card, str)
        assert "N/A (API Model)" in card

    def test_contains_gpu_schema(self):
        """Test card contains GPU metrics schema."""
        card = generate_metrics_card(
            model_name="gpt-4",
            run_id="test-run",
            num_metrics=100,
            has_gpu_metrics=True,
        )

        assert "gpu_utilization_percent" in card
        assert "gpu_memory_used_mib" in card
        assert "gpu_temperature_celsius" in card
        assert "gpu_power_watts" in card

    def test_contains_environmental_metrics(self):
        """Test card contains environmental metrics."""
        card = generate_metrics_card(
            model_name="gpt-4",
            run_id="test-run",
            num_metrics=100,
            has_gpu_metrics=True,
        )

        assert "co2_emissions_gco2e" in card
        assert "power_cost_usd" in card
        assert "Environmental Impact" in card

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_metrics_card(
            model_name="gpt-4",
            run_id="test-run",
            num_metrics=100,
            has_gpu_metrics=True,
        )

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card


class TestGenerateLeaderboardCard:
    """Test generate_leaderboard_card function."""

    def test_basic_generation(self):
        """Test basic leaderboard card generation."""
        card = generate_leaderboard_card(username="testuser")

        assert isinstance(card, str)
        assert len(card) > 1000

    def test_contains_username(self):
        """Test card contains username."""
        card = generate_leaderboard_card(username="myuser123")

        assert "myuser123" in card

    def test_contains_performance_metrics(self):
        """Test card contains performance metrics schema."""
        card = generate_leaderboard_card(username="testuser")

        assert "success_rate" in card
        assert "avg_steps" in card
        assert "total_tokens" in card
        assert "total_cost_usd" in card

    def test_contains_identification_fields(self):
        """Test card contains identification fields."""
        card = generate_leaderboard_card(username="testuser")

        assert "run_id" in card
        assert "model" in card
        assert "agent_type" in card
        assert "provider" in card

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_leaderboard_card(username="testuser")

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card


class TestGenerateBenchmarkCard:
    """Test generate_benchmark_card function."""

    def test_basic_generation(self):
        """Test basic benchmark card generation."""
        card = generate_benchmark_card(
            username="testuser",
            num_cases=132,
            source_user="kshitijthakkar",
        )

        assert isinstance(card, str)
        assert len(card) > 1000

    def test_contains_metadata(self):
        """Test card contains benchmark metadata."""
        card = generate_benchmark_card(
            username="myuser",
            num_cases=132,
            source_user="sourceuser",
        )

        assert "myuser" in card
        assert "132" in card
        assert "sourceuser" in card

    def test_contains_difficulty_info(self):
        """Test card contains difficulty distribution info."""
        card = generate_benchmark_card(
            username="testuser",
            num_cases=132,
            source_user="kshitijthakkar",
        )

        assert "Easy" in card
        assert "Medium" in card
        assert "Hard" in card

    def test_contains_usage_instructions(self):
        """Test card contains usage instructions."""
        card = generate_benchmark_card(
            username="testuser",
            num_cases=132,
            source_user="kshitijthakkar",
        )

        assert "smoltrace-eval" in card
        assert "--model" in card

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_benchmark_card(
            username="testuser",
            num_cases=132,
            source_user="kshitijthakkar",
        )

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card


class TestGenerateTasksCard:
    """Test generate_tasks_card function."""

    def test_basic_generation(self):
        """Test basic tasks card generation."""
        card = generate_tasks_card(
            username="testuser",
            num_cases=13,
            source_user="kshitijthakkar",
        )

        assert isinstance(card, str)
        assert len(card) > 1000

    def test_contains_metadata(self):
        """Test card contains tasks metadata."""
        card = generate_tasks_card(
            username="myuser",
            num_cases=13,
            source_user="sourceuser",
        )

        assert "myuser" in card
        assert "13" in card
        assert "sourceuser" in card

    def test_describes_lightweight_purpose(self):
        """Test card describes lightweight purpose."""
        card = generate_tasks_card(
            username="testuser",
            num_cases=13,
            source_user="kshitijthakkar",
        )

        # Should mention it's for quick evaluations
        assert "quick" in card.lower() or "lightweight" in card.lower()

    def test_contains_branding(self):
        """Test card contains SMOLTRACE branding."""
        card = generate_tasks_card(
            username="testuser",
            num_cases=13,
            source_user="kshitijthakkar",
        )

        assert SMOLTRACE_LOGO_URL in card
        assert "SMOLTRACE" in card


class TestCardFooter:
    """Test that all cards contain proper footer with links."""

    @pytest.mark.parametrize(
        "card_func,args",
        [
            (generate_results_card, {"model_name": "gpt-4", "run_id": "test", "num_results": 10}),
            (generate_traces_card, {"model_name": "gpt-4", "run_id": "test", "num_traces": 5}),
            (
                generate_metrics_card,
                {
                    "model_name": "gpt-4",
                    "run_id": "test",
                    "num_metrics": 100,
                    "has_gpu_metrics": True,
                },
            ),
            (generate_leaderboard_card, {"username": "testuser"}),
            (
                generate_benchmark_card,
                {"username": "testuser", "num_cases": 132, "source_user": "source"},
            ),
            (
                generate_tasks_card,
                {"username": "testuser", "num_cases": 13, "source_user": "source"},
            ),
        ],
    )
    def test_contains_footer_links(self, card_func, args):
        """Test all cards contain footer links."""
        card = card_func(**args)

        # Check for GitHub link
        assert SMOLTRACE_REPO_URL in card

        # Check for installation instructions
        assert "pip install smoltrace" in card

        # Check for citation info
        assert "Citation" in card or "citation" in card or "bibtex" in card.lower()


class TestCardYAMLFrontmatter:
    """Test YAML frontmatter in all cards."""

    @pytest.mark.parametrize(
        "card_func,args",
        [
            (generate_results_card, {"model_name": "gpt-4", "run_id": "test", "num_results": 10}),
            (generate_traces_card, {"model_name": "gpt-4", "run_id": "test", "num_traces": 5}),
            (
                generate_metrics_card,
                {
                    "model_name": "gpt-4",
                    "run_id": "test",
                    "num_metrics": 100,
                    "has_gpu_metrics": True,
                },
            ),
            (generate_leaderboard_card, {"username": "testuser"}),
            (
                generate_benchmark_card,
                {"username": "testuser", "num_cases": 132, "source_user": "source"},
            ),
            (
                generate_tasks_card,
                {"username": "testuser", "num_cases": 13, "source_user": "source"},
            ),
        ],
    )
    def test_starts_with_yaml_frontmatter(self, card_func, args):
        """Test all cards start with YAML frontmatter."""
        card = card_func(**args)

        assert card.startswith("---")
        assert "license:" in card
        assert "tags:" in card
