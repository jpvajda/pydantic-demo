# pydantic-demo

Two small demos for the Pydantic ecosystem. Both send traces to [Pydantic Logfire](https://pydantic.dev/docs/logfire/).

| Demo | What it shows | Start here |
| --- | --- | --- |
| [`logfire_demo/`](logfire_demo/README.md) | Pydantic validation plus Logfire tracing on a small order pipeline. | `uv run logfire_demo/main.py` |
| [`eval_demo/`](eval_demo/README.md) | A customer support chat bot graded with Pydantic Evals. Scores print in the terminal and show up in Logfire. | `uv run eval_demo/pydantic_evals/eval_support.py` |

## Setup

You need [uv](https://docs.astral.sh/uv/) and a free Logfire account.

```bash
uv sync
uvx logfire-cli auth
uvx logfire-cli init
```

Run `init` from this directory. It writes a write token to `.logfire/` here. That directory is gitignored. Each person connects the clone to their own Logfire project. Do not run `init` inside `logfire_demo/` or `eval_demo/`. A token written there is not the one the scripts read.

The eval demo also needs a Gemini key in the same terminal. See [eval_demo/README.md](eval_demo/README.md):

```bash
export GEMINI_API_KEY="your-gemini-api-key"   # https://aistudio.google.com/apikey
```

Run every command below from this directory.
