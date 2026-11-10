import argparse
import sys
from pathlib import Path

import logfire

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from logfire_setup import configure_logfire


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate, enrich, and store orders.")
    parser.add_argument("--orders", type=Path, default=HERE / "orders.json")
    parser.add_argument("--db", type=Path, default=HERE / "orders.db")
    args = parser.parse_args()

    # configure() first. instrument_pydantic() must run before models are imported.
    configure_logfire("order-pipeline")
    logfire.instrument_pydantic(record="failure")
    logfire.instrument_httpx()
    logfire.instrument_sqlite3()
    orders_processed = logfire.metric_counter(
        "orders_processed",
        unit="1",
        description="Orders written to SQLite",
    )

    from pipeline.steps import enrich, load, save, validate

    with logfire.span("run order pipeline", orders_path=str(args.orders)):
        with logfire.span("load orders", orders_path=str(args.orders)):
            raw_orders = load(args.orders)
            logfire.info("loaded {count} orders", count=len(raw_orders))

        with logfire.span("validate orders", count=len(raw_orders)):
            valid_orders, validation_errors = validate(raw_orders)
            logfire.info(
                "validated {valid} of {count} orders",
                valid=len(valid_orders),
                count=len(raw_orders),
            )

        with logfire.span("enrich orders", count=len(valid_orders)):
            enriched_orders, enrich_errors = enrich(valid_orders)

        with logfire.span("save orders", count=len(enriched_orders), db_path=str(args.db)):
            saved = save(enriched_orders, args.db)
            orders_processed.add(saved)
            logfire.info("saved {saved} orders", saved=saved)

    print(f"loaded={len(raw_orders)} valid={len(valid_orders)} saved={saved}")
    for error in validation_errors + enrich_errors:
        print(f"error: {error}")


if __name__ == "__main__":
    main()
