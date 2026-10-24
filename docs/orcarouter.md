# OrcaRouter provider

Taranis AI includes a named **OrcaRouter Cyber Inference** provider in **Admin Settings > LLM Endpoints**. [OrcaRouter](https://www.orcarouter.ai) is an OpenAI-compatible AI gateway that routes many providers behind one endpoint and adds gateway-level security controls for AI agents.

Use this provider for authorized, scoped security inference by verified security teams. Taranis sends only the prompts and selected story content required by the configured features.

## Configuration

1. Create an API key in the [OrcaRouter console](https://www.orcarouter.ai/console). Keys start with `sk-orca-`.
2. Add an LLM endpoint and select **OrcaRouter Cyber Inference** as its provider.
3. Keep the base URL `https://api.orcarouter.ai/v1`.
4. Paste the key into **API key**. Taranis stores it server-side; the browser never receives the saved value back.
5. Enable **Responses** and/or **Chat Completions**, then choose a model from the catalogue-backed dropdown for each enabled format.

The dropdown is populated from OrcaRouter's `/v1/models` response for the saved key, so workspace-specific models appear after the key is saved or entered. Selecting a provider or base URL reloads the catalogue, and changing the key refreshes it. If OrcaRouter rejects the key or the catalogue is unreachable, Taranis shows the error and a small verified seed of models instead of mixing stale options into live results.

## Model recommendations

The catalogue lists every model returned for the workspace. Taranis recommends these OrcaRouter model IDs in this order:

- `orcarouter/auto` — default for general Chat and background content features.
- `orca/orcacyber-ultra-1.0` (OrcaCyber Ultra) and `orca/orcacyber-zero-1.5` (OrcaCyber Zero) — dedicated cyber models for verified security teams. See the [cyber model catalogue](https://www.orcarouter.ai/models?tier=cyber).
- `orcarouter/fusion` — fallback when the default route is unavailable or when a task benefits from routing across providers.

Cyber models are exposed through Chat Completions only. Select a response-capable model such as `orcarouter/auto` when **Responses** is enabled.

## Supported features and limits

Chat, story clustering, summarization and titles, NER, and sentiment use the configured Responses or Chat Completions format. Each format uses its own model and falls back to the provider base URL unless a URL override is set.

Topic classification is not available through OrcaRouter because it requires a Decisions API. Keep classification on its existing Decisions endpoint; selecting the OrcaRouter provider hides the Decisions fields for that endpoint. OrcaRouter endpoints use realtime processing only; OpenRouter batch processing remains available on OpenRouter endpoints.

## Links

- [OrcaRouter](https://www.orcarouter.ai)
- [Security inference overview](https://www.orcarouter.ai/cyber)
- [Cyber model catalogue](https://www.orcarouter.ai/models?tier=cyber)
- [API keys](https://www.orcarouter.ai/console)
