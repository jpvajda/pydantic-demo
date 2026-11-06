# pydantic-demo

A small Python CLI for learning two Pydantic tools together: **Pydantic** validates each order, and **Pydantic Logfire** records the run as a trace you can open in a browser.

One command loads 11 orders, rejects the bad ones, looks up a customer name, and writes the good rows to SQLite. The interesting parts are deliberate: three orders fail validation, one lookup returns a 404, and one step sleeps for 1.2 seconds.

## What you should see

After `uv run main.py`, the terminal prints a tree of spans and this summary:

```text
loaded=11 valid=8 saved=7
```

In the Logfire Live view, open the newest `run order pipeline` row. The long bar is `enrich orders`. Inside it, `slow enrichment delay` is about 1.2 seconds, and `GET .../users/99` is an HTTP 404.

## Setup

You need [uv](https://docs.astral.sh/uv/) and a free [Logfire](https://pydantic.dev/docs/logfire/) account.

```bash
uv sync
uvx logfire-cli auth
uvx logfire-cli init
```

`init` writes a write token to `.logfire/`. That directory is gitignored. Leave it that way. Each person connects the clone to their own Logfire project.

## Run

```bash
uv run hello.py   # one greeting span, to confirm Logfire is connected
uv run main.py    # the order pipeline
```

The command prints a Logfire project URL. Open it and widen the time range if the new rows are missing.

## The 11 orders

| Order | What happens |
| --- | --- |
| `ORD-001` … `ORD-007` | Valid. Customer name comes from JSONPlaceholder. |
| `ORD-SLOW` | Valid, then sleeps 1.2s so the span is easy to spot. |
| `ORD-BAD-QTY` | `quantity` is 0. Pydantic rejects it. |
| `ORD-BAD-PRICE` | `unit_price` is negative. Pydantic rejects it. |
| `ORD-BAD-SKU` | `sku` is empty. Pydantic rejects it. |
| `ORD-MISSING` | Valid order, `user_id` 99. JSONPlaceholder returns 404. |

JSONPlaceholder is a public fake API. No key. Any customer name in a trace comes from that API.

## Where to look in the code

- `pipeline/models.py` is the Pydantic `Order` model. The constraints are `quantity > 0`, `unit_price > 0`, and a non-empty `sku`.
- `main.py` calls `logfire.configure()` before any instrumentation. `instrument_pydantic()` has to run before the models are imported.
- `pipeline/steps.py` is load, validate, enrich, and save. Validation failures are structured logs. The HTTP and SQLite spans are automatic.

Two things that are easy to miss: SQLite spans show up for `cursor.execute`, and a caught 404 is a log, not an exception issue.

## Optional: ask an assistant about your traces

To query your own traces from Cursor, create `.cursor/mcp.json` locally (it is gitignored):

```json
{
  "mcpServers": {
    "logfire": {
      "url": "https://logfire-us.pydantic.dev/mcp"
    }
  }
}
```

No token goes in that file. The first query opens a browser login. Use `https://logfire-eu.pydantic.dev/mcp` if your project is in the EU.
