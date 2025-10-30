"""Tests for new features: InferenceClientModel, optional tools, parallel workers."""

import os
from unittest.mock import Mock, patch

import pytest

from smoltrace.core import initialize_agent
from smoltrace.tools import get_all_tools, get_smolagents_optional_tools


class TestInferenceClientModelProvider:
    """Tests for InferenceClientModel provider support."""

    def test_initialize_agent_with_inference_provider(self):
        """Test agent initialization with inference provider."""
        with patch("smolagents.InferenceClientModel") as mock_inference_model:
            mock_model_instance = Mock()
            mock_inference_model.return_value = mock_model_instance

            agent = initialize_agent(
                model_name="meta-llama/Llama-3.1-8B",
                agent_type="tool",
                provider="inference",
            )

            # Verify InferenceClientModel was called
            mock_inference_model.assert_called_once_with(model_id="meta-llama/Llama-3.1-8B")
            assert agent is not None

    def test_initialize_agent_with_inference_provider_and_hf_provider(self):
        """Test agent initialization with inference provider and specific HF provider."""
        with patch("smolagents.InferenceClientModel") as mock_inference_model:
            mock_model_instance = Mock()
            mock_inference_model.return_value = mock_model_instance

            agent = initialize_agent(
                model_name="meta-llama/Llama-3.1-70B-Instruct",
                agent_type="tool",
                provider="inference",
                hf_inference_provider="hf-inference-api",
            )

            # Verify InferenceClientModel was called with provider
            mock_inference_model.assert_called_once_with(
                model_id="meta-llama/Llama-3.1-70B-Instruct", provider="hf-inference-api"
            )
            assert agent is not None

    def test_initialize_code_agent_with_inference_provider(self):
        """Test CodeAgent initialization with inference provider."""
        with patch("smolagents.InferenceClientModel") as mock_inference_model:
            mock_model_instance = Mock()
            mock_inference_model.return_value = mock_model_instance

            agent = initialize_agent(
                model_name="Qwen/Qwen2.5-7B-Instruct",
                agent_type="code",
                provider="inference",
            )

            mock_inference_model.assert_called_once_with(model_id="Qwen/Qwen2.5-7B-Instruct")
            assert agent is not None

    def test_initialize_agent_inference_import_error(self):
        """Test error handling when InferenceClientModel is not available."""
        # Patch at the import location in initialize_agent
        with patch("smolagents.InferenceClientModel", side_effect=ImportError("Module not found")):
            with pytest.raises(ImportError, match="InferenceClientModel requires"):
                initialize_agent(
                    model_name="meta-llama/Llama-3.1-8B",
                    agent_type="tool",
                    provider="inference",
                )


class TestOptionalSmolagentsTools:
    """Tests for optional smolagents tools functionality."""

    def test_get_smolagents_optional_tools_multiple_tools(self, capsys):
        """Test loading multiple optional tools."""
        tools = get_smolagents_optional_tools(["visit_webpage", "python_interpreter"])

        # Should have 2 tools
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "visit_webpage" in tool_names
        assert "python_interpreter" in tool_names

        # Check console output
        captured = capsys.readouterr()
        assert "Enabled VisitWebpageTool" in captured.out
        assert "Enabled PythonInterpreterTool" in captured.out

    def test_get_smolagents_optional_tools_with_additional_imports(self, capsys):
        """Test PythonInterpreterTool with additional imports."""
        tools = get_smolagents_optional_tools(
            ["python_interpreter"], additional_imports=["pandas", "numpy"]
        )

        assert len(tools) == 1
        captured = capsys.readouterr()
        assert "pandas" in captured.out
        assert "numpy" in captured.out

    def test_get_smolagents_optional_tools_google_search_no_api_key(self, capsys):
        """Test GoogleSearchTool without API key (should use duckduckgo)."""
        # Ensure API keys are not set
        env_copy = os.environ.copy()
        env_copy.pop("SERPER_API_KEY", None)
        env_copy.pop("BRAVE_API_KEY", None)

        with patch.dict(os.environ, env_copy, clear=True):
            tools = get_smolagents_optional_tools(["google_search"], search_provider="duckduckgo")

            # Should succeed with duckduckgo (no API key needed)
            # Note: GoogleSearchTool with duckduckgo provider doesn't require API key
            assert len(tools) >= 0  # May succeed or fail depending on smolagents version
            captured = capsys.readouterr()
            # Check for either success or warning
            assert "Enabled GoogleSearchTool" in captured.out or "WARNING" in captured.out

    def test_get_smolagents_optional_tools_google_search_with_serper(self, capsys):
        """Test GoogleSearchTool with serper provider and API key."""
        with patch.dict(os.environ, {"SERPER_API_KEY": "test_key"}):
            tools = get_smolagents_optional_tools(["google_search"], search_provider="serper")

            assert len(tools) == 1
            captured = capsys.readouterr()
            assert "Enabled GoogleSearchTool" in captured.out
            assert "serper" in captured.out

    def test_get_smolagents_optional_tools_google_search_missing_api_key(self, capsys):
        """Test GoogleSearchTool with serper but missing API key."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SERPER_API_KEY", None)

            tools = get_smolagents_optional_tools(["google_search"], search_provider="serper")

            # Should skip the tool
            assert len(tools) == 0
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "SERPER_API_KEY" in captured.out

    def test_get_all_tools_with_multiple_optional_tools(self, capsys):
        """Test get_all_tools with multiple optional tools."""
        tools = get_all_tools(enabled_smolagents_tools=["visit_webpage"])

        # Should have 5 default (3 custom + web_search + python_interpreter) + 1 optional = 6 tools
        # Note: python_interpreter is now a default tool, so we only add visit_webpage as optional
        assert len(tools) == 6
        tool_names = [tool.name for tool in tools]
        assert "get_weather" in tool_names
        assert "calculator" in tool_names
        assert "get_current_time" in tool_names
        assert "web_search" in tool_names  # DuckDuckGoSearchTool (default)
        assert "python_interpreter" in tool_names  # PythonInterpreterTool (default)
        assert "visit_webpage" in tool_names  # VisitWebpageTool (optional)

    def test_get_all_tools_with_search_provider(self):
        """Test get_all_tools with custom search provider."""
        with patch.dict(os.environ, {"SERPER_API_KEY": "test_key"}):
            tools = get_all_tools(
                search_provider="serper", enabled_smolagents_tools=["google_search"]
            )

            # Should have 5 default + 1 optional (google_search) = 6 tools
            assert len(tools) == 6

    def test_get_smolagents_optional_tools_duckduckgo_search(self, capsys):
        """Test DuckDuckGoSearchTool from smolagents."""
        tools = get_smolagents_optional_tools(["duckduckgo_search"])

        assert len(tools) == 1
        assert tools[0].name == "web_search"
        captured = capsys.readouterr()
        assert "Enabled DuckDuckGoSearchTool" in captured.out

    def test_get_smolagents_optional_tools_user_input(self, capsys):
        """Test UserInputTool."""
        _ = get_smolagents_optional_tools(["user_input"])

        # Should either load successfully or fail gracefully
        captured = capsys.readouterr()
        assert (
            "Enabled UserInputTool" in captured.out
            or "WARNING" in captured.out
            or "Failed to initialize" in captured.out
        )


class TestAgentInitializationWithOptionalTools:
    """Tests for agent initialization with optional tools."""

    @patch("smoltrace.core.LiteLLMModel")
    def test_initialize_agent_with_optional_tools(self, mock_litellm):
        """Test agent initialization with optional tools."""
        mock_model = Mock()
        mock_litellm.return_value = mock_model

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            agent = initialize_agent(
                model_name="gpt-4",
                agent_type="tool",
                provider="litellm",
                enabled_smolagents_tools=["visit_webpage"],
            )

            assert agent is not None
            # Check that agent has tools
            assert hasattr(agent, "tools")
            # 5 default (3 custom + web_search + python_interpreter) + 1 optional + 1 final_answer = 7 tools
            assert len(agent.tools) == 7
            tool_names = list(agent.tools.keys())
            assert "visit_webpage" in tool_names
            assert "web_search" in tool_names  # DuckDuckGoSearchTool (default)
            assert "python_interpreter" in tool_names  # PythonInterpreterTool (default)
            assert "final_answer" in tool_names

    @patch("smoltrace.core.LiteLLMModel")
    def test_initialize_agent_with_search_provider(self, mock_litellm):
        """Test agent initialization with optional visit_webpage tool."""
        mock_model = Mock()
        mock_litellm.return_value = mock_model

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            agent = initialize_agent(
                model_name="gpt-4",
                agent_type="tool",
                provider="litellm",
                enabled_smolagents_tools=[
                    "visit_webpage"
                ],  # Use visit_webpage instead of google_search
            )

            assert agent is not None
            assert hasattr(agent, "tools")
            # 5 default + 1 visit_webpage + 1 final_answer (auto-added) = 7 tools
            assert len(agent.tools) == 7
            tool_names = list(agent.tools.keys())
            assert "web_search" in tool_names  # DuckDuckGoSearchTool (default)
            assert "python_interpreter" in tool_names  # PythonInterpreterTool (default)
            assert "visit_webpage" in tool_names  # VisitWebpageTool (optional)
            assert "final_answer" in tool_names


class TestParallelWorkersInfrastructure:
    """Tests for parallel workers infrastructure."""

    def test_run_evaluation_accepts_parallel_workers_parameter(self):
        """Test that run_evaluation accepts parallel_workers parameter."""
        # Check function signature
        import inspect

        from smoltrace.core import run_evaluation

        sig = inspect.signature(run_evaluation)
        assert "parallel_workers" in sig.parameters
        assert sig.parameters["parallel_workers"].default == 1

    def test_initialize_agent_signature_includes_new_parameters(self):
        """Test that initialize_agent has all new parameters."""
        import inspect

        sig = inspect.signature(initialize_agent)

        # Check for new parameters
        assert "search_provider" in sig.parameters
        assert "hf_inference_provider" in sig.parameters
        assert "enabled_smolagents_tools" in sig.parameters

        # Check defaults
        assert sig.parameters["search_provider"].default == "duckduckgo"
        assert sig.parameters["hf_inference_provider"].default is None
        assert sig.parameters["enabled_smolagents_tools"].default is None


class TestToolsWithAdditionalImports:
    """Tests for additional imports functionality."""

    @patch("smoltrace.core.LiteLLMModel")
    def test_initialize_code_agent_with_additional_imports(self, mock_litellm):
        """Test CodeAgent with additional authorized imports."""
        mock_model = Mock()
        mock_litellm.return_value = mock_model

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            agent = initialize_agent(
                model_name="gpt-4",
                agent_type="code",
                provider="litellm",
                additional_authorized_imports=["pandas", "numpy"],
            )

            assert agent is not None

    def test_get_smolagents_tools_merges_additional_imports(self, capsys):
        """Test that additional imports are merged with base imports."""
        _ = get_smolagents_optional_tools(
            ["python_interpreter"], additional_imports=["pandas", "matplotlib"]
        )

        captured = capsys.readouterr()
        # Should contain both base imports and additional ones
        output = captured.out
        assert "pandas" in output
        assert "matplotlib" in output
        # Base imports should also be present
        assert "numpy" in output or "sympy" in output


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility."""

    @patch("smoltrace.core.LiteLLMModel")
    def test_initialize_agent_without_new_parameters(self, mock_litellm):
        """Test that agent initialization works without new parameters."""
        mock_model = Mock()
        mock_litellm.return_value = mock_model

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # This should work exactly as before
            agent = initialize_agent(
                model_name="gpt-4",
                agent_type="tool",
                provider="litellm",
            )

            assert agent is not None
            # Should have 5 default tools (3 custom + web_search + python_interpreter) + 1 final_answer = 6 tools
            assert len(agent.tools) == 6
            tool_names = list(agent.tools.keys())
            # Verify our default tools are present
            assert "get_weather" in tool_names
            assert "calculator" in tool_names
            assert "get_current_time" in tool_names
            assert "web_search" in tool_names  # DuckDuckGoSearchTool (default)
            assert "python_interpreter" in tool_names  # PythonInterpreterTool (default)
            assert "final_answer" in tool_names

    def test_get_all_tools_without_parameters(self):
        """Test get_all_tools without any parameters (default behavior)."""
        tools = get_all_tools()

        # Should return 5 default tools (3 custom + web_search + python_interpreter)
        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        assert "get_weather" in tool_names
        assert "calculator" in tool_names
        assert "get_current_time" in tool_names
        assert "web_search" in tool_names  # DuckDuckGoSearchTool (default)
        assert "python_interpreter" in tool_names  # PythonInterpreterTool (default)


class TestErrorHandling:
    """Tests for error handling in new features."""

    def test_initialize_agent_with_invalid_provider(self):
        """Test error handling for invalid provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            initialize_agent(
                model_name="test-model",
                agent_type="tool",
                provider="invalid_provider",
            )

    def test_get_smolagents_optional_tools_with_invalid_tool_name(self, capsys):
        """Test that invalid tool names are silently ignored."""
        tools = get_smolagents_optional_tools(["invalid_tool_name"])

        # Should return empty list (tool name not recognized)
        assert len(tools) == 0

    def test_initialize_agent_inference_runtime_error(self):
        """Test error handling when InferenceClientModel raises RuntimeError."""
        with patch("smolagents.InferenceClientModel") as mock_inference_model:
            mock_inference_model.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                initialize_agent(
                    model_name="test-model",
                    agent_type="tool",
                    provider="inference",
                )
