import logfire

logfire.configure()

with logfire.span("greeting"):
    logfire.info("Hello, {name}!", name="world")
