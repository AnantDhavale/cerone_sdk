"""Lightweight CLI for first-run Cerone onboarding."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from cerone import CeroneClient, ValidationError, __version__


def _format_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _mask_token(token: str) -> str:
    if not token:
        return "(missing)"
    if len(token) <= 20:
        return token
    return f"{token[:12]}...{token[-4:]}"


def _run_doctor(base_url: str) -> int:
    client = CeroneClient(api_key=None, base_url=base_url)
    try:
        health = client.health_check()
        status = str(health.get("status", "unknown"))
        print(f"Cerone {__version__}")
        print("Runtime governance for AI agents.")
        print(f"API: {client.base_url}")
        print(f"Health: {status}")
        if health and status != "healthy":
            print(_format_json(health))

        client._ensure_api_key()
        token = client.api_key or ""
        masked = _mask_token(token)

        usage = client._request("GET", "/usage", _allow_private_request=True)
        remaining = usage.get("remaining")
        print("\nHosted trial is live.")
        print(f"Trial token issued: {masked}")
        print(f"{remaining} validations included for this hosted trial.")
        print("Cerone auto-stops before the hard cap to protect your account and infrastructure.")
        print("No signup. No model proxy. Your model key stays yours.")

        print("\nWhat Cerone gives you:")
        print("- cryptographic agent identity")
        print("- runtime decisions: approved, flagged, rejected")
        print("- audit and trust signals around each action")

        print("\nTry this next:")
        print("from cerone import CeroneClient")
        print("client = CeroneClient()")
        print('agent = client.create_agent("Answer customer billing questions and look up billing records.", ["db_read", "billing_api"])')
        print("# For one action, start with validate(...).")
        print('result = client.validate(agent.agent_id, "database_query", {"customer_id": "123"})')
        print("client.close()")
        print("# Use validate_batch([...]) only when you have two or more items.")
        print('print(result.result, result.trust_score)')
        return 0
    except ValidationError as exc:
        print(f"Cerone trial bootstrap failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(f"Cerone CLI failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


def _run_demo(base_url: str) -> int:
    client = CeroneClient(api_key=None, base_url=base_url)
    try:
        print("Running a live validation against your trial...\n")
        client._ensure_api_key()

        agent = client.create_agent(
            "Answer customer billing questions and look up billing records.",
            ["db_read", "billing_api"],
            environment="development",
        )
        result = client.validate(
            agent.agent_id,
            "database_query",
            {"customer_id": "123"},
        )
        usage = client._request("GET", "/usage", _allow_private_request=True)
        remaining = usage.get("remaining")

        print('✓ Agent created: "Demo Agent" (customer billing support)')
        print("✓ Action validated: database_query")
        print(f"  Result: {result.result.value}")
        print(f"  Trust score: {result.trust_score:.2f}")
        print(f"  Latency: {result.latency_ms}ms")
        if remaining is not None:
            print(f"\nYour trial is working. {remaining} validations remaining.")
        else:
            print("\nYour trial is working.")

        print("\nNext: drop this into your project:")
        print("──────────────────────────────────────")
        print("from cerone import CeroneClient, infer_agent_profile_from_action")
        print("client = CeroneClient()")
        print('profile = infer_agent_profile_from_action("file_read", {"path": "README.md"}, workspace_target="repository files such as README.md")')
        print('agent = client.create_agent(profile.purpose, profile.capabilities, environment="development")')
        print('result = client.validate(agent.agent_id, "file_read", {"path": "README.md"})')
        print("print(result.result, result.trust_score)")
        print("client.close()")
        print("──────────────────────────────────────")
        return 0
    except ValidationError as exc:
        print(f"Cerone demo failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(f"Cerone demo failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cerone",
        description="Cerone CLI for hosted trial bootstrap and connectivity checks.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("doctor", "demo"),
        default="doctor",
        help="Run onboarding checks (`doctor`) or a live trial activation demo (`demo`).",
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
    if args.command == "demo":
        return _run_demo(args.base_url)
    return _run_doctor(args.base_url)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
