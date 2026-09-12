"""Microsoft behind the ports. Six adapters, one client, no new vocabulary.

Each adapter is thin on purpose: it builds a Graph request, hands it to
`GraphClient`, and translates the answer into the port's `Result`. Retry,
throttling, paging and delta all live in the client, so none of them is
implemented six times and approximately.

Nothing here has been executed against Microsoft. The tests drive recorded
response shapes through an injected opener and prove the request shape, the
translation and the refusals. `docs/M365_ACTIVATION.md` states exactly what an
operator supplies before the first real call.
"""

from __future__ import annotations

from dataclasses import dataclass

from m365.graph_client import GraphClient, GraphError, GraphUnauthorized
from m365.ports import (
    CalendarEvent,
    PortError,
    PortRefused,
    PortUnconfigured,
    Result,
    StoredFile,
)

PROVIDER = "microsoft_graph"


def _guard(client: GraphClient) -> Result | None:
    if client.status() == "UNCONFIGURED":
        return Result(
            "UNCONFIGURED",
            "No Microsoft account is connected on this machine. "
            "See docs/M365_ACTIVATION.md.",
            PROVIDER,
        )
    return None


def _translate(exc: Exception) -> Result:
    if isinstance(exc, GraphUnauthorized):
        return Result("UNCONFIGURED", f"Microsoft refused the token: {exc}", PROVIDER)
    if isinstance(exc, GraphError):
        # A 403 is an answer -- the account does not have that permission -- and
        # it needs a different action from the operator than a 503 does.
        word = "UNAVAILABLE" if exc.retryable else "ABSENT"
        return Result(word, str(exc), PROVIDER, {"status": exc.status, "code": exc.code})
    return Result("UNAVAILABLE", f"{type(exc).__name__}: {exc}", PROVIDER)


# ------------------------------------------------------------------- calendar


@dataclass
class GraphCalendar:
    """Reads the schedule. Proposes an event; never writes one unasked.

    CLAUDE.md 5.5: Outlook is the scheduling authority and "Dispatch must not
    create a separate competing scheduling system". So there is no `sync`, no
    local calendar table, and `propose_event` returns something a person accepts
    -- because creating a calendar entry is an external side effect of a human's
    approval, not a state Dispatch passes through.
    """

    client: GraphClient
    provider_id: str = PROVIDER

    def status(self) -> str:
        return self.client.status()

    def read_events(self, *, start: str, end: str, limit: int = 100) -> Result:
        blocked = _guard(self.client)
        if blocked:
            return blocked
        try:
            rows = self.client.get_all(
                "me/calendarView", limit=limit,
                startDateTime=start, endDateTime=end,
                **{"$orderby": "start/dateTime", "$top": min(limit, 100)},
            )
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)

        events = [
            CalendarEvent(
                event_id=row.get("id", ""),
                subject=row.get("subject", ""),
                starts_at=(row.get("start") or {}).get("dateTime", ""),
                ends_at=(row.get("end") or {}).get("dateTime", ""),
                location=((row.get("location") or {}).get("displayName", "")),
                organizer=(((row.get("organizer") or {}).get("emailAddress") or {})
                           .get("address", "")),
                is_all_day=bool(row.get("isAllDay")),
                source="Outlook",
            ).to_dict()
            for row in rows
        ]
        return Result("LIVE", f"{len(events)} event(s) read from Outlook.", PROVIDER,
                      {"events": events})

    def changed_since(self, token: str = "", *, limit: int = 500) -> Result:
        """What moved. The token is returned for the caller to keep, not cached."""
        blocked = _guard(self.client)
        if blocked:
            return blocked
        try:
            outcome = self.client.delta("me/calendarView/delta", token=token, limit=limit)
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result(
            "LIVE",
            f"{len(outcome['items'])} change(s) over {outcome['pages']} page(s).",
            PROVIDER,
            {"items": outcome["items"], "delta_token": outcome["delta_token"]},
        )

    def propose_event(self, *, subject: str, starts_at: str, ends_at: str,
                      location: str = "", authorized_by: str = "",
                      authorization_ref: str = "") -> Result:
        if not authorized_by or not authorization_ref:
            return Result(
                "MANUAL",
                "Dispatch does not put entries in Outlook by itself. This is the event "
                "to create; a person creates it, or authorises it with a recorded "
                "decision (authorized_by + authorization_ref).",
                PROVIDER,
                {"proposed": {"subject": subject, "starts_at": starts_at,
                              "ends_at": ends_at, "location": location}},
            )
        blocked = _guard(self.client)
        if blocked:
            return blocked
        payload = {
            "subject": subject,
            "start": {"dateTime": starts_at, "timeZone": "UTC"},
            "end": {"dateTime": ends_at, "timeZone": "UTC"},
        }
        if location:
            payload["location"] = {"displayName": location}
        try:
            created = self.client.post("me/events", payload)
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"Created in Outlook under {authorization_ref}.", PROVIDER,
                      {"event_id": created.get("id", "")})


# ----------------------------------------------------------------------- mail


@dataclass
class GraphMail:
    client: GraphClient
    provider_id: str = PROVIDER

    def status(self) -> str:
        return self.client.status()

    def send(self, *, to: tuple, subject: str, body_text: str,
             body_html: str = "", cc: tuple = ()) -> Result:
        blocked = _guard(self.client)
        if blocked:
            return blocked
        if not to:
            return Result("ABSENT", "No recipient.", PROVIDER)

        def recipients(addresses):
            return [{"emailAddress": {"address": a}} for a in addresses]

        payload = {
            "message": {
                "subject": subject,
                "body": ({"contentType": "HTML", "content": body_html} if body_html
                         else {"contentType": "Text", "content": body_text}),
                "toRecipients": recipients(to),
            },
            # The operator's Sent Items, so a broker's reply lands in a thread
            # that exists in Outlook rather than appearing from nowhere.
            "saveToSentItems": True,
        }
        if cc:
            payload["message"]["ccRecipients"] = recipients(cc)
        try:
            self.client.post("me/sendMail", payload)
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        account = self.client.account()
        return Result("LIVE", f"Sent via Microsoft Graph{f' as {account}' if account else ''}.",
                      PROVIDER)


# ------------------------------------------------------------------- onedrive


@dataclass
class GraphFiles:
    """OneDrive as durable storage for evidence. Never as the system of record.

    CLAUDE.md 5.4: operational truth lives in Dispatch and "a plug-in's copy is a
    copy". So a file put here is a second copy of something Dispatch already has
    a checksum for; losing it costs a re-upload, not a record.
    """

    client: GraphClient
    root: str = "Dispatch"
    provider_id: str = PROVIDER

    def status(self) -> str:
        return self.client.status()

    def _item_path(self, path: str) -> str:
        clean = "/".join(p for p in f"{self.root}/{path}".split("/") if p)
        return f"me/drive/root:/{clean}"

    def put(self, *, path: str, content: bytes, content_type: str = "") -> Result:
        blocked = _guard(self.client)
        if blocked:
            return blocked
        if len(content) > 4 * 1024 * 1024:
            # Graph's simple upload stops at 4 MB; beyond that it is an upload
            # session, which is a different flow and is not written.
            return Result(
                "ABSENT",
                f"{len(content):,} bytes exceeds the 4 MB simple-upload limit. "
                "A resumable upload session is not implemented.",
                PROVIDER,
            )
        try:
            item = self.client.put_bytes(
                f"{self._item_path(path)}:/content", content,
                content_type or "application/octet-stream",
            )
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"Stored {path} in OneDrive.", PROVIDER,
                      {"file": StoredFile(
                          file_id=item.get("id", ""), name=item.get("name", path),
                          size=int(item.get("size", len(content))),
                          web_url=item.get("webUrl", ""),
                      ).to_dict()})

    def get(self, *, path: str) -> Result:
        blocked = _guard(self.client)
        if blocked:
            return blocked
        try:
            content = self.client.get_bytes(f"{self._item_path(path)}:/content")
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"{len(content):,} bytes.", PROVIDER, {"content": content})

    def list(self, *, folder: str = "") -> Result:
        blocked = _guard(self.client)
        if blocked:
            return blocked
        target = self._item_path(folder) if folder else f"me/drive/root:/{self.root}"
        try:
            rows = self.client.get_all(f"{target}:/children", limit=200)
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"{len(rows)} item(s).", PROVIDER, {
            "files": [
                StoredFile(file_id=r.get("id", ""), name=r.get("name", ""),
                           size=int(r.get("size", 0)), web_url=r.get("webUrl", "")).to_dict()
                for r in rows
            ]
        })


# ----------------------------------------------------------------- sharepoint


@dataclass
class GraphSite:
    client: GraphClient
    site_id: str = ""
    provider_id: str = PROVIDER

    def status(self) -> str:
        if not self.site_id:
            return "UNCONFIGURED"
        return self.client.status()

    def list_documents(self, *, library: str = "Documents", limit: int = 50) -> Result:
        if not self.site_id:
            return Result("UNCONFIGURED",
                          "No SharePoint site is configured (JOE_SHAREPOINT_SITE_ID).",
                          PROVIDER)
        blocked = _guard(self.client)
        if blocked:
            return blocked
        try:
            rows = self.client.get_all(
                f"sites/{self.site_id}/drive/root/children", limit=limit)
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"{len(rows)} document(s) in {library}.", PROVIDER,
                      {"documents": [{"id": r.get("id", ""), "name": r.get("name", ""),
                                      "web_url": r.get("webUrl", "")} for r in rows]})

    def read_document(self, *, item_id: str) -> Result:
        if not self.site_id:
            return Result("UNCONFIGURED", "No SharePoint site is configured.", PROVIDER)
        try:
            content = self.client.get_bytes(
                f"sites/{self.site_id}/drive/items/{item_id}/content")
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"{len(content):,} bytes.", PROVIDER, {"content": content})


# ---------------------------------------------------------------------- teams


@dataclass
class GraphChat:
    """Posts a notice a person wrote. Does not hold a conversation.

    Deliberately one method. A bot that answers in a Teams channel is a second
    interface to Dispatch with its own authority story, and there is no doctrine
    for one. Posting a notice somebody already approved has a clear one.
    """

    client: GraphClient
    team_id: str = ""
    provider_id: str = PROVIDER

    def status(self) -> str:
        if not self.team_id:
            return "UNCONFIGURED"
        return self.client.status()

    def post_notice(self, *, channel: str, text: str, authorized_by: str = "") -> Result:
        if not self.team_id:
            return Result("UNCONFIGURED", "No Teams team is configured (JOE_TEAMS_TEAM_ID).",
                          PROVIDER)
        if not authorized_by:
            return Result("MANUAL",
                          "A notice is posted by a person, not by Dispatch. "
                          "Pass authorized_by once somebody has approved this text.",
                          PROVIDER, {"proposed": {"channel": channel, "text": text}})
        blocked = _guard(self.client)
        if blocked:
            return blocked
        try:
            self.client.post(
                f"teams/{self.team_id}/channels/{channel}/messages",
                {"body": {"contentType": "text", "content": text}},
            )
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"Posted to {channel}.", PROVIDER)


# ------------------------------------------------------------------ documents


@dataclass
class GraphDocuments:
    """Word production, by asking Graph to convert rather than writing OOXML.

    Graph will return any drive item as PDF via `?format=pdf`. For .docx the
    honest position is that there is no conversion endpoint: the document has to
    be written as OOXML and uploaded, and writing an OOXML serialiser is a
    dependency and a body of work this package does not have. So a `.docx`
    request is refused by name rather than quietly producing something else.
    """

    client: GraphClient
    files: GraphFiles | None = None
    provider_id: str = PROVIDER

    def status(self) -> str:
        return self.client.status()

    def render(self, *, title: str, sections: tuple, fmt: str = "docx") -> Result:
        if fmt not in ("pdf", "txt", "html"):
            return Result(
                "ABSENT",
                f"{fmt!r} is not produced here. Graph converts an uploaded document to "
                "PDF; it does not author one. Writing OOXML is a dependency this "
                "package does not take.",
                PROVIDER,
            )
        body = _render_body(title, sections, fmt)
        if fmt in ("txt", "html"):
            return Result("SIMULATED",
                          f"{len(body):,} bytes rendered locally; nothing was sent to "
                          "Microsoft.", PROVIDER, {"content": body, "format": fmt})

        if self.files is None:
            return Result("UNCONFIGURED", "PDF conversion needs a OneDrive adapter to "
                          "upload through.", PROVIDER)
        blocked = _guard(self.client)
        if blocked:
            return blocked
        staged = f"_conversion/{title.replace('/', '-')}.html"
        upload = self.files.put(path=staged, content=body, content_type="text/html")
        if not upload.real:
            return upload
        try:
            pdf = self.client.get_bytes(
                f"me/drive/root:/{self.files.root}/{staged}:/content?format=pdf")
        except Exception as exc:  # noqa: BLE001
            return _translate(exc)
        return Result("LIVE", f"{len(pdf):,} bytes of PDF.", PROVIDER,
                      {"content": pdf, "format": "pdf"})


def _render_body(title: str, sections: tuple, fmt: str) -> bytes:
    if fmt == "txt":
        lines = [title, "=" * len(title), ""]
        for heading, text in sections:
            lines += [heading, "-" * len(heading), text, ""]
        return "\n".join(lines).encode("utf-8")
    import html as _html

    parts = [f"<h1>{_html.escape(title)}</h1>"]
    for heading, text in sections:
        parts.append(f"<h2>{_html.escape(heading)}</h2><p>{_html.escape(text)}</p>")
    return ("<html><body>" + "".join(parts) + "</body></html>").encode("utf-8")
