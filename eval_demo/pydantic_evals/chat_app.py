"""Live customer support chat, traced to Logfire.

    uv run eval_demo/pydantic_evals/chat_app.py

It calls the same `bot.reply()` that eval_support.py grades. Each typed turn
is a span nested under one `conversation` span. Type `quit` to exit.

The spans record the turn number only. Set LOGFIRE_LOG_CHAT=1 to also send
the customer message, the reply, and the conversation history.
"""

import os
import sys
from pathlib import Path

import logfire

import bot

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from logfire_setup import configure_logfire

# A person types slower than the free-tier limit, so skip the pacing delay.
bot.REQUEST_INTERVAL_SECONDS = 0

LOG_CHAT_TEXT = os.environ.get("LOGFIRE_LOG_CHAT") == "1"


def main() -> None:
    configure_logfire("customer-support-chat")
    logfire.instrument_google_genai()

    print("Customer Support Chat (type 'quit' to exit)")
    print("-" * 45)

    history: list[dict] = []
    turn_number = 0

    with logfire.span("conversation") as conversation:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except EOFError:
                break
            if user_input.lower() == "quit":
                break
            if not user_input:
                continue

            turn_number += 1
            turn_fields: dict = {"turn_number": turn_number}
            if LOG_CHAT_TEXT:
                turn_fields["customer_message"] = user_input
            with logfire.span("turn_{turn_number}", **turn_fields) as turn:
                answer = bot.reply(user_input, history=history, temperature=1.0)
                if LOG_CHAT_TEXT:
                    turn.set_attribute("agent_reply", answer)

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": answer})
            print(f"\nAgent: {answer}")

        conversation.set_attribute("total_turns", turn_number)
        if LOG_CHAT_TEXT:
            conversation.set_attribute("history", history)


if __name__ == "__main__":
    main()
