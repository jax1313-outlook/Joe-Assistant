"""Microsoft behind ports, with the four things that always bite, and no claims.

`Dispatch/CLAUDE.md` records the General Contractor Doctrine: "Use the provider;
own the interface." A port is how the interface is owned, and the cost of not
owning it is not felt until the day the wheel has to come off.

**Nothing in this module has been run against Microsoft.** Every test drives
recorded response shapes through an injected opener. What is proven: request
shapes, the paging walk, delta handling, the retry rules, error translation, and
that no adapter claims LIVE without a call. What is not proven: connectivity,
and no test here pretends otherwise.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from m365.adapters.graph import GraphCalendar, GraphChat, GraphDocuments, GraphFiles, GraphMail, GraphSite
from m365.adapters.local import LocalCalendar, LocalFiles, LocalMail, UnavailableChat, UnavailableSite
from m365.graph_client import GraphClient, GraphError
from m365.ports import TRUTH_WORDS, Result
from m365.registry import build_suite


class Token:
    def __init__(self, status="LIVE", account="mike@example.com"):
        self._status, self._account = status, account
        self.refreshes = 0

    def status(self): return self._status
    def account(self): return self._account

    def access_token(self):
        if self._status == "UNCONFIGURED":
            raise RuntimeError("no account connected")
        return f"tok-{self.refreshes}"


class Response:
    def __init__(self, payload=None, raw=None, status=200):
        self._body = raw if raw is not None else json.dumps(payload or {}).encode()
        #: An upload session distinguishes "chunk accepted, send the next" (202)
        #: from "that was the last one" (200/201) by status alone -- the bodies
        #: do not say.
        self.status = status

    def read(self): return self._body
    def __enter__(self): return self
    def __exit__(self, *a): return False


def http_error(code, *, message="no", retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError(
        "https://graph.microsoft.com/v1.0/x", code, "err", headers,
        io.BytesIO(json.dumps({"error": {"code": "e", "message": message}}).encode()),
    )


class Opener:
    """Replays scripted answers and records every request."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        answer = self.answers.pop(0) if self.answers else Response({})
        if isinstance(answer, Exception):
            raise answer
        return answer


def client(*answers, token=None, slept=None, max_attempts=None):
    kw = {} if max_attempts is None else {"max_attempts": max_attempts}
    return GraphClient(
        token_provider=token or Token(),
        opener=Opener(*answers),
        sleeper=(slept.append if slept is not None else (lambda s: None)),
        **kw,
    )


class TestTheClient:
    def test_it_carries_the_bearer_token(self):
        graph = client(Response({"value": []}))
        graph.get("me/events")
        assert graph.opener.requests[0].headers["Authorization"] == "tok-0"[:0] + "Bearer tok-0"

    def test_it_walks_every_page(self):
        """A caller that stops at the first page believes it has everything, and
        nothing about the result says otherwise."""
        graph = client(
            Response({"value": [1, 2], "@odata.nextLink": "https://graph/next"}),
            Response({"value": [3]}),
        )
        assert graph.get_all("me/events") == [1, 2, 3]
        assert len(graph.opener.requests) == 2

    def test_paging_stops_at_the_limit(self):
        graph = client(
            Response({"value": [1, 2], "@odata.nextLink": "https://graph/next"}),
            Response({"value": [3, 4]}),
        )
        assert graph.get_all("me/events", limit=3) == [1, 2, 3]

    def test_a_self_referential_next_link_cannot_loop_forever(self):
        answers = [Response({"value": [1], "@odata.nextLink": "https://graph/same"})
                   for _ in range(200)]
        graph = client(*answers)
        assert len(graph.get_all("me/events")) < 200

    def test_delta_returns_the_token_and_does_not_keep_it(self):
        """A delta token cached inside a client outlives the collection it
        describes, and produces a silent gap."""
        graph = client(Response({"value": [{"id": "1"}], "@odata.deltaLink": "https://d/1"}))
        outcome = graph.delta("me/calendarView/delta")
        assert outcome["delta_token"] == "https://d/1"
        assert not hasattr(graph, "_delta_token")

    def test_a_delta_token_is_used_as_the_url(self):
        graph = client(Response({"value": []}))
        graph.delta("me/calendarView/delta", token="https://graph/delta-abc")
        assert graph.opener.requests[0].full_url == "https://graph/delta-abc"

    def test_a_429_waits_exactly_as_long_as_microsoft_says(self):
        slept = []
        graph = client(http_error(429, retry_after="7"), Response({"value": []}),
                       slept=slept)
        graph.get("me/events")
        assert slept == [7.0], "the Retry-After header is authoritative"

    def test_a_429_without_a_header_backs_off(self):
        slept = []
        graph = client(http_error(429), Response({"value": []}), slept=slept)
        graph.get("me/events")
        assert slept and slept[0] > 0

    @pytest.mark.parametrize("code", [500, 502, 503, 504])
    def test_server_errors_are_retried(self, code):
        graph = client(http_error(code), Response({"value": []}))
        assert graph.get("me/events") == {"value": []}

    @pytest.mark.parametrize("code", [400, 403, 404, 409])
    def test_an_answer_is_not_retried(self, code):
        graph = client(http_error(code), Response({"value": []}))
        with pytest.raises(GraphError) as caught:
            graph.get("me/events")
        assert caught.value.retryable is False
        assert len(graph.opener.requests) == 1, "retrying an answer changes nothing"

    def test_a_401_refreshes_once_then_gives_up(self):
        graph = client(http_error(401), http_error(401), Response({"value": []}))
        with pytest.raises(GraphError):
            graph.get("me/events")
        assert len(graph.opener.requests) == 2, (
            "a second 401 after a fresh token is a permissions problem, not a stale one"
        )

    def test_it_gives_up_after_max_attempts(self):
        graph = client(*[http_error(503) for _ in range(10)])
        with pytest.raises(GraphError):
            graph.get("me/events")
        assert len(graph.opener.requests) == graph.max_attempts

    def test_an_unconnected_account_never_reaches_the_network(self):
        graph = client(Response({}), token=Token(status="UNCONFIGURED"))
        with pytest.raises(GraphError):
            graph.get("me/events")
        assert graph.opener.requests == []


class TestCalendar:
    def test_it_reads_and_labels_the_source(self):
        graph = client(Response({"value": [{
            "id": "E1", "subject": "Pickup", "start": {"dateTime": "2026-09-14T08:00:00"},
            "end": {"dateTime": "2026-09-14T09:00:00"},
            "location": {"displayName": "Columbus OH"},
        }]}))
        result = GraphCalendar(graph).read_events(start="a", end="b")
        assert result.real
        assert result.data["events"][0]["source"] == "Outlook"

    def test_it_never_writes_without_a_recorded_decision(self):
        """CLAUDE.md 5.5: creating a calendar entry is an external side effect of
        a human's approval, not a state Dispatch passes through."""
        graph = client(Response({}))
        result = GraphCalendar(graph).propose_event(
            subject="Pickup", starts_at="a", ends_at="b")
        assert result.status == "MANUAL"
        assert result.data["proposed"]["subject"] == "Pickup"
        assert graph.opener.requests == [], "nothing was sent to Outlook"

    def test_an_authorised_event_is_created(self):
        graph = client(Response({"id": "E9"}))
        result = GraphCalendar(graph).propose_event(
            subject="Pickup", starts_at="a", ends_at="b",
            authorized_by="Mike", authorization_ref="DEC-1")
        assert result.real and result.data["event_id"] == "E9"

    def test_there_is_no_sync_method(self):
        """Dispatch must not create a second scheduling system, so there is
        nothing here that mirrors Outlook into a local table."""
        methods = [m for m in dir(GraphCalendar(client())) if not m.startswith("_")]
        assert not any("sync" in m or "mirror" in m or "import" in m for m in methods)

    def test_changed_since_hands_the_token_back(self):
        graph = client(Response({"value": [{"id": "1"}], "@odata.deltaLink": "https://d/2"}))
        result = GraphCalendar(graph).changed_since()
        assert result.data["delta_token"] == "https://d/2"

    def test_an_unconnected_account_is_unconfigured_not_an_error(self):
        result = GraphCalendar(client(token=Token(status="UNCONFIGURED"))).read_events(
            start="a", end="b")
        assert result.status == "UNCONFIGURED"
        assert "M365_ACTIVATION" in result.detail


class TestMailFilesSiteChatDocuments:
    def test_mail_sends_graph_json_and_saves_to_sent_items(self):
        graph = client(Response({}))
        result = GraphMail(graph).send(to=("ops@broker.test",), subject="s", body_text="t")
        payload = json.loads(graph.opener.requests[0].data.decode())
        assert payload["saveToSentItems"] is True
        assert payload["message"]["toRecipients"][0]["emailAddress"]["address"] == "ops@broker.test"
        assert result.real

    def test_a_file_over_four_megabytes_uses_an_upload_session(self):
        """It used to be refused. A driver's bill-of-lading photo is routinely
        3-8 MB, so the refusal refused the ordinary case."""
        size = 6 * 1024 * 1024  # two chunks: 5 MiB then 1 MiB
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            Response({"nextExpectedRanges": ["5242880-"]}, status=202),
            Response({"id": "F9", "name": "big.pdf", "size": size,
                      "webUrl": "https://one/big"}, status=201),
        )
        result = GraphFiles(graph).put(path="big.pdf", content=b"x" * size)
        assert result.status == "LIVE", result.detail
        assert result.data["file"]["file_id"] == "F9"
        assert result.data["resumed"] == 0

    def test_a_file_is_stored_with_its_identifiers(self):
        graph = client(Response({"id": "F1", "name": "bol.pdf", "size": 12,
                                 "webUrl": "https://one/x"}))
        result = GraphFiles(graph).put(path="bol.pdf", content=b"x" * 12)
        assert result.data["file"]["file_id"] == "F1"

    def test_a_site_without_configuration_says_so(self):
        assert GraphSite(client()).list_documents().status == "UNCONFIGURED"

    def test_teams_will_not_post_something_nobody_approved(self):
        graph = client(Response({}))
        result = GraphChat(graph, team_id="T1").post_notice(channel="C1", text="hello")
        assert result.status == "MANUAL"
        assert graph.opener.requests == []

    def test_docx_is_refused_by_name_rather_than_quietly_substituted(self):
        result = GraphDocuments(client()).render(title="T", sections=(), fmt="docx")
        assert result.status == "ABSENT"
        assert "does not author one" in result.detail

    def test_local_rendering_is_simulated_and_touches_nothing(self):
        graph = client()
        result = GraphDocuments(graph).render(
            title="Completion", sections=(("Load", "LD-1"),), fmt="html")
        assert result.status == "SIMULATED"
        assert b"Completion" in result.data["content"]
        assert graph.opener.requests == []


class TestTheLocalSubstitutes:
    def test_they_say_simulated_and_never_live(self, tmp_path):
        mail = LocalMail(tmp_path / "Outbox")
        result = mail.send(to=("a@b.test",), subject="s", body_text="t")
        assert result.status == "SIMULATED"
        assert result.real is False, "a .eml on disk is not delivery"
        assert result.ok is True, "it did work; it just reached nobody"

    def test_a_local_file_round_trips(self, tmp_path):
        files = LocalFiles(tmp_path / "Drive")
        files.put(path="a/b.txt", content=b"hello")
        assert files.get(path="a/b.txt").data["content"] == b"hello"
        assert files.list(folder="a").data["files"][0]["name"] == "b.txt"

    def test_a_local_calendar_reads_a_file_an_operator_can_edit(self, tmp_path):
        source = tmp_path / "cal.json"
        source.write_text(json.dumps([
            {"id": "1", "subject": "Pickup", "start": "2026-09-14T08:00", "end": "..."}
        ]), encoding="utf-8")
        result = LocalCalendar(source).read_events(start="2026-09-01", end="2026-09-30")
        assert result.status == "SIMULATED"
        assert result.data["events"][0]["source"] == "local file"

    def test_there_is_no_pretend_sharepoint_or_teams(self):
        """A folder on this laptop is not a shared site, and writing a file does
        not tell anybody in Teams."""
        assert UnavailableSite().list_documents().status == "ABSENT"
        assert UnavailableChat().post_notice(channel="c", text="t").status == "ABSENT"


class TestTheSuite:
    def test_with_no_account_everything_falls_back_honestly(self, tmp_path, monkeypatch):
        for var in ("DISPATCH_MS_CLIENT_ID", "JOE_SHAREPOINT_SITE_ID", "JOE_TEAMS_TEAM_ID"):
            monkeypatch.delenv(var, raising=False)
        suite = build_suite(local_root=tmp_path)
        statuses = {row["port"]: row["status"] for row in suite.survey()}
        assert statuses["mail"] == "SIMULATED"
        assert statuses["site"] == "ABSENT"
        assert all(s in TRUTH_WORDS for s in statuses.values())

    def test_with_an_account_the_graph_adapters_are_used(self, tmp_path):
        suite = build_suite(local_root=tmp_path, provider=Token())
        assert all(row["provider"] == "microsoft_graph" for row in suite.survey())

    def test_the_report_says_what_simulated_means(self, tmp_path):
        rendered = build_suite(local_root=tmp_path).render()
        assert "reached nobody" in rendered

    def test_no_port_reports_live_without_a_connected_account(self, tmp_path):
        suite = build_suite(local_root=tmp_path)
        assert all(row["status"] != "LIVE" for row in suite.survey())


class TestTheResultType:
    def test_a_status_outside_the_eight_is_refused(self):
        with pytest.raises(ValueError, match="one of the eight"):
            Result("PROBABLY", "x")

    def test_simulated_is_ok_but_not_real(self):
        result = Result("SIMULATED", "wrote a file")
        assert result.ok and not result.real


class TestResumableUpload:
    """Files over 4 MB used to be refused by name.

    That refusal was not an edge case being declined: a driver photographing a
    bill of lading produces 3-8 MB routinely, so the ordinary case was the one
    being refused. These cover the session flow, and most of them are about the
    ways it could report a success it has no evidence for.
    """

    def _content(self, mib):
        return b"x" * (mib * 1024 * 1024)

    def test_the_chunk_size_is_a_multiple_of_320_kib(self):
        """Graph rejects any chunk but the last that is not. A named constant
        and an assertion, so a future tuning cannot quietly break uploads."""
        from m365.adapters.graph import UPLOAD_CHUNK_BYTES, UPLOAD_CHUNK_UNIT

        assert UPLOAD_CHUNK_UNIT == 320 * 1024
        assert UPLOAD_CHUNK_BYTES % UPLOAD_CHUNK_UNIT == 0
        assert 5 * 1024 * 1024 <= UPLOAD_CHUNK_BYTES <= 10 * 1024 * 1024

    def test_a_small_file_still_takes_the_simple_path(self):
        """One request, not a session. The session is overhead where it is not
        needed."""
        graph = client(Response({"id": "S1", "name": "small.pdf", "size": 10}))
        result = GraphFiles(graph).put(path="small.pdf", content=b"x" * 10)
        assert result.real
        assert len(graph.opener.requests) == 1
        assert "createUploadSession" not in graph.opener.requests[0].full_url

    def test_the_session_url_is_never_sent_an_authorization_header(self):
        """The uploadUrl carries its own pre-authorisation. Attaching a bearer
        token to it is a documented way to have the upload rejected."""
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            Response({"id": "F1", "size": 6 * 1024 * 1024}, status=201),
        )
        GraphFiles(graph).put(path="b.pdf", content=self._content(6))
        session_request = graph.opener.requests[0]
        chunk_request = graph.opener.requests[1]
        assert "Authorization" in session_request.headers
        assert "Authorization" not in chunk_request.headers, chunk_request.headers

    def test_each_chunk_declares_its_byte_range(self):
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            Response({"nextExpectedRanges": ["5242880-"]}, status=202),
            Response({"id": "F1", "size": 6 * 1024 * 1024}, status=201),
        )
        GraphFiles(graph).put(path="b.pdf", content=self._content(6))
        ranges = [r.headers.get("Content-range") for r in graph.opener.requests[1:]]
        total = 6 * 1024 * 1024
        assert ranges[0] == f"bytes 0-5242879/{total}"
        assert ranges[1] == f"bytes 5242880-{total - 1}/{total}"

    def test_graphs_own_next_expected_range_is_trusted_over_our_arithmetic(self):
        """Graph is the one that knows what actually landed. If it says resume
        from somewhere other than where we counted to, it wins."""
        total = 6 * 1024 * 1024
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            Response({"nextExpectedRanges": ["1000-"]}, status=202),
            Response({"id": "F1", "size": total}, status=201),
        )
        GraphFiles(graph).put(path="b.pdf", content=b"x" * total)
        assert graph.opener.requests[2].headers.get("Content-range").startswith("bytes 1000-")

    def test_a_dropped_connection_resumes_where_graph_says(self):
        """The whole point of resumable. Restarting from zero would be a large
        upload, not a resumable one, and on a phone tether that is the
        difference between finishing and never finishing."""
        total = 6 * 1024 * 1024
        # max_attempts=1 so the client's own retry budget does not absorb the
        # failure before the adapter's resume path can see it. Both layers are
        # real; this test is about the outer one.
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            http_error(503),                                  # chunk 1 dies
            Response({"nextExpectedRanges": ["5242880-"]}),   # session status
            Response({"id": "F1", "size": total}, status=201),
            max_attempts=1,
        )
        result = GraphFiles(graph).put(path="b.pdf", content=b"x" * total)
        assert result.real, result.detail
        assert result.data["resumed"] == 1
        assert "1 resume" in result.detail
        assert graph.opener.requests[-1].headers.get("Content-range").startswith("bytes 5242880-")

    def test_an_unrecoverable_failure_cancels_the_session(self):
        """Leaving it to expire holds a partial file, and the point of failing
        is to leave nothing behind that looks like a delivery."""
        total = 6 * 1024 * 1024
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            http_error(403),   # not retryable
            Response({}),      # the DELETE
        )
        result = GraphFiles(graph).put(path="b.pdf", content=b"x" * total)
        assert not result.real
        assert graph.opener.requests[-1].get_method() == "DELETE"

    def test_it_gives_up_rather_than_resuming_forever(self):
        """A bounded number of recoveries. An upload that cannot make progress
        should fail visibly, not retry until the session expires an hour later."""
        from m365.adapters.graph import MAX_UPLOAD_RECOVERIES

        total = 6 * 1024 * 1024
        answers = [Response({"uploadUrl": "https://up/1"})]
        for _ in range(MAX_UPLOAD_RECOVERIES + 2):
            answers.append(http_error(503))
            answers.append(Response({"nextExpectedRanges": ["0-"]}))
        answers.append(Response({}))
        graph = client(*answers, slept=[], max_attempts=1)
        result = GraphFiles(graph).put(path="b.pdf", content=b"x" * total)
        assert not result.real

    def test_a_session_with_no_upload_url_is_not_a_success(self):
        graph = client(Response({}))
        result = GraphFiles(graph).put(path="b.pdf", content=self._content(6))
        assert result.status == "UNAVAILABLE"
        assert "nowhere to send" in result.detail

    def test_bytes_sent_without_a_confirmed_item_is_unverified_not_live(self):
        """The bug this test was written for. If every chunk is accepted with a
        202 and Graph never returns the finished item, the bytes may well be
        there -- but 'may well be' is not a delivery, and LIVE would be a
        success claim with no evidence behind it."""
        total = 6 * 1024 * 1024
        graph = client(
            Response({"uploadUrl": "https://up/1"}),
            Response({"nextExpectedRanges": ["5242880-"]}, status=202),
            Response({"nextExpectedRanges": []}, status=202),   # never a 200/201
            Response({}),                                        # the DELETE
        )
        result = GraphFiles(graph).put(path="b.pdf", content=b"x" * total)
        assert result.status == "UNVERIFIED", result.detail
        assert "cannot confirm" in result.detail
        assert graph.opener.requests[-1].get_method() == "DELETE"

    def test_an_unconfigured_client_never_starts_a_session(self):
        from m365.adapters.graph import GraphFiles as GF

        graph = client()
        graph.token_provider = type("Dead", (), {
            "status": staticmethod(lambda: "UNCONFIGURED"),
            "access_token": staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no"))),
            "account": staticmethod(lambda: ""),
        })()
        result = GF(graph).put(path="b.pdf", content=self._content(6))
        assert not result.real
        assert graph.opener.requests == []

