# SPEC v0.2.11: generation settings, Brave and Tavily search, the litellm key gate

## 1. Generation settings

Flags (Python API: `run_evaluation(generation_settings={...})` with the same names, underscored):

| Flag | Value | Meaning |
|---|---|---|
| `--temperature` | float, >= 0 | Sampling temperature |
| `--top-p` | float, 0 < p <= 1 | Nucleus sampling |
| `--top-k` | int, >= 1 | Top-k sampling |
| `--max-new-tokens` | int, >= 1 | Maximum tokens generated per model call |
| `--reasoning-effort` | `none` `minimal` `low` `medium` `high` | Reasoning effort |
| `--enable-thinking` | `true` `false` | Chat-template thinking switch of open-weight models |

Unset means the provider's default: nothing is sent.

### How they reach the model

smolagents stores model-constructor kwargs (`Model.__init__(**kwargs)` -> `self.kwargs`) and merges
them into every completion in `_prepare_completion_kwargs`, with priority over per-call arguments.
SMOLTRACE passes the settings there, in `_initialize_model`. `--model-args` does not do this: it
reaches `agent.run(additional_args=...)`, which gives the values to the agent as task variables.

### What each provider is sent

Checked against smolagents 1.26.0, litellm 1.91.3 (the request body litellm builds) and
huggingface_hub 1.23.0.

| Setting | `litellm` | `ollama` | `inference` | `transformers` |
|---|---|---|---|---|
| temperature | `temperature`, when litellm lists it for the model | `temperature` | `temperature` | `temperature` + `do_sample=True`; `0` becomes `do_sample=False` |
| top_p | `top_p`, when listed | `top_p` | `top_p` | `top_p` + `do_sample=True`; not applied at temperature 0 |
| top_k | `top_k` (provider-specific field). Not applied on native OpenAI/Azure, whose API has none | `top_k` | `extra_body.top_k` | `top_k` + `do_sample=True`; not applied at temperature 0 |
| max_new_tokens | `max_tokens` (or `max_completion_tokens` when only that is listed) | `max_tokens` (Ollama `num_predict`) | `max_tokens` | `max_new_tokens` |
| reasoning_effort | `reasoning_effort`, when litellm lists it for the model | `reasoning_effort` (litellm turns it into Ollama's `think`); not sent when `--enable-thinking` is also set | `extra_body.reasoning_effort` | `apply_chat_template(reasoning_effort=...)`, only when the model's chat template reads it |
| enable_thinking | `extra_body={"chat_template_kwargs": {"enable_thinking": bool}}`. Not applied on native OpenAI, Azure, Anthropic, Gemini, Vertex, Bedrock, Cohere: use `--reasoning-effort` | `think=bool` (gpt-oss takes the effort level instead) | `extra_body.chat_template_kwargs.enable_thinking` | `apply_chat_template(enable_thinking=bool)`, only when the model's chat template reads it |

Notes:

* **"listed"** is litellm's `get_supported_openai_params(model, provider)`. An OpenAI parameter that
  is not listed raises `UnsupportedParamsError` on every call, so SMOLTRACE leaves it out and reports
  it. A model id litellm cannot place has no table: the setting is sent and the call decides.
* **`litellm.drop_params` is left off on purpose.** It removes an unsupported setting from the
  request without a word, which would let a run claim a temperature it never used.
* `openai/<model>` with `OPENAI_API_BASE` / `OPENAI_BASE_URL` set is a custom OpenAI-compatible
  endpoint (vLLM, llama-server): `top_k` and `enable_thinking` are sent.
* `top_k`, `extra_body` and Ollama's `think` are provider-specific fields. litellm and the Hugging
  Face client forward them as given; an endpoint that rejects unknown fields fails the call, loudly.
* transformers: `temperature`, `top_p` and `top_k` only act when sampling, so sampling is switched
  on with them. The chat template is inspected after the model loads; a template that never reads
  `enable_thinking` would ignore it silently, so it is reported as not applied.

### Reporting

Before the first task:

```
[GENERATION] applied for litellm: temperature=0.2, top_p=0.9
[GENERATION] not applied for litellm: top_k (the OpenAI API has no top_k)
```

The leaderboard row carries `generation_settings`: JSON text, `{"requested": {...}, "applied":
{...}, "not_applied": {"<setting>": "<reason>"}}`, or null when no setting was given. One string
column keeps the Hub dataset and the OpenSearch mapping (`keyword`, not indexed) a fixed shape. A
run that fails before producing results records it on its status row too.

## 2. Search providers

`--enable-tools google_search --search-provider <p>` builds one tool named `web_search`:

| Provider | Tool | Key |
|---|---|---|
| `duckduckgo` (default) | smolagents `DuckDuckGoSearchTool` | none |
| `serper` | smolagents `GoogleSearchTool(provider="serper")` | `SERPER_API_KEY` |
| `brave` | smolagents `ApiWebSearchTool` (Brave Search API) | `BRAVE_API_KEY` |
| `tavily` | `smoltrace.tools.TavilySearchTool` | `TAVILY_API_KEY` |

Tavily: `POST https://api.tavily.com/search`, header `Authorization: Bearer <key>`, body
`{"query": ..., "max_results": 10}`; the answer's `results[]` carry `title`, `url`, `content`
(checked against Tavily's API reference, 2026-10-01). The HTTP request times out at `--tool-timeout`.

Before 0.2.11 `brave` and `duckduckgo` were handed to `GoogleSearchTool`, which only speaks SerpAPI
and Serper: the tool failed to initialise, one warning was printed and the run continued without
search. A selected provider whose key is not set now raises `SearchProviderUnavailableError` before
the first task. `google_search` and `duckduckgo_search` together with the `duckduckgo` provider
register the tool once. `--search-provider` without `google_search` prints that it has no effect.

## 3. The litellm key gate

`--provider litellm` used to require one of `LITELLM_API_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`, whatever the model. Now:

1. `LITELLM_API_KEY` set: accepted (as before).
2. Otherwise litellm's `validate_environment(model)` decides, so the key is the model's own
   provider's (`openrouter/...` -> `OPENROUTER_API_KEY`, `gemini/...` -> `GEMINI_API_KEY` or
   `GOOGLE_API_KEY`, ...). When it is missing the error names it.
3. A model id litellm cannot place needs at least one `*_API_KEY` in the environment.
4. No key at all still fails. A key that belongs to another provider no longer passes.

`ollama/...` and other keyless litellm providers are accepted.
