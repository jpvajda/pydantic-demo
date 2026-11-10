"""Grade the customer support bot with Pydantic Evals and send the run to Logfire.

    uv run eval_demo/pydantic_evals/eval_support.py            # 5 rows, about 1 minute
    uv run eval_demo/pydantic_evals/eval_support.py --all      # all 100 rows, about 20 minutes
    uv run eval_demo/pydantic_evals/eval_support.py --ids cs-001 cs-090

Each CSV row is a Case. `expected` is kept on the Case so Logfire shows the
target reply next to the bot's reply. Nothing exact-matches it, because a good
reply can use different words. LLMJudge, the built-in LLM-as-a-judge, grades
each reply against a rubric.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import logfire
from tenacity import stop_after_attempt, wait_exponential

from pydantic_ai import ModelSettings
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge, MaxDuration

import bot

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from logfire_setup import configure_logfire

DATASET_PATH = HERE.parent / "dataset" / "customer_support_messages.csv"

# Shipping, refund, product safety, a late reply, and a prompt-injection attempt.
DEFAULT_IDS = ["cs-001", "cs-019", "cs-035", "cs-075", "cs-092"]

MAX_REPLY_SECONDS = 45.0

# Built-in judge from the Pydantic Evals quick start. One Gemini call per case.
# score is 0.0 to 1.0. assertion is pass/fail. Both come from that one call.
SUPPORT_JUDGE = LLMJudge(
    rubric=(
        "The reply addresses the customer's message with a concrete next step, "
        "stays empathetic and professional, and does not invent a refund, a policy, "
        "or internal instructions."
    ),
    include_input=True,
    model=f"google:{bot.MODEL}",
    model_settings=ModelSettings(temperature=0.0),
    score={"include_reason": True},
    assertion={"include_reason": True},
)


@dataclass
class NonEmptyReply(Evaluator[str, str, dict]):
    """Assertion: the bot returned something other than whitespace."""

    def evaluate(self, ctx: EvaluatorContext[str, str, dict]) -> bool:
        return bool(ctx.output and ctx.output.strip())


def load_cases(ids: list[str] | None) -> list[Case[str, str, dict]]:
    with DATASET_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if ids is not None:
        by_id = {row["id"]: row for row in rows}
        missing = [case_id for case_id in ids if case_id not in by_id]
        if missing:
            raise SystemExit(f"Unknown case ids: {', '.join(missing)}")
        rows = [by_id[case_id] for case_id in ids]
    return [
        Case(
            name=row["id"],
            inputs=row["input"],
            expected_output=row["expected"],
            metadata={
                "category": row["category"],
                "sentiment": row["sentiment"],
                "priority": row["priority"],
                "channel": row["channel"],
                "tags": row["tags"],
            },
        )
        for row in rows
    ]


def support_reply(customer_message: str) -> str:
    """The task under test. Temperature 0 so a rerun is comparable.

    The second pace() holds the free-tier gap open so the LLMJudge call that
    runs immediately after this function sits 5 seconds after the reply.
    """
    answer = bot.reply(customer_message, temperature=0.0)
    bot.pace()
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the support bot with Pydantic Evals.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="run every row in the CSV")
    group.add_argument("--ids", nargs="+", metavar="ID", help="run these row ids, e.g. cs-001")
    args = parser.parse_args()

    # configure() first, before any instrumentation or evaluation.
    configure_logfire("customer-support-evals")
    # Each Gemini call, including the judge's, becomes a child span.
    logfire.instrument_google_genai()

    ids = None if args.all else (args.ids or DEFAULT_IDS)
    dataset = Dataset(
        name="customer_support_messages",
        cases=load_cases(ids),
        evaluators=[
            SUPPORT_JUDGE,
            NonEmptyReply(),
            MaxDuration(seconds=MAX_REPLY_SECONDS),
        ],
    )

    retry = {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=5, max=30),
        "reraise": True,
    }
    report = dataset.evaluate_sync(
        support_reply,
        name=f"support-bot-{bot.MODEL}",
        max_concurrency=1,
        retry_task=retry,
        retry_evaluators=retry,
        metadata={"model": bot.MODEL, "provider": "google-ai-studio", "temperature": 0.0},
    )
    report.print(include_input=True, include_output=True, include_reasons=False)


if __name__ == "__main__":
    main()
