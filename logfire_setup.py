"""Logfire setup shared by the demo entrypoints.

The write token lives in `.logfire/` at the repository root. Run
`uvx logfire-cli init` from that directory. An init inside a demo folder
writes a second token these entrypoints do not read.
"""

from pathlib import Path

import logfire

ROOT = Path(__file__).resolve().parent


def configure_logfire(service_name: str) -> None:
    logfire.configure(
        service_name=service_name,
        service_version="0.1.0",
        environment="dev",
        send_to_logfire="if-token-present",
        data_dir=ROOT / ".logfire",
    )
