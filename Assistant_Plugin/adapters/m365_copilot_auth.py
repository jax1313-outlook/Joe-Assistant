"""Microsoft 365 sign-in for the Copilot provider.

Uses **MSAL**, Microsoft's supported authentication library, as a public
desktop client. No client secret is used, because a public client has no
secure place to keep one.

TOKEN HANDLING - the rules this module exists to enforce:

  * Tokens are acquired, held, and refreshed by MSAL. This module never
    parses, stores, prints, logs, or returns a token to a caller. The only
    thing that leaves here is an Authorization header handed straight to the
    HTTP call, and a boolean saying whether sign-in succeeded.
  * The token cache is persisted through msal-extensions using **Windows
    DPAPI**, so the cache file is encrypted at rest and readable only by the
    signed-in Windows user. It is never plain text.
  * If DPAPI is unavailable, the cache is held **in memory only** and the
    caller is told sign-in will not persist. A readable token file is never
    written as a fallback.
  * `sign_out()` removes the accounts from MSAL and deletes the cache file.

WHAT NEEDS A HUMAN: Entra app registration, tenant id, client id, delegated
permission review, admin consent, and the interactive sign-in itself. None of
those are done here, and none are done on Mike's behalf.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

AUTHORITY_BASE = "https://login.microsoftonline.com/"
GRAPH_SCOPES = (
    "Sites.Read.All",
    "Mail.Read",
    "People.Read.All",
    "OnlineMeetingTranscript.Read.All",
    "Chat.Read",
    "ChannelMessage.Read.All",
    "ExternalItem.Read.All",
)
SCOPE_URIS = tuple("https://graph.microsoft.com/" + s for s in GRAPH_SCOPES)

CACHE_FILENAME = "copilot_token_cache.bin"

# Environment variables. Neither is a secret: a public-client id and a tenant
# id are both safe to hold in configuration. No secret is ever read.
ENV_TENANT = "ASSISTANT_COPILOT_TENANT_ID"
ENV_CLIENT = "ASSISTANT_COPILOT_CLIENT_ID"


class AuthState:
    NOT_CONFIGURED = "NOT CONFIGURED"     # no tenant / client id
    LIBRARY_MISSING = "LIBRARY MISSING"   # msal not installed
    SIGNED_OUT = "SIGNED OUT"             # configured, nobody signed in
    SIGNED_IN = "SIGNED IN"               # a cached account can get a token
    ERROR = "ERROR"

    ALL = (NOT_CONFIGURED, LIBRARY_MISSING, SIGNED_OUT, SIGNED_IN, ERROR)


class AuthError(RuntimeError):
    pass


def msal_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("msal") is not None


@dataclass
class DeviceFlow:
    """What a human must do to complete sign-in. Contains no secret material.

    `user_code` is a short one-time code the person types at the verification
    URL. It is not a credential, is useless without the interactive sign-in,
    and expires in minutes.
    """

    verification_uri: str
    user_code: str
    expires_in: int
    message: str
    handle: dict = field(default=None, repr=False)  # opaque MSAL state


class CopilotAuth:
    """MSAL public-client sign-in for Microsoft Graph."""

    def __init__(
        self,
        tenant_id: str = "",
        client_id: str = "",
        cache_dir: str | Path | None = None,
    ) -> None:
        self.tenant_id = (tenant_id or os.environ.get(ENV_TENANT, "")).strip()
        self.client_id = (client_id or os.environ.get(ENV_CLIENT, "")).strip()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.last_error = ""
        self.cache_is_encrypted = False
        self.cache_persisted = False
        self._app = None
        self._cache = None

    # ---- configuration ------------------------------------------------

    @property
    def configured(self) -> bool:
        return bool(self.tenant_id) and bool(self.client_id)

    @property
    def authority(self) -> str:
        return AUTHORITY_BASE + (self.tenant_id or "organizations")

    @property
    def cache_path(self) -> Path | None:
        return (self.cache_dir / CACHE_FILENAME) if self.cache_dir else None

    # ---- cache --------------------------------------------------------

    def _build_cache(self):
        """A DPAPI-encrypted cache, or an in-memory one. Never plain text."""
        if self._cache is not None:
            return self._cache

        import msal

        path = self.cache_path
        if path is not None:
            try:
                from msal_extensions import (
                    FilePersistenceWithDataProtection,
                    PersistedTokenCache,
                )

                path.parent.mkdir(parents=True, exist_ok=True)
                persistence = FilePersistenceWithDataProtection(str(path))
                self._cache = PersistedTokenCache(persistence)
                self.cache_is_encrypted = True
                self.cache_persisted = True
                return self._cache
            except Exception as error:  # noqa: BLE001
                # No readable-token fallback. Memory only, and say so.
                self.last_error = (
                    "encrypted token cache unavailable (" + type(error).__name__
                    + "); sign-in will not persist between sessions"
                )

        self._cache = msal.SerializableTokenCache()
        self.cache_is_encrypted = False
        self.cache_persisted = False
        return self._cache

    def _application(self):
        if self._app is not None:
            return self._app
        if not msal_available():
            raise AuthError(
                "msal is not installed. Install it with:  py -m pip install --user msal msal-extensions"
            )
        if not self.configured:
            raise AuthError(
                "no tenant id and client id are configured for Microsoft 365 sign-in"
            )
        import msal

        # Public client: no client secret, by design.
        self._app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self._build_cache(),
        )
        return self._app

    # ---- accounts -----------------------------------------------------

    def accounts(self) -> list[dict]:
        """Signed-in accounts. Usernames only - never a token."""
        try:
            app = self._application()
        except AuthError:
            return []
        return [
            {"username": a.get("username", ""), "home_account_id": a.get("home_account_id", "")}
            for a in app.get_accounts()
        ]

    @property
    def signed_in(self) -> bool:
        return bool(self.accounts())

    # ---- acquiring ----------------------------------------------------

    def _acquire_silent(self):
        """A token from the cache, or None. The token never leaves this class."""
        try:
            app = self._application()
        except AuthError as error:
            self.last_error = str(error)
            return None
        accounts = app.get_accounts()
        if not accounts:
            return None
        result = app.acquire_token_silent(list(SCOPE_URIS), account=accounts[0])
        if result and "access_token" in result:
            return result
        if result and result.get("error"):
            self.last_error = self._safe(result)
        return None

    def authorization_header(self) -> str | None:
        """`Bearer <token>` for one request, or None.

        This is the only path by which a token leaves this module, and it goes
        straight into an HTTP header. It is never logged or returned upward.
        """
        result = self._acquire_silent()
        if not result:
            return None
        return "Bearer " + result["access_token"]

    # ---- interactive sign-in (needs a human) --------------------------

    def begin_device_flow(self) -> DeviceFlow:
        """Start device-code sign-in. A person must finish it."""
        app = self._application()
        flow = app.initiate_device_flow(scopes=list(SCOPE_URIS))
        if "user_code" not in flow:
            raise AuthError(
                "could not start Microsoft sign-in: " + self._safe(flow)
            )
        return DeviceFlow(
            verification_uri=str(flow.get("verification_uri", "")),
            user_code=str(flow.get("user_code", "")),
            expires_in=int(flow.get("expires_in", 900)),
            message=str(flow.get("message", "")),
            handle=flow,
        )

    def complete_device_flow(self, flow: DeviceFlow) -> tuple[bool, str]:
        """Block until the person signs in, or it times out.

        Returns (signed_in, message). No token is returned.
        """
        app = self._application()
        result = app.acquire_token_by_device_flow(flow.handle)
        if result and "access_token" in result:
            accounts = app.get_accounts()
            who = accounts[0].get("username", "") if accounts else ""
            return True, "Signed in as " + who if who else "Signed in."
        self.last_error = self._safe(result)
        return False, self.last_error

    # ---- sign out -----------------------------------------------------

    def sign_out(self) -> str:
        """Remove every account and delete the token cache file."""
        removed = 0
        try:
            app = self._application()
            for account in app.get_accounts():
                app.remove_account(account)
                removed += 1
        except AuthError:
            pass

        deleted = False
        path = self.cache_path
        if path is not None and path.exists():
            try:
                path.unlink()
                deleted = True
            except OSError as error:
                self.last_error = "could not delete the token cache: " + str(error)

        self._app = None
        self._cache = None
        return (
            "Signed out. "
            + str(removed) + " account(s) removed"
            + (", token cache deleted." if deleted else ", no cache file to delete.")
        )

    # ---- reporting ----------------------------------------------------

    @staticmethod
    def _safe(result) -> str:
        """An error string with nothing sensitive in it.

        MSAL error payloads can carry codes and correlation ids. Only the
        error name and description are used, and never any token field.
        """
        if not isinstance(result, dict):
            return "sign-in failed"
        name = str(result.get("error", "error"))
        description = str(result.get("error_description", ""))
        description = description.split("\r")[0].split("\n")[0][:200]
        return (name + ": " + description).strip(": ")

    def state(self) -> str:
        if not msal_available():
            return AuthState.LIBRARY_MISSING
        if not self.configured:
            return AuthState.NOT_CONFIGURED
        try:
            self._application()
        except AuthError:
            return AuthState.ERROR
        return AuthState.SIGNED_IN if self.signed_in else AuthState.SIGNED_OUT

    def status(self) -> dict:
        """Everything the UI needs, and no credential material at all."""
        state = self.state()
        accounts = self.accounts() if state == AuthState.SIGNED_IN else []
        blocker = ""
        if state == AuthState.LIBRARY_MISSING:
            blocker = (
                "msal is not installed. Run:  "
                "py -m pip install --user msal msal-extensions"
            )
        elif state == AuthState.NOT_CONFIGURED:
            blocker = (
                "no tenant id and client id are configured. These come from an "
                "Entra app registration, which only Mike can create."
            )
        elif state == AuthState.SIGNED_OUT:
            blocker = "configured, but nobody has signed in yet"
        elif state == AuthState.ERROR:
            blocker = self.last_error or "sign-in could not be prepared"

        return {
            "state": state,
            "signed_in": state == AuthState.SIGNED_IN,
            "configured": self.configured,
            "msal_available": msal_available(),
            "tenant_id_set": bool(self.tenant_id),
            "client_id_set": bool(self.client_id),
            "account": accounts[0]["username"] if accounts else "",
            "cache_encrypted": self.cache_is_encrypted,
            "cache_persisted": self.cache_persisted,
            "cache_location": str(self.cache_path) if self.cache_path else "(memory only)",
            "scopes": list(GRAPH_SCOPES),
            "client_secret_used": False,
            "blocker": blocker,
            "last_error": self.last_error,
        }
