"""0.2.11: generation settings that reach the model, Brave/Tavily search, the litellm key gate.

Pure unit tests: they assert the kwargs handed to the model constructors and which search tool is
built. No network.
"""

import argparse
import json
import sys
import types

import pytest

from smoltrace import core, generation, tools
from smoltrace.generation import (
    finalize_chat_template,
    generation_settings_from_args,
    litellm_key_status,
    normalize_generation_settings,
    plan_generation,
)
from smoltrace.utils import build_status_row, generation_settings_field

ALL_SETTINGS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 40,
    "max_new_tokens": 256,
    "reasoning_effort": "low",
    "enable_thinking": False,
}
API_KEY_NAMES = (
    "LITELLM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "TOGETHER_API_KEY",
    "TOGETHERAI_API_KEY",
    "OPENROUTER_API_KEY",
    "NEBIUS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
)


@pytest.fixture
def no_keys(monkeypatch):
    """An environment with no provider key at all."""
    import os

    for name in list(os.environ):
        if name.endswith("_API_KEY") or name in ("OPENAI_API_BASE", "OPENAI_BASE_URL"):
            monkeypatch.delenv(name, raising=False)
    return monkeypatch


# --- validation --------------------------------------------------------------------------------


def test_normalize_drops_unset_and_keeps_types():
    assert normalize_generation_settings(None) == {}
    assert normalize_generation_settings({"temperature": None, "top_k": "40"}) == {"top_k": 40}
    assert normalize_generation_settings({"enable_thinking": "true"}) == {"enable_thinking": True}
    assert normalize_generation_settings({"reasoning_effort": "HIGH"}) == {
        "reasoning_effort": "high"
    }


@pytest.mark.parametrize(
    "settings",
    [
        {"temperature": -0.1},
        {"top_p": 0},
        {"top_p": 1.5},
        {"top_k": 0},
        {"top_k": 1.5},
        {"max_new_tokens": 0},
        {"reasoning_effort": "extreme"},
        {"enable_thinking": "maybe"},
        {"frequency_penalty": 1},
    ],
)
def test_normalize_refuses_bad_values(settings):
    with pytest.raises(ValueError):
        normalize_generation_settings(settings)


def test_settings_from_args_ignores_absent_and_non_primitive_values():
    args = argparse.Namespace(temperature=0.2, top_p=None, enable_thinking="false", top_k=object())
    assert generation_settings_from_args(args) == {"temperature": 0.2, "enable_thinking": False}


# --- per-provider mapping ----------------------------------------------------------------------


def test_litellm_openai_compatible_gets_every_setting_it_supports(no_keys):
    plan = plan_generation("litellm", "hosted_vllm/qwen3", ALL_SETTINGS)
    assert plan.model_kwargs == {
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 256,
        "top_k": 40,
        "reasoning_effort": "low",
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
    assert plan.not_applied == {}
    assert plan.applied == ALL_SETTINGS


def test_litellm_reports_what_the_model_does_not_support(no_keys):
    plan = plan_generation("litellm", "openai/gpt-4.1-nano", ALL_SETTINGS)
    assert plan.model_kwargs == {"temperature": 0.3, "top_p": 0.9, "max_tokens": 256}
    assert set(plan.not_applied) == {"top_k", "reasoning_effort", "enable_thinking"}
    assert "no top_k" in plan.not_applied["top_k"]
    assert "--reasoning-effort" in plan.not_applied["enable_thinking"]


def test_litellm_openai_prefix_on_a_custom_endpoint_keeps_top_k_and_thinking(no_keys):
    no_keys.setenv("OPENAI_API_BASE", "http://vllm.internal:8000/v1")
    plan = plan_generation("litellm", "openai/my-qwen", {"top_k": 20, "enable_thinking": True})
    assert plan.model_kwargs == {
        "top_k": 20,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": True}},
    }
    assert plan.not_applied == {}


def test_litellm_native_reasoning_providers_refuse_the_template_switch(no_keys):
    plan = plan_generation(
        "litellm", "anthropic/claude-sonnet-4-5", {"enable_thinking": True, "top_k": 5}
    )
    assert plan.model_kwargs == {"top_k": 5}
    assert "anthropic" in plan.not_applied["enable_thinking"]


def test_litellm_unknown_model_id_passes_settings_through(no_keys):
    # litellm cannot place the id, so it has no table to check: the call itself decides, loudly.
    plan = plan_generation("litellm", "some-unknown-model", {"temperature": 0.1})
    assert plan.model_kwargs == {"temperature": 0.1}


def test_litellm_falls_back_to_max_completion_tokens(no_keys, monkeypatch):
    monkeypatch.setattr(
        generation, "_litellm_supported_params", lambda *_: ["max_completion_tokens"]
    )
    plan = plan_generation("litellm", "openai/x", {"max_new_tokens": 64, "temperature": 1})
    assert plan.model_kwargs == {"max_completion_tokens": 64}
    assert "temperature" in plan.not_applied

    monkeypatch.setattr(generation, "_litellm_supported_params", lambda *_: [])
    plan = plan_generation("litellm", "openai/x", {"max_new_tokens": 64})
    assert plan.model_kwargs == {}
    assert "max_new_tokens" in plan.not_applied


def test_ollama_uses_the_think_switch(no_keys):
    plan = plan_generation("ollama", "ollama/qwen3", ALL_SETTINGS)
    assert plan.model_kwargs == {
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 256,
        "top_k": 40,
        "think": False,
    }
    assert set(plan.not_applied) == {"reasoning_effort"}

    effort_only = plan_generation("ollama", "ollama/qwen3", {"reasoning_effort": "high"})
    assert effort_only.model_kwargs == {"reasoning_effort": "high"}


def test_ollama_gpt_oss_takes_the_effort_level(no_keys):
    plan = plan_generation(
        "ollama", "ollama/gpt-oss:20b", {"reasoning_effort": "high", "enable_thinking": True}
    )
    assert plan.model_kwargs == {"reasoning_effort": "high"}
    assert set(plan.not_applied) == {"enable_thinking"}


def test_inference_names_three_and_sends_the_rest_in_extra_body():
    plan = plan_generation("inference", "Qwen/Qwen3-32B", ALL_SETTINGS)
    assert plan.model_kwargs == {
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 256,
        "extra_body": {
            "top_k": 40,
            "reasoning_effort": "low",
            "chat_template_kwargs": {"enable_thinking": False},
        },
    }
    assert plan.not_applied == {}


def test_transformers_samples_only_when_asked():
    plan = plan_generation("transformers", "Qwen/Qwen3-0.6B", ALL_SETTINGS)
    assert plan.model_kwargs == {
        "temperature": 0.3,
        "do_sample": True,
        "top_p": 0.9,
        "top_k": 40,
        "max_new_tokens": 256,
    }
    assert plan.chat_template_kwargs == {"reasoning_effort": "low", "enable_thinking": False}

    greedy = plan_generation("transformers", "m", {"temperature": 0, "top_p": 0.9, "top_k": 5})
    assert greedy.model_kwargs == {"do_sample": False}
    assert set(greedy.not_applied) == {"top_p", "top_k"}


def test_transformers_thinking_needs_a_template_that_reads_it():
    plan = plan_generation(
        "transformers", "m", {"enable_thinking": False, "reasoning_effort": "low"}
    )
    kwargs = finalize_chat_template(plan, "{% if enable_thinking %}<think>{% endif %}")
    assert kwargs == {"enable_thinking": False}
    assert plan.applied == {"enable_thinking": False}
    assert "chat template" in plan.not_applied["reasoning_effort"]

    plan = plan_generation("transformers", "m", {"enable_thinking": True})
    assert finalize_chat_template(plan, None) == {}
    assert "enable_thinking" in plan.not_applied


def test_unknown_provider_applies_nothing():
    plan = plan_generation("other", "m", {"temperature": 0.5})
    assert plan.model_kwargs == {}
    assert "temperature" in plan.not_applied


def test_report_and_record(capsys):
    plan = plan_generation("transformers", "m", {"temperature": 0, "top_p": 0.5})
    plan.report()
    out = capsys.readouterr().out
    assert "[GENERATION] applied for transformers: temperature=0.0" in out
    assert "[GENERATION] not applied for transformers: top_p (" in out
    record = plan.as_record()
    assert record["requested"] == {"temperature": 0.0, "top_p": 0.5}
    assert set(record["not_applied"]) == {"top_p"}

    empty = plan_generation("litellm", "openai/gpt-4", None)
    empty.report()
    assert capsys.readouterr().out == ""
    assert empty.as_record() is None


# --- the kwargs reach the model constructors -----------------------------------------------------


def test_initialize_model_passes_generation_kwargs_to_litellm(no_keys, mocker, capsys):
    no_keys.setenv("OPENROUTER_API_KEY", "sk-or-test")
    model_cls = mocker.patch("smoltrace.core.LiteLLMModel")
    record = {}
    core._initialize_model(
        "openrouter/qwen/qwen3-32b",
        "litellm",
        request_timeout=30,
        generation_settings={"temperature": 0.2, "top_k": 10, "enable_thinking": False},
        generation_record=record,
    )
    assert model_cls.call_args.kwargs == {
        "model_id": "openrouter/qwen/qwen3-32b",
        "timeout": 30,
        "temperature": 0.2,
        "top_k": 10,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
    assert record["applied"] == {"temperature": 0.2, "top_k": 10, "enable_thinking": False}
    assert "[GENERATION] applied for litellm" in capsys.readouterr().out

    # A second model of the same run (a parallel worker) does not print or overwrite the record.
    core._initialize_model(
        "openrouter/qwen/qwen3-32b",
        "litellm",
        generation_settings={"temperature": 0.2},
        generation_record=record,
    )
    assert "[GENERATION]" not in capsys.readouterr().out
    assert set(record["applied"]) == {"temperature", "top_k", "enable_thinking"}


def test_initialize_model_without_settings_adds_no_kwargs(no_keys, mocker):
    no_keys.setenv("OPENAI_API_KEY", "sk-test")
    model_cls = mocker.patch("smoltrace.core.LiteLLMModel")
    core._initialize_model("openai/gpt-4.1-nano", "litellm")
    assert model_cls.call_args.kwargs == {"model_id": "openai/gpt-4.1-nano"}


def test_initialize_model_passes_generation_kwargs_to_ollama(mocker):
    model_cls = mocker.patch("smoltrace.core.LiteLLMModel")
    core._initialize_model(
        "qwen3",
        "ollama",
        generation_settings={"max_new_tokens": 128, "enable_thinking": True},
    )
    assert model_cls.call_args.kwargs == {
        "model_id": "ollama/qwen3",
        "api_base": "http://localhost:11434",
        "max_tokens": 128,
        "think": True,
    }


def test_initialize_model_passes_generation_kwargs_to_inference(mocker):
    import smolagents

    model_cls = mocker.patch.object(smolagents, "InferenceClientModel")
    core._initialize_model(
        "Qwen/Qwen3-32B",
        "inference",
        hf_inference_provider="nebius",
        generation_settings={"temperature": 0.7, "top_k": 5},
    )
    kwargs = model_cls.call_args.kwargs
    assert kwargs["model_id"] == "Qwen/Qwen3-32B"
    assert kwargs["provider"] == "nebius"
    assert kwargs["temperature"] == 0.7
    assert kwargs["extra_body"] == {"top_k": 5}


def test_initialize_model_passes_generation_kwargs_to_transformers(mocker):
    import smolagents

    built = types.SimpleNamespace(
        tokenizer=types.SimpleNamespace(chat_template="{{ enable_thinking }}"),
        apply_chat_template_kwargs={},
    )
    model_cls = mocker.patch.object(smolagents, "TransformersModel", return_value=built)
    record = {}
    model = core._initialize_model(
        "Qwen/Qwen3-0.6B",
        "transformers",
        generation_settings={
            "temperature": 0.6,
            "top_k": 20,
            "max_new_tokens": 512,
            "enable_thinking": False,
            "reasoning_effort": "low",
        },
        generation_record=record,
    )
    kwargs = model_cls.call_args.kwargs
    assert kwargs["temperature"] == 0.6
    assert kwargs["do_sample"] is True
    assert kwargs["top_k"] == 20
    assert kwargs["max_new_tokens"] == 512
    assert "enable_thinking" not in kwargs
    assert model.apply_chat_template_kwargs == {"enable_thinking": False}
    assert record["applied"]["enable_thinking"] is False
    assert "reasoning_effort" in record["not_applied"]


def test_initialize_agent_threads_generation_settings(mocker):
    init = mocker.patch("smoltrace.core._initialize_model")
    mocker.patch("smoltrace.core.ToolCallingAgent")
    record = {}
    core.initialize_agent(
        "openai/gpt-4",
        "tool",
        generation_settings={"temperature": 0.1},
        generation_record=record,
    )
    assert init.call_args.kwargs["generation_settings"] == {"temperature": 0.1}
    assert init.call_args.kwargs["generation_record"] is record


# --- leaderboard field -------------------------------------------------------------------------


def test_generation_settings_field_is_json_or_null():
    assert generation_settings_field(None) is None
    assert generation_settings_field({}) is None
    record = {"requested": {"top_k": 5}, "applied": {}, "not_applied": {"top_k": "why"}}
    assert json.loads(generation_settings_field(record)) == record

    row = build_status_row(
        "m",
        agent_type="tool",
        run_id="r",
        provider="litellm",
        dataset_used="d",
        error="boom",
        generation_settings=record,
    )
    assert json.loads(row["generation_settings"])["not_applied"] == {"top_k": "why"}
    assert (
        build_status_row(
            "m", agent_type="tool", run_id="r", provider="litellm", dataset_used="d", error="x"
        )["generation_settings"]
        is None
    )


def test_opensearch_leaderboard_mapping_declares_the_field():
    from smoltrace.exporters.opensearch import LEADERBOARD_INDEX_MAPPING

    assert "generation_settings" in LEADERBOARD_INDEX_MAPPING["mappings"]["properties"]


# --- CLI ---------------------------------------------------------------------------------------


def test_cli_parses_generation_flags_and_new_search_providers(mocker):
    from smoltrace import cli

    flow = mocker.patch("smoltrace.cli.run_evaluation_flow")
    mocker.patch.object(
        sys,
        "argv",
        [
            "smoltrace-eval",
            "--model",
            "openai/gpt-4",
            "--temperature",
            "0.4",
            "--top-p",
            "0.8",
            "--top-k",
            "30",
            "--max-new-tokens",
            "1024",
            "--reasoning-effort",
            "medium",
            "--enable-thinking",
            "false",
            "--search-provider",
            "tavily",
        ],
    )
    cli.main()
    args = flow.call_args.args[0]
    assert generation_settings_from_args(args) == {
        "temperature": 0.4,
        "top_p": 0.8,
        "top_k": 30,
        "max_new_tokens": 1024,
        "reasoning_effort": "medium",
        "enable_thinking": False,
    }
    assert args.search_provider == "tavily"


def test_cli_refuses_an_out_of_range_setting(mocker):
    from smoltrace import cli

    mocker.patch("smoltrace.cli.run_evaluation_flow")
    mocker.patch.object(sys, "argv", ["smoltrace-eval", "--model", "m", "--top-p", "1.5"])
    with pytest.raises(SystemExit):
        cli.main()


# --- search providers --------------------------------------------------------------------------


def test_brave_uses_the_api_web_search_tool(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "brave-key")
    tool = tools.build_search_tool("brave")
    assert type(tool).__name__ == "ApiWebSearchTool"
    assert tool.endpoint == "https://api.search.brave.com/res/v1/web/search"
    assert tool.headers == {"X-Subscription-Token": "brave-key"}
    assert tool.name == "web_search"


def test_serper_and_duckduckgo_still_work(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "serper-key")
    serper = tools.build_search_tool("serper")
    assert type(serper).__name__ == "GoogleSearchTool"
    assert serper.provider == "serper"
    assert type(tools.build_search_tool("duckduckgo")).__name__ == "DuckDuckGoSearchTool"


@pytest.mark.parametrize(
    "provider,key",
    [("serper", "SERPER_API_KEY"), ("brave", "BRAVE_API_KEY"), ("tavily", "TAVILY_API_KEY")],
)
def test_a_provider_without_its_key_fails_loudly(monkeypatch, provider, key):
    monkeypatch.delenv(key, raising=False)
    with pytest.raises(tools.SearchProviderUnavailableError, match=key):
        tools.get_all_tools(search_provider=provider, enabled_smolagents_tools=["google_search"])


def test_unknown_search_provider_is_refused():
    with pytest.raises(tools.SearchProviderUnavailableError, match="Unknown search provider"):
        tools.build_search_tool("bing")


def test_google_search_and_duckduckgo_search_do_not_register_web_search_twice():
    built = tools.get_smolagents_optional_tools(
        ["google_search", "duckduckgo_search"], search_provider="duckduckgo"
    )
    assert [tool.name for tool in built] == ["web_search"]


def test_search_provider_without_the_tool_says_it_has_no_effect(monkeypatch, capsys):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    built = tools.get_all_tools(
        search_provider="tavily", enabled_smolagents_tools=["visit_webpage"]
    )
    assert "web_search" not in [tool.name for tool in built]
    assert "--search-provider tavily has no effect" in capsys.readouterr().out


def test_tavily_tool_requires_a_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(tools.SearchProviderUnavailableError, match="TAVILY_API_KEY"):
        tools.TavilySearchTool()


def test_tavily_tool_request_and_response_shape(monkeypatch, mocker):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    tool = tools.build_search_tool("tavily", tool_timeout=45)
    assert isinstance(tool, tools.TavilySearchTool)
    assert tool.timeout == 45

    response = mocker.Mock()
    response.json.return_value = {
        "query": "smolagents",
        "results": [
            {"title": "Docs", "url": "https://example.org/a", "content": "First.", "score": 0.9},
            {"title": "Blog", "url": "https://example.org/b", "content": "Second.", "score": 0.5},
        ],
    }
    post = mocker.patch("requests.post", return_value=response)

    text = tool.forward("smolagents")

    post.assert_called_once_with(
        "https://api.tavily.com/search",
        headers={"Authorization": "Bearer tvly-test"},
        json={"query": "smolagents", "max_results": 10},
        timeout=45,
    )
    response.raise_for_status.assert_called_once()
    assert text.startswith("## Search Results")
    assert "1. [Docs](https://example.org/a)\nFirst." in text
    assert "2. [Blog](https://example.org/b)\nSecond." in text

    response.json.return_value = {"results": []}
    assert tool.forward("nothing") == "No results found."
    assert tools.TavilySearchTool(api_key="k").timeout == tools.DEFAULT_SEARCH_REQUEST_TIMEOUT_S


# --- the litellm key gate ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "model,key",
    [
        ("openrouter/qwen/qwen3-32b", "OPENROUTER_API_KEY"),
        ("nebius/Qwen/Qwen3-32B", "NEBIUS_API_KEY"),
        ("gemini/gemini-2.5-flash", "GEMINI_API_KEY"),
        ("gemini/gemini-2.5-flash", "GOOGLE_API_KEY"),
        ("deepseek/deepseek-chat", "DEEPSEEK_API_KEY"),
        ("openai/gpt-4.1-nano", "OPENAI_API_KEY"),
        ("together_ai/meta/llama", "TOGETHER_API_KEY"),
        ("anthropic/claude-sonnet-4-5", "LITELLM_API_KEY"),
    ],
)
def test_key_gate_accepts_the_providers_own_key(no_keys, mocker, model, key):
    no_keys.setenv(key, "sk-test")
    assert litellm_key_status(model) == (True, [])
    model_cls = mocker.patch("smoltrace.core.LiteLLMModel")
    core._initialize_model(model, "litellm")
    assert model_cls.call_args.kwargs == {"model_id": model}


def test_key_gate_names_the_missing_key(no_keys):
    ok, missing = litellm_key_status("openrouter/qwen/qwen3-32b")
    assert (ok, missing) == (False, ["OPENROUTER_API_KEY"])
    with pytest.raises(ValueError, match="requires an API key.*OPENROUTER_API_KEY"):
        core._initialize_model("openrouter/qwen/qwen3-32b", "litellm")


def test_key_gate_refuses_another_providers_key(no_keys):
    # An OpenAI key does not let an Anthropic model start: the old list accepted any of six.
    no_keys.setenv("OPENAI_API_KEY", "sk-test")
    assert litellm_key_status("anthropic/claude-sonnet-4-5") == (False, ["ANTHROPIC_API_KEY"])


def test_key_gate_no_key_at_all_still_fails(no_keys):
    assert litellm_key_status("some-unplaced-model") == (False, [])
    with pytest.raises(ValueError, match="LiteLLM provider requires an API key"):
        core._initialize_model("some-unplaced-model", "litellm")
    no_keys.setenv("OPENAI_API_KEY", "dummy")
    assert litellm_key_status("some-unplaced-model") == (False, [])
    no_keys.setenv("CUSTOM_API_KEY", "real")
    assert litellm_key_status("some-unplaced-model") == (True, [])


def test_key_gate_keyless_providers(no_keys):
    assert litellm_key_status("ollama/qwen3") == (True, [])
    assert litellm_key_status("hosted_vllm/qwen3") == (True, [])


def test_key_gate_survives_a_litellm_failure(no_keys, mocker):
    mocker.patch("litellm.validate_environment", side_effect=RuntimeError("boom"))
    assert litellm_key_status("openai/gpt-4") == (False, [])
    mocker.patch("litellm.get_llm_provider", side_effect=RuntimeError("boom"))
    assert generation._litellm_provider("openai/gpt-4") is None
    assert generation._litellm_supported_params("openai/gpt-4", None) is None
    mocker.patch("litellm.get_supported_openai_params", side_effect=RuntimeError("boom"))
    assert generation._litellm_supported_params("openai/gpt-4", "openai") is None
