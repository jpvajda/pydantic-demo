# eval_demo

A customer support bot graded with [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/). The model is `gemini-3.5-flash-lite`. Scores print in the terminal and the run is sent to [Pydantic Logfire](https://pydantic.dev/docs/logfire/).

## Dataset

`dataset/customer_support_messages.csv` has 100 customer messages (`cs-001` … `cs-100`). Each row has the message, an `expected` reply, and category, sentiment, priority, channel, and tags.

## Setup

Run everything from the repository root.

```bash
uv sync
export GEMINI_API_KEY="your-gemini-api-key"   # https://aistudio.google.com/apikey
```

> Connect Logfire once (see the [root README](../README.md))

From the repository root:

```bash
uv run eval_demo/pydantic_evals/eval_support.py                      # 5 rows, about 1 minute
uv run eval_demo/pydantic_evals/eval_support.py --all                # all 100 rows, about 20 minutes
uv run eval_demo/pydantic_evals/eval_support.py --ids cs-001 cs-090  # these ids only, not the rows between them
uv run eval_demo/pydantic_evals/chat_app.py                          # live chat, type quit to exit
```

## What gets graded

Each CSV row is a `Case`. `expected` rides along on the case so Logfire shows it next to the bot's reply. Nothing exact-matches it. Three evaluators grade every reply:

- **LLMJudge** — the built-in LLM-as-a-judge. Gemini scores the reply from 0 to 1 and marks it pass or fail, using the customer message and a rubric. One extra Gemini call per row.
- **NonEmptyReply** — assertion that the reply is not blank.
- **MaxDuration** — assertion that the reply finishes within 45 seconds.

Each row makes two Gemini calls, the reply and the judge. The script waits 5 seconds before every one of those calls, which stays inside the free tier (about 15 requests per minute). `eval_support.py` uses temperature 0 so reruns compare. The live chat uses temperature 1.0 and does not wait.

A live chat span records the turn number only. `LOGFIRE_LOG_CHAT=1` also sends the message, the reply, and the history. Leave it unset when a message might contain an email or an order number.

In Logfire, filter on `service_name = 'customer-support-evals'` and open the newest `evaluate support-bot-...` span for the case table. Live chats use `service_name = 'customer-support-chat'`. The order pipeline in [`logfire_demo/`](../logfire_demo/README.md) uses `order-pipeline`, so the three stay separate.
