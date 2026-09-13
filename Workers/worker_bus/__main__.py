"""`python -m worker_bus` -- ask the workers something from a command line.

`host.py` gave the bus a way to be built. This gives it a way to be *run*, by a
person, on a machine, without writing Python first. Those are different gaps and
only closing the first one leaves `describe()` in the same condition the bus was
in before: a correct function with no caller outside its own tests.

Two commands, because two questions are worth asking:

    python -m worker_bus status
    python -m worker_bus ask JOE read_back_load load_id=LOAD-...

`status` answers "what can this machine's workers do right now", and it answers
it **without running a worker** -- `Dispatch/CLAUDE.md` D9: retrieval is not
modification, so asking what is possible must not do anything.

`ask` runs exactly one capability and prints the answer. It prints the status
word first and the sentence second, because the status word is what decides
whether the sentence can be trusted, and a person reading `UNCONFIGURED` should
not have to read three lines to find that out.

Nothing here can write to Dispatch. It builds the same `DispatchReader` every
other caller gets, and that reader has no write method to reach.
"""

from __future__ import annotations

import argparse
import json
import sys

from worker_bus.contracts import ContractError, WorkerRequest
from worker_bus.host import build_bus, describe

#: What the caller is, in `requested_by`. Not "DISPATCH": Dispatch is not what is
#: asking, a person at a terminal is, and the audit line should say so.
OPERATOR = "OPERATOR"


def _parse_payload(pairs: list[str]) -> dict:
    """`key=value` arguments into a payload.

    Values stay strings unless they parse as JSON. That way `confidence=0.8`
    arrives as a number and `heard=picked up at 3` arrives as the sentence
    somebody actually said, without needing to be quoted as JSON.
    """
    payload: dict = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"expected key=value, got {pair!r}")
        try:
            payload[key] = json.loads(value)
        except (ValueError, TypeError):
            payload[key] = value
    return payload


def _print_status(as_json: bool) -> int:
    report = describe()
    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    print("Dispatch readable:  " + ("yes" if report["dispatch_readable"] else "no"))
    print("Assistant plug-in:  " + ("present" if report["plugin_present"] else "absent"))
    print()
    for entry in report["workers"]:
        print(f"{entry['worker']:<14} {entry['status']}")
        for capability in entry.get("capabilities", ()):
            name = capability["name"] if isinstance(capability, dict) else capability
            summary = capability.get("summary", "") if isinstance(capability, dict) else ""
            print(f"    {name:<20} {summary}")
    return 0


def _print_response(response, as_json: bool) -> int:
    if as_json:
        print(json.dumps(response.to_dict(), indent=2))
        return 0 if response.actionable else 1

    # Status first. It is what tells the reader whether to believe the rest.
    print(f"{response.worker} {response.capability}: {response.status}")
    # `refuse()` copies the reason into `detail`, so printing both says the same
    # sentence twice and buries the remedy, which is the part worth reading.
    if response.detail and not (response.refusal and response.detail == response.refusal.reason):
        print(response.detail)
    if response.refusal:
        print(f"  refused under {response.refusal.rule}: {response.refusal.reason}")
        if response.refusal.remedy:
            print(f"  {response.refusal.remedy}")
    for finding in response.findings:
        print(f"  [{finding.confidence}] {finding.code}: {finding.summary}")
    for recommendation in response.recommendations:
        print(f"  -> {recommendation}")

    # Some answers are entirely in the artifacts -- an empty shelf comes back
    # ABSENT with nothing else, which on a terminal is one bare word and no
    # reason. Showing what came back is honest; writing a sentence the worker
    # did not say would not be.
    if not (response.detail or response.findings or response.recommendations
            or response.refusal):
        for key, value in sorted(response.artifacts.items()):
            print(f"  {key}: {json.dumps(value)}")

    # Exit non-zero when the answer is not something a person can act on, so a
    # script calling this does not mistake UNCONFIGURED for success.
    return 0 if response.actionable else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m worker_bus",
        description="Ask Intelligence, Publisher, Joe or Library for one thing.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="what the workers can do on this machine")

    ask = sub.add_parser("ask", help="run one capability")
    ask.add_argument("worker", help="INTELLIGENCE, PUBLISHER, JOE or LIBRARY")
    ask.add_argument("capability")
    ask.add_argument("payload", nargs="*", metavar="key=value")
    # There is deliberately no --authorized-by flag. A terminal is not an
    # authenticated action, and CLAUDE.md section 4 forbids manufacturing a Mike
    # attribution "not as a default, not as a seed, not as a test fixture, not
    # as an inference". Typing a name at a prompt is all four. A capability that
    # requires a recorded human decision therefore always refuses from here, and
    # the refusal says to record the decision in Dispatch first -- which is the
    # correct answer, not a missing feature.

    args = parser.parse_args(argv)

    # No subcommand is the same question as `status`, because somebody typing
    # the bare command wants to know what is here.
    if args.command in (None, "status"):
        return _print_status(args.json)

    try:
        request = WorkerRequest(
            capability=args.capability,
            payload=_parse_payload(args.payload),
            requested_by=OPERATOR,
        )
    except ContractError as exc:
        print(f"bad request: {exc}", file=sys.stderr)
        return 2

    # An unknown worker and an undeclared capability are both refusals the bus
    # already makes, by name and with the list of what it does declare. Checking
    # for them here would be a second answer to a question that has one.
    return _print_response(build_bus().ask(args.worker.upper(), request), args.json)


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
