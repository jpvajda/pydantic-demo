import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from logfire_setup import configure_logfire

configure_logfire("hello-world")

import logfire

with logfire.span("greeting"):
    logfire.info("Hello, {name}!", name="world")
