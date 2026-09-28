"""--prompt-yml must reach smolagents as ``prompt_templates``.

Earlier releases passed ``system_prompt=`` (and CodeAgent ``grammar=``) to the agent
constructor. smolagents >=1.0 accepts neither, so every --prompt-yml run raised
TypeError before a single test executed. The existing tests mocked the agent classes,
which is exactly why it went unnoticed — the tests below construct REAL agents.
"""

import warnings

import pytest
import yaml
from smolagents import CodeAgent, ToolCallingAgent
from smolagents.models import Model

from smoltrace.core import _default_prompt_templates, build_prompt_templates, initialize_agent


class _StubModel(Model):
    """A real smolagents Model that is never called (construction only)."""

    def __init__(self):
        super().__init__(model_id="stub")

    def generate(self, *args, **kwargs):  # pragma: no cover - never invoked
        raise AssertionError("not called")


def _agent(agent_type, prompt_config, mocker):
    mocker.patch("smoltrace.core._initialize_model", return_value=_StubModel())
    mocker.patch("smoltrace.core.get_all_tools", return_value=[])
    return initialize_agent("stub", agent_type, prompt_config=prompt_config)


@pytest.mark.parametrize("agent_type,cls", [("tool", ToolCallingAgent), ("code", CodeAgent)])
def test_full_smolagents_template_constructs_real_agent(agent_type, cls, mocker):
    template = _default_prompt_templates(agent_type)
    template["system_prompt"] = "You are a banking support agent.\n" + template["system_prompt"]

    agent = _agent(agent_type, template, mocker)

    assert isinstance(agent, cls)
    assert agent.prompt_templates["system_prompt"].startswith("You are a banking support agent.")
    assert agent.system_prompt.startswith("You are a banking support agent.")


@pytest.mark.parametrize("agent_type", ["tool", "code"])
def test_legacy_plain_system_prompt_is_prepended_not_replacing(agent_type, mocker):
    agent = _agent(
        agent_type, {"system_prompt": "Always answer in French.", "max_steps": 3}, mocker
    )

    sp = agent.prompt_templates["system_prompt"]
    assert sp.startswith("Always answer in French.")
    # The protocol-bearing default survives, or the agent could not call tools at all.
    assert _default_prompt_templates(agent_type)["system_prompt"] in sp
    assert agent.max_steps == 3


def test_nested_prompt_templates_key_is_accepted(mocker):
    nested = {"prompt_templates": {"system_prompt": "Custom {{tools}} body"}}
    agent = _agent("tool", nested, mocker)
    # A nested prompt_templates block is a full template: used verbatim, not prepended.
    assert agent.prompt_templates["system_prompt"] == "Custom {{tools}} body"
    # Missing sections are filled from the defaults, so smolagents' key check passes.
    assert set(agent.prompt_templates) >= {"planning", "managed_agent", "final_answer"}


def test_partial_section_override_merges_subkeys():
    out = build_prompt_templates("code", {"final_answer": {"pre_messages": "PRE"}})
    assert out["final_answer"]["pre_messages"] == "PRE"
    assert (
        out["final_answer"]["post_messages"]
        == _default_prompt_templates("code")["final_answer"]["post_messages"]
    )


def test_no_template_keys_returns_none():
    assert build_prompt_templates("tool", {"max_steps": 4}) is None
    assert build_prompt_templates("tool", None) is None


def test_grammar_is_ignored_with_a_warning(mocker):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = _agent("code", {"grammar": {"x": 1}}, mocker)
    assert isinstance(agent, CodeAgent)
    assert any("grammar" in str(w.message) for w in caught)


def test_planning_interval_reaches_tool_agent(mocker):
    agent = _agent("tool", {"planning_interval": 2}, mocker)
    assert agent.planning_interval == 2


def test_platform_published_file_roundtrips(tmp_path, mocker):
    """The exact file TraceMind publishes (prompt_template.tool.yaml) loads and runs."""
    from smoltrace.utils import load_prompt_config

    template = _default_prompt_templates("tool")
    template["system_prompt"] = "You are an expert travel assistant.\n" + template["system_prompt"]
    path = tmp_path / "prompt_template.tool.yaml"
    path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")

    agent = _agent("tool", load_prompt_config(str(path)), mocker)
    assert agent.system_prompt.startswith("You are an expert travel assistant.")
