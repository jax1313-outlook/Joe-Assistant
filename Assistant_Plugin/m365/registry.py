"""Which provider is behind each port on this machine, and what it will do.

One question this answers, and it is the one an operator always asks: *is it
actually connected?* The survey says so per port, in the eight words, before
anything is called -- so nobody finds out by sending a test email to a broker.

Selection is simple and stated: Microsoft where a token is available, the local
substitute otherwise, and `ABSENT` where there is no honest substitute at all. A
folder on this laptop is not a SharePoint site and writing a file is not telling
anybody in Teams, so those two report ABSENT rather than pretending.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from m365.adapters import graph as graph_adapters
from m365.adapters import local as local_adapters
from m365.graph_client import GraphClient

PORTS = ("calendar", "mail", "files", "site", "chat", "documents")


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def token_provider():
    """Delegated device-code auth where Dispatch supplies it; a refusal otherwise.

    Joe is a plug-in and must not require Dispatch to be installed. Where it is,
    the same connected account serves both -- one sign-in, not two.
    """
    try:
        from dispatch.msauth import provider_from_environment  # type: ignore

        return provider_from_environment(_token_cache())
    except ImportError:
        return _StandaloneRefusal()


def _token_cache():
    explicit = _env("JOE_MS_TOKEN_CACHE") or _env("DISPATCH_MS_TOKEN_CACHE")
    if explicit:
        return Path(explicit)
    root = _env("DISPATCH_MEMORY_ROOT")
    return Path(root) / "auth" / "microsoft-token.json" if root else None


class _StandaloneRefusal:
    """What a token provider looks like when there is none. Never silent."""

    def status(self) -> str:
        return "UNCONFIGURED"

    def account(self) -> str:
        return ""

    def access_token(self) -> str:
        raise RuntimeError(
            "No Microsoft sign-in is available in this build. Connect one with "
            "`python -m dispatch_launcher connect-microsoft`, or run Joe beside Dispatch."
        )


@dataclass
class M365Suite:
    calendar: object
    mail: object
    files: object
    site: object
    chat: object
    documents: object
    client: GraphClient | None = None

    def survey(self) -> list[dict]:
        rows = []
        for name in PORTS:
            port = getattr(self, name)
            rows.append({
                "port": name,
                "provider": getattr(port, "provider_id", "unknown"),
                "status": port.status(),
            })
        return rows

    def render(self) -> str:
        account = self.client.account() if self.client else ""
        head = f"  Microsoft account: {self.client.status() if self.client else 'UNCONFIGURED'}"
        lines = [head + (f" ({account})" if account else ""), ""]
        for row in self.survey():
            lines.append(f"    {row['status']:<13} {row['port']:<10} via {row['provider']}")
        lines.append("")
        lines.append("  SIMULATED means it worked locally and reached nobody.")
        return "\n".join(lines)


def build_suite(*, local_root: Path | None = None, provider=None) -> M365Suite:
    """The suite this machine will actually use."""
    provider = provider or token_provider()
    client = GraphClient(token_provider=provider)
    connected = client.status() != "UNCONFIGURED"

    root = Path(local_root) if local_root else Path(_env("JOE_LOCAL_M365_ROOT") or "LocalM365")

    if connected:
        files = graph_adapters.GraphFiles(client)
        return M365Suite(
            calendar=graph_adapters.GraphCalendar(client),
            mail=graph_adapters.GraphMail(client),
            files=files,
            site=graph_adapters.GraphSite(client, site_id=_env("JOE_SHAREPOINT_SITE_ID")),
            chat=graph_adapters.GraphChat(client, team_id=_env("JOE_TEAMS_TEAM_ID")),
            documents=graph_adapters.GraphDocuments(client, files=files),
            client=client,
        )

    calendar_file = _env("JOE_LOCAL_CALENDAR")
    return M365Suite(
        calendar=local_adapters.LocalCalendar(Path(calendar_file) if calendar_file else None),
        mail=local_adapters.LocalMail(root / "Outbox"),
        files=local_adapters.LocalFiles(root / "Drive"),
        # No honest substitute exists for either of these, and inventing one
        # would be the exact claim the truth vocabulary exists to prevent.
        site=local_adapters.UnavailableSite(),
        chat=local_adapters.UnavailableChat(),
        documents=local_adapters.LocalDocuments(),
        client=client,
    )
