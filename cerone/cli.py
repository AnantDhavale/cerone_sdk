"""Lightweight CLI for first-run Cerone onboarding."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from cerone import CeroneClient, ValidationError, __version__


def _format_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _run_doctor(base_url: str) -> int:
    client = CeroneClient(api_key=None, base_url=base_url)
    try:
        print(f"Cerone {__version__}")
        print(f"Base URL: {client.base_url}")

        health = client.health_check()
        status = str(health.get("status", "unknown"))
        print(f"Health: {status}")
        if health and status != "healthy":
            print(_format_json(health))

        client._ensure_api_key()
        token = client.api_key or ""
        masked = f"{token[:12]}..." if token else "(missing)"
        print(f"Trial token: {masked}")

        usage = client._request("GET", "/usage")
        remaining = usage.get("remaining")
        stoploss = usage.get("trial_stoploss_limit")
        hard_limit = usage.get("validations_limit")
        print(
            "Hosted trial ready: "
            f"{remaining} validations remaining "
            f"(stoploss {stoploss}, hard cap {hard_limit})."
        )

        print("\nNext step:")
        print("from cerone import CeroneClient")
        print("client = CeroneClient()")
        print('agent = client.create_agent("Customer billing support", ["db_read", "billing_api"])')
        print('result = client.validate(agent.agent_id, "database_query", {"customer_id": "123"})')
        return 0
    except ValidationError as exc:
        print(f"Cerone trial bootstrap failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(f"Cerone CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cerone",
        description="Cerone CLI for hosted trial bootstrap and connectivity checks.",
    )
    parser.add_argument(
        "--base-url",
        default="https://api.homersemantics.com",
        help="Override the Cerone / AZTP base URL.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the Cerone SDK version and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    return _run_doctor(args.base_url)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
