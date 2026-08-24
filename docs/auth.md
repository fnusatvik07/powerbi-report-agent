# Authentication

There are two independent auth concerns. Keep them separate.

## 1. The model backend (for the natural-language agent)

The `chat` agent runs on a LangChain model. It needs an API key, set in `.env`:

- Anthropic (default): `ANTHROPIC_API_KEY`, model `claude-sonnet-4-5-20250929`.
- OpenAI: `OPENAI_API_KEY` plus `PBI_AGENT_MODEL=gpt-4o` and `pip install langchain-openai`.

This key only talks to the model provider. It has nothing to do with Power BI.

## 2. Publishing to Power BI (the Fabric CLI)

Publishing uses the Fabric CLI, which authenticates interactively:

```bash
fab auth login          # opens a browser / device code, sign in with your account
fab auth status         # confirm you are logged in
```

This is an OAuth authorization-code flow: you (the human) sign in, and the CLI holds a
short-lived token. No client id or secret is stored in this repo, which is deliberate. If
you need unattended publishing (CI), register a service principal and use the client
credentials flow instead, but that is out of scope for the default setup here.

## Why no secrets live in the repo

`.env` is gitignored. The only credential the tool ever handles for Power BI is the token
the Fabric CLI manages after `fab auth login`. Generated example projects contain sample
data only, never credentials.
