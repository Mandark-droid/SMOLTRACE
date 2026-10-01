# smoltrace/generation.py
"""Generation settings (0.2.11): what each provider is actually sent.

``--model-args`` reaches ``agent.run(additional_args=...)``, which smolagents hands to the agent as
task variables: it never reaches the model. The settings here go to the model constructor instead.
smolagents merges constructor kwargs into every completion (``Model.__init__(**kwargs)`` ->
``self.kwargs`` -> ``_prepare_completion_kwargs``), so they apply to every model call of the run.

Every setting is either sent in the form the provider's client accepts, or reported as not applied
with the reason. Nothing is dropped silently, which is why ``litellm.drop_params`` is left off: it
would remove an unsupported setting from the request without saying so. The support check runs once,
before the first task, against litellm's own table (``get_supported_openai_params``).
"""

import json
import os
import re
from typing import Any, Dict, Optional, Tuple

GENERATION_SETTING_NAMES = (
    "temperature",
    "top_p",
    "top_k",
    "max_new_tokens",
    "reasoning_effort",
    "enable_thinking",
)

REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high")

#: litellm providers whose own API has a reasoning control and no chat template to switch.
_NATIVE_REASONING_PROVIDERS = frozenset(
    {
        "anthropic",
        "azure",
        "azure_ai",
        "bedrock",
        "bedrock_converse",
        "cohere",
        "cohere_chat",
        "gemini",
        "text-completion-openai",
        "vertex_ai",
        "vertex_ai_beta",
    }
)
_OPENAI_NATIVE_PROVIDERS = frozenset({"openai", "azure", "text-completion-openai"})
_OPENAI_BASE_ENV = ("OPENAI_API_BASE", "OPENAI_BASE_URL")


class GenerationPlan:
    """What a provider's model constructor receives, and what the run could not apply."""

    def __init__(self, provider: str, requested: Dict[str, Any]):
        self.provider = provider
        self.requested = dict(requested)
        self.model_kwargs: Dict[str, Any] = {}
        self.applied: Dict[str, Any] = {}
        self.not_applied: Dict[str, str] = {}
        #: transformers only: settings that reach the model through the chat template, applied
        #: only once the loaded template is seen to read them (``finalize_chat_template``).
        self.chat_template_kwargs: Dict[str, Any] = {}

    def apply(self, name: str, **model_kwargs: Any) -> None:
        self.applied[name] = self.requested[name]
        self.model_kwargs.update(model_kwargs)

    def skip(self, name: str, reason: str) -> None:
        self.not_applied[name] = reason

    def as_record(self) -> Optional[Dict[str, Any]]:
        """The run's record of its settings, or None when none was requested."""
        if not self.requested:
            return None
        return {
            "requested": dict(self.requested),
            "applied": dict(self.applied),
            "not_applied": dict(self.not_applied),
        }

    def report(self) -> None:
        """Print what was applied and, on its own line, everything that was not."""
        if not self.requested:
            return
        if self.applied:
            sent = ", ".join(f"{name}={value}" for name, value in self.applied.items())
            print(f"[GENERATION] applied for {self.provider}: {sent}")
        if self.not_applied:
            skipped = "; ".join(f"{name} ({reason})" for name, reason in self.not_applied.items())
            print(f"[GENERATION] not applied for {self.provider}: {skipped}")


def normalize_generation_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the settings and drop the unset ones. Raises ValueError on a bad value."""
    if not settings:
        return {}
    unknown = sorted(set(settings) - set(GENERATION_SETTING_NAMES))
    if unknown:
        raise ValueError(
            f"Unknown generation setting(s): {', '.join(unknown)}. "
            f"Known: {', '.join(GENERATION_SETTING_NAMES)}"
        )
    normalized: Dict[str, Any] = {}
    for name in GENERATION_SETTING_NAMES:
        value = settings.get(name)
        if value is None:
            continue
        if name == "temperature":
            value = float(value)
            if value < 0:
                raise ValueError("temperature must be 0 or greater")
        elif name == "top_p":
            value = float(value)
            if not 0 < value <= 1:
                raise ValueError("top_p must be greater than 0 and at most 1")
        elif name in ("top_k", "max_new_tokens"):
            if isinstance(value, bool) or int(value) != float(value):
                raise ValueError(f"{name} must be a whole number")
            value = int(value)
            if value < 1:
                raise ValueError(f"{name} must be 1 or greater")
        elif name == "reasoning_effort":
            value = str(value).strip().lower()
            if value not in REASONING_EFFORTS:
                raise ValueError(f"reasoning_effort must be one of: {', '.join(REASONING_EFFORTS)}")
        elif name == "enable_thinking":
            if isinstance(value, str):
                if value.strip().lower() not in ("true", "false"):
                    raise ValueError("enable_thinking must be true or false")
                value = value.strip().lower() == "true"
            value = bool(value)
        normalized[name] = value
    return normalized


def _litellm_provider(model_id: str) -> Optional[str]:
    """litellm's provider for a model id, or None when it cannot tell."""
    try:
        import litellm

        return litellm.get_llm_provider(model=model_id)[1]
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _litellm_supported_params(model_id: str, llm_provider: Optional[str]) -> Optional[list]:
    """The OpenAI parameters litellm maps for this model, or None when it has no table for it."""
    if not llm_provider:
        return None
    try:
        import litellm

        return litellm.get_supported_openai_params(model=model_id, custom_llm_provider=llm_provider)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _plan_litellm(plan: GenerationPlan, model_id: str) -> None:
    """litellm (and the ollama provider, which is litellm's ``ollama/`` route).

    Verified against litellm's request bodies: an OpenAI parameter the provider's table does not list
    raises ``UnsupportedParamsError`` on every call, so it is left out and reported instead. ``top_k``
    and ``extra_body`` are provider-specific fields litellm forwards to the endpoint as they are.
    """
    requested = plan.requested
    llm_provider = _litellm_provider(model_id)
    supported = _litellm_supported_params(model_id, llm_provider)
    is_ollama = llm_provider in ("ollama", "ollama_chat")
    custom_openai_base = any(os.getenv(name) for name in _OPENAI_BASE_ENV)
    openai_native = llm_provider in _OPENAI_NATIVE_PROVIDERS and not custom_openai_base

    def listed(param: str) -> bool:
        return supported is None or param in supported

    for name in ("temperature", "top_p"):
        if name in requested:
            if listed(name):
                plan.apply(name, **{name: requested[name]})
            else:
                plan.skip(name, f"litellm does not list {name} for {model_id}")

    if "max_new_tokens" in requested:
        if listed("max_tokens"):
            plan.apply("max_new_tokens", max_tokens=requested["max_new_tokens"])
        elif listed("max_completion_tokens"):
            plan.apply("max_new_tokens", max_completion_tokens=requested["max_new_tokens"])
        else:
            plan.skip("max_new_tokens", f"litellm does not list max_tokens for {model_id}")

    if "top_k" in requested:
        if openai_native:
            plan.skip("top_k", "the OpenAI API has no top_k")
        else:
            plan.apply("top_k", top_k=requested["top_k"])

    # Ollama has one think switch. litellm turns reasoning_effort into it, and an explicit
    # ``think`` wins over that, so only one of the two is sent. gpt-oss takes effort levels.
    ollama_levels = is_ollama and model_id.split("/", 1)[-1].startswith("gpt-oss")
    thinking_is_switch = is_ollama and "enable_thinking" in requested and not ollama_levels

    if "reasoning_effort" in requested:
        if thinking_is_switch:
            plan.skip(
                "reasoning_effort",
                "Ollama has one think switch and enable_thinking sets it",
            )
        elif listed("reasoning_effort"):
            plan.apply("reasoning_effort", reasoning_effort=requested["reasoning_effort"])
        else:
            plan.skip(
                "reasoning_effort",
                f"litellm does not list reasoning_effort for {model_id}",
            )

    if "enable_thinking" in requested:
        if is_ollama:
            if ollama_levels and "reasoning_effort" in plan.applied:
                plan.skip("enable_thinking", "gpt-oss on Ollama takes the reasoning effort level")
            else:
                plan.apply("enable_thinking", think=requested["enable_thinking"])
        elif openai_native or llm_provider in _NATIVE_REASONING_PROVIDERS:
            plan.skip(
                "enable_thinking",
                f"{llm_provider} has no chat-template switch; use --reasoning-effort",
            )
        else:
            plan.apply(
                "enable_thinking",
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": requested["enable_thinking"]}
                },
            )


def _plan_inference(plan: GenerationPlan) -> None:
    """Hugging Face ``InferenceClient.chat_completion``.

    It names ``temperature``, ``top_p`` and ``max_tokens``; everything else goes in ``extra_body``,
    which it merges into the request for the serving provider.
    """
    requested = plan.requested
    extra_body: Dict[str, Any] = {}
    for name in ("temperature", "top_p"):
        if name in requested:
            plan.apply(name, **{name: requested[name]})
    if "max_new_tokens" in requested:
        plan.apply("max_new_tokens", max_tokens=requested["max_new_tokens"])
    if "top_k" in requested:
        extra_body["top_k"] = requested["top_k"]
        plan.apply("top_k")
    if "reasoning_effort" in requested:
        extra_body["reasoning_effort"] = requested["reasoning_effort"]
        plan.apply("reasoning_effort")
    if "enable_thinking" in requested:
        extra_body["chat_template_kwargs"] = {"enable_thinking": requested["enable_thinking"]}
        plan.apply("enable_thinking")
    if extra_body:
        plan.model_kwargs["extra_body"] = extra_body


def _plan_transformers(plan: GenerationPlan) -> None:
    """``TransformersModel``: constructor kwargs reach ``model.generate``.

    ``temperature``/``top_p``/``top_k`` only act when sampling, so sampling is switched on with them;
    a temperature of 0 is greedy decoding. ``enable_thinking`` and ``reasoning_effort`` can only reach
    the model through its chat template, which is checked once the model is loaded.
    """
    requested = plan.requested
    greedy = requested.get("temperature") == 0
    if "temperature" in requested:
        if greedy:
            plan.apply("temperature", do_sample=False)
        else:
            plan.apply("temperature", temperature=requested["temperature"], do_sample=True)
    for name in ("top_p", "top_k"):
        if name in requested:
            if greedy:
                plan.skip(name, "temperature 0 is greedy decoding, which does not sample")
            else:
                plan.apply(name, **{name: requested[name]}, do_sample=True)
    if "max_new_tokens" in requested:
        plan.apply("max_new_tokens", max_new_tokens=requested["max_new_tokens"])
    for name in ("reasoning_effort", "enable_thinking"):
        if name in requested:
            plan.chat_template_kwargs[name] = requested[name]


def finalize_chat_template(plan: GenerationPlan, chat_template: Any) -> Dict[str, Any]:
    """Settle the transformers settings that travel through the chat template.

    Returns the ``apply_chat_template`` kwargs to use. A template that never reads a variable would
    ignore it without a word, so such a setting is reported as not applied instead.
    """
    template_text = (
        chat_template if isinstance(chat_template, str) else json.dumps(chat_template or "")
    )
    kwargs: Dict[str, Any] = {}
    for name, value in plan.chat_template_kwargs.items():
        if name in template_text:
            kwargs[name] = value
            plan.applied[name] = value
        else:
            plan.skip(name, f"the model's chat template does not read {name}")
    plan.chat_template_kwargs = {}
    return kwargs


def plan_generation(
    provider: str, model_id: str, settings: Optional[Dict[str, Any]]
) -> GenerationPlan:
    """Decide, for one provider, what the model constructor is given and what cannot be applied."""
    plan = GenerationPlan(provider, normalize_generation_settings(settings))
    if not plan.requested:
        return plan
    if provider in ("litellm", "ollama"):
        _plan_litellm(plan, model_id)
    elif provider == "inference":
        _plan_inference(plan)
    elif provider == "transformers":
        _plan_transformers(plan)
    else:
        for name in plan.requested:
            plan.skip(name, f"unknown provider {provider}")
    return plan


def generation_settings_from_args(args: Any) -> Dict[str, Any]:
    """The generation flags of a parsed CLI namespace (unset ones left out)."""
    settings = {}
    for name in GENERATION_SETTING_NAMES:
        value = getattr(args, name, None)
        if isinstance(value, (bool, int, float, str)):
            settings[name] = value
    return normalize_generation_settings(settings)


#: Key names litellm's own lookup accepts beyond the ones ``validate_environment`` reports.
_KEY_ALIASES = {
    "together_ai": ("TOGETHER_API_KEY", "TOGETHER_AI_API_KEY"),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}
#: litellm providers that take no API key.
_KEYLESS_PROVIDERS = frozenset({"ollama", "ollama_chat"})


def _usable(value: Optional[str]) -> bool:
    return bool(value) and value != "dummy"


def litellm_key_status(model_id: str) -> Tuple[bool, list]:
    """Whether the environment holds the key this litellm model needs: (ok, missing key names).

    Until 0.2.11 the check was a fixed list of six key names, so an estate holding only
    ``OPENROUTER_API_KEY`` (or Nebius, Gemini, DeepSeek...) was refused. litellm knows each provider's
    key (``validate_environment``); ``LITELLM_API_KEY`` is accepted for any model, as before. A model
    id litellm cannot place needs at least one ``*_API_KEY`` to be set: no key at all still fails.
    """
    if _usable(os.getenv("LITELLM_API_KEY")):
        return True, []
    llm_provider = _litellm_provider(model_id)
    if llm_provider in _KEYLESS_PROVIDERS:
        return True, []
    if llm_provider:
        try:
            import litellm

            status = litellm.validate_environment(model=model_id)
        except Exception:  # pylint: disable=broad-exception-caught
            status = {}
        if status.get("keys_in_environment"):
            return True, []
        missing = list(status.get("missing_keys") or [])
        if missing:
            alternatives = (
                *_KEY_ALIASES.get(llm_provider, ()),
                f"{re.sub(r'[^A-Za-z0-9]+', '_', llm_provider).upper()}_API_KEY",
            )
            if any(_usable(os.getenv(name)) for name in alternatives):
                return True, []
            return False, missing
    if any(_usable(value) for name, value in os.environ.items() if name.endswith("_API_KEY")):
        return True, []
    return False, []
