"""JOE - entry point.

    py joe_main.py            open the window
    py joe_main.py --status   print status and exit
    py joe_main.py --headless "question"   ask once, print, exit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import AssistantService, Config, ConfigError  # noqa: E402


def _service(args) -> AssistantService:
    config = Config.load(args.config) if args.config else Config.load()
    return AssistantService(config)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="assistant", description="JOE, the Level 1 Assistant"
    )
    parser.add_argument("--config", default=None)
    parser.add_argument("--status", action="store_true", help="Print status and exit.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--headless", default=None, metavar="QUESTION")
    parser.add_argument(
        "--accounts", action="store_true",
        help="List the Outlook accounts available to JOE.",
    )
    parser.add_argument(
        "--voice-test", action="store_true",
        help="Open the window in voice-input test mode.",
    )
    args = parser.parse_args(argv)

    try:
        service = _service(args)
    except ConfigError as error:
        print("Configuration problem: " + str(error), file=sys.stderr)
        return 2

    if args.status:
        if args.json:
            print(json.dumps(service.status_dict(), indent=2))
        else:
            print("JOE, the Level 1 Assistant")
            print("Operating mode: " + service.operating_mode())
            for status in service.status():
                print("  " + status.display())
            print("  Dispatch contacted: False    Operational writes: 0")
        return 0

    if args.accounts:
        accounts = service.outlook.accounts()
        if args.json:
            print(json.dumps(accounts, indent=2))
            return 0
        if not accounts:
            print("No Outlook accounts could be read.")
            print("  " + (service.outlook.last_error or "Outlook may be disabled in configuration."))
            return 1
        print("Outlook accounts in this profile:")
        for account in accounts:
            mark = "  * " if account.get("is_default") else "    "
            print(mark + str(account.get("smtp", "")))
            print("      display name: " + str(account.get("display_name", "")))
            print("      store:        " + str(account.get("store", "")))
        print()
        print("  * = Outlook default store")
        print("  currently configured: " + (service.outlook.account or "(default store)"))
        print("  in use:               " + service.outlook.account_in_use())
        return 0

    if args.headless:
        interaction = service.ask(args.headless)
        if args.json:
            print(json.dumps(interaction.response.to_dict(), indent=2))
        else:
            print(interaction.response.answer)
            print()
            print(interaction.response.written)
        return 0

    from ui.window import AssistantWindow

    AssistantWindow(service, voice_test=args.voice_test).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
