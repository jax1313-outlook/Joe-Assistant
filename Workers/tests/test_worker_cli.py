"""`python -m worker_bus` -- the part a person can actually type.

`host.py` closed the gap where the bus could not be built outside a test.
`__main__.py` closes the next one: a `build_bus()` nothing invokes is the same
defect one layer up. These tests exist so that stays true -- every one of them
calls `main()` the way a shell would, with a list of arguments and an exit code.

The two that matter most are the last two. One proves the command cannot be
talked into manufacturing a Mike attribution; the other proves it cannot write.
"""

from __future__ import annotations

import json

import pytest

from worker_bus.__main__ import main


@pytest.fixture()
def no_library(monkeypatch):
    """A machine with no Library repo on it.

    The Library is a separate repository -- THE MIKE RULE keeps it liftable --
    so its absence is an ordinary configuration, not a broken install, and the
    CLI has to be readable on a machine that does not have it.
    """
    import worker_bus.host as host

    monkeypatch.setattr(host, "_LIBRARY_SERVICE", None)
    monkeypatch.setattr(host, "ensure_library_importable", lambda: False)
    yield


@pytest.fixture()
def seeded(tmp_path, monkeypatch):
    """A real Dispatch with one real load, exactly as the host tests build it."""
    pytest.importorskip("dispatch")
    monkeypatch.setenv("PORTAL_DATA_DIR", str(tmp_path / "portal"))
    from dispatch import db, services

    db.set_db_path(tmp_path / "portal" / "dispatch.db")
    try:
        driver = services.create_driver(name="Jane Trucker", phone="555-0000")
        load = services.create_load(
            customer="Host Co", broker_shipper="TQL", driver_id=driver["driver_id"],
            pickup_location="Dallas TX", delivery_location="Houston TX",
            pickup_datetime="2026-07-30 06:00 - 10:00",
            delivery_datetime="2026-07-30 16:00 - 20:00",
        )
        services.add_milestone(load["load_id"], event_type="dispatched")
        yield load["load_id"]
    finally:
        db.set_db_path(None)


class TestStatus:
    def test_the_bare_command_answers_the_same_question_as_status(self, capsys):
        assert main([]) == 0
        bare = capsys.readouterr().out
        assert main(["status"]) == 0
        assert capsys.readouterr().out == bare

    def test_it_names_every_worker_and_what_each_will_do(self, capsys):
        assert main(["status"]) == 0
        out = capsys.readouterr().out
        for worker in ("INTELLIGENCE", "PUBLISHER", "JOE", "LIBRARY"):
            assert worker in out
        assert "read_back_load" in out
        assert "check_readiness" in out

    def test_json_is_machine_readable(self, capsys):
        assert main(["--json", "status"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert set(report) == {
            "dispatch_readable", "plugin_present", "library_present", "workers"
        }
        assert {w["worker"] for w in report["workers"]} == {
            "INTELLIGENCE", "PUBLISHER", "JOE", "LIBRARY"
        }

    def test_asking_what_is_possible_runs_nothing(self, seeded):
        """D9: retrieval is not modification. `status` reports what the workers
        *would* do, and a report that quietly ran three duties to find out would
        be the opposite of the rule."""
        assert _fingerprint() == _run_and_fingerprint(["status"])


class TestAsk:
    def test_it_reads_a_real_load_back(self, seeded, capsys):
        assert main(["ask", "JOE", "read_back_load", f"load_id={seeded}"]) == 0
        out = capsys.readouterr().out
        # Status word first, on its own line, before anything a person might act
        # on. That ordering is the whole point of the format.
        assert out.splitlines()[0] == "JOE read_back_load: LIVE"
        assert "Houston TX" in out

    def test_publisher_and_intelligence_answer_too(self, seeded, capsys):
        assert main(["ask", "PUBLISHER", "check_readiness", f"load_id={seeded}"]) == 0
        assert main(["ask", "INTELLIGENCE", "assess_load", f"load_id={seeded}"]) == 0
        out = capsys.readouterr().out
        assert "PUBLISHER check_readiness: LIVE" in out
        assert "INTELLIGENCE assess_load: LIVE" in out
        assert "RATE_MISSING" in out

    def test_json_carries_the_whole_response(self, seeded, capsys):
        assert main(["--json", "ask", "JOE", "read_back_load", f"load_id={seeded}"]) == 0
        body = json.loads(capsys.readouterr().out)
        assert body["status"] == "LIVE"
        assert body["worker"] == "JOE"
        assert body["refusal"] is None
        assert body["correlation_id"]


class TestItRefusesReadably:
    def test_an_unknown_worker_names_the_ones_that_exist(self, capsys):
        assert main(["ask", "MANAGER", "do_something"]) == 1
        out = capsys.readouterr().out
        assert "worker_not_registered" in out
        assert "INTELLIGENCE, JOE, LIBRARY, PUBLISHER" in out

    def test_an_undeclared_capability_names_the_declared_ones(self, capsys):
        assert main(["ask", "JOE", "fly_the_truck"]) == 1
        out = capsys.readouterr().out
        assert "undeclared_capability" in out
        assert "read_back_load" in out

    def test_a_refusal_is_said_once(self, capsys):
        """`refuse()` copies its reason into `detail`. Printing both says the
        same sentence twice and pushes the remedy off the top of a terminal."""
        main(["ask", "JOE", "fly_the_truck"])
        out = capsys.readouterr().out
        assert out.count("does not declare") == 1

    def test_a_missing_load_is_a_refusal_not_an_invention(self, seeded, capsys):
        assert main(["ask", "JOE", "read_back_load", "load_id=NOPE"]) == 1
        out = capsys.readouterr().out
        assert "subject_not_found" in out
        assert "does not fill in a gap out loud" in out

    def test_an_unusable_answer_exits_non_zero(self, no_library, capsys):
        """With no Library on the machine there is no shelf to read, so the
        answer is ABSENT. A script reading exit 0 would treat "there is
        nothing" as a result.

        This asks for a machine without the Library deliberately. A real
        Library that happens to be empty is LIVE and exits 0 -- "the shelf is
        there and nothing is on it" is a usable answer, and collapsing it into
        the same word as "there is no shelf" is the distinction the whole
        vocabulary exists to keep.
        """
        code = main(["ask", "LIBRARY", "list_assets"])
        out = capsys.readouterr().out
        assert code == 1, out
        assert out.splitlines()[0] == "LIBRARY list_assets: ABSENT"

    def test_an_answer_that_is_only_artifacts_still_says_something(self, no_library, capsys):
        """ABSENT with no detail and no findings prints as one bare word. What
        came back is shown instead -- which is a fact, where a sentence written
        here to fill the space would be an invention."""
        main(["ask", "LIBRARY", "list_assets"])
        assert "assets: []" in capsys.readouterr().out

    def test_a_payload_argument_without_a_value_is_rejected(self):
        with pytest.raises(SystemExit) as raised:
            main(["ask", "JOE", "read_back_load", "load_id"])
        assert "key=value" in str(raised.value)


class TestPayloadParsing:
    def test_a_number_arrives_as_a_number_and_a_sentence_as_a_sentence(self):
        from worker_bus.__main__ import _parse_payload

        parsed = _parse_payload(["confidence=0.8", "heard=picked up at 3", "n=2"])
        assert parsed == {"confidence": 0.8, "heard": "picked up at 3", "n": 2}

    def test_a_value_containing_an_equals_sign_survives(self):
        from worker_bus.__main__ import _parse_payload

        assert _parse_payload(["q=a=b"]) == {"q": "a=b"}


class TestTheTwoThingsItMustNotDo:
    def test_there_is_no_way_to_claim_somebody_authorised_this(self, capsys):
        """CLAUDE.md §4.3 forbids manufacturing a Mike attribution "not as a
        default, not as a seed, not as a test fixture, not as an inference".
        Typing a name at an unauthenticated prompt is all four, so the flag does
        not exist -- and the capability that needs one refuses from here every
        time, with the remedy naming what would actually satisfy it."""
        with pytest.raises(SystemExit):
            main(["ask", "PUBLISHER", "assemble_completion_package",
                  "--authorized-by", "Mike"])
        capsys.readouterr()

        assert main(["ask", "PUBLISHER", "assemble_completion_package",
                     "load_id=X"]) == 1
        out = capsys.readouterr().out
        assert "human_authorization_required" in out
        assert "Record the decision first" in out

    def test_no_command_writes_a_single_row(self, seeded):
        """§5.4, measured through the command line rather than through the bus,
        because the command line is the surface a person will actually use."""
        before = _fingerprint()
        for argv in (
            ["status"],
            ["ask", "INTELLIGENCE", "assess_load", f"load_id={seeded}"],
            ["ask", "PUBLISHER", "check_readiness", f"load_id={seeded}"],
            ["ask", "JOE", "read_back_load", f"load_id={seeded}"],
            ["ask", "JOE", "read_back_load", "load_id=NOPE"],
        ):
            main(argv)
        assert _fingerprint() == before


# ── helpers ──────────────────────────────────────────────────────────────


def _fingerprint() -> str:
    """Every table's row count, hashed. A write anywhere changes it."""
    import hashlib

    from dispatch import db

    with db.get_connection() as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = [f"{t}={conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}"
                  for t in tables]
    return hashlib.sha256("|".join(counts).encode()).hexdigest()


def _run_and_fingerprint(argv: list[str]) -> str:
    main(argv)
    return _fingerprint()
