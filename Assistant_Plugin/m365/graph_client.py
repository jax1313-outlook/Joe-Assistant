"""One HTTP client for Microsoft Graph, with the four things that always bite.

Every Graph adapter in this package goes through here, so retry, throttling,
paging and delta are implemented once and correctly rather than six times and
approximately.

**Throttling is honoured, not guessed at.** Graph answers 429 with a
`Retry-After` header saying exactly how long to wait. Ignoring it and backing off
on a schedule of your own is how a client gets throttled harder; the header is
authoritative and this client waits for what it is told.

**Retry distinguishes "not yet" from "no".** 429 and 5xx are transient. 401 means
the token is stale -- refreshed once, then retried once, because a second 401
after a fresh token is a permissions problem no amount of retrying fixes. Every
other 4xx is an answer, and retrying an answer for four hours produces a long
log and no change.

**Paging is not optional.** Graph returns `@odata.nextLink` and a caller that
ignores it silently processes the first page and believes it has everything. A
calendar read that quietly stops at 10 events is worse than one that fails.

**Delta is how you ask "what changed".** `@odata.deltaLink` comes back at the end
of a full read; presenting it on the next call returns only changes. The token is
returned to the caller to store -- this client keeps no state, because a cached
delta token that outlives its collection produces a silent resync nobody asked
for.

Nothing here has been run against Microsoft. `opener` is injected, the tests
drive recorded response shapes through it, and what is proven is the request
shape, the paging walk, the retry rules and the error mapping -- not
connectivity. `docs/M365_ACTIVATION.md` states what an operator must supply
before the first real call.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

#: 429 and 5xx are "not yet". Everything else in 4xx is an answer.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_TIMEOUT = 30

#: Guard against a paging loop. A malformed nextLink that points at itself would
#: otherwise walk until the process is killed.
MAX_PAGES = 50


class GraphError(RuntimeError):
    def __init__(self, message: str, *, status: int = 0, code: str = "", retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.code = code
        self.retryable = retryable


class GraphUnauthorized(GraphError):
    pass


@dataclass
class GraphClient:
    token_provider: object
    opener: object = field(default=urllib.request.urlopen)
    sleeper: object = field(default=time.sleep)
    timeout: int = DEFAULT_TIMEOUT
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    #: Every call made, for the activation report. Not the payloads -- a record
    #: of requests that copies their contents is a second place the data lives.
    calls: list = field(default_factory=list)

    # ------------------------------------------------------------------ status

    def status(self) -> str:
        provider_status = self.token_provider.status()
        return provider_status if provider_status in ("UNCONFIGURED", "LIVE") else "CONFIGURED"

    def account(self) -> str:
        return self.token_provider.account()

    # ------------------------------------------------------------------- verbs

    def get(self, path: str, **params) -> dict:
        return self._request("GET", self._url(path, params))

    def post(self, path: str, payload: dict) -> dict:
        return self._request("POST", self._url(path, {}), payload=payload)

    def put_bytes(self, path: str, content: bytes, content_type: str) -> dict:
        return self._request(
            "PUT", self._url(path, {}), raw=content, content_type=content_type,
        )

    def get_bytes(self, path: str) -> bytes:
        return self._request("GET", self._url(path, {}), want_bytes=True)

    # ------------------------------------------------------------------ paging

    def get_all(self, path: str, *, limit: int = 1000, **params) -> list:
        """Every page, or as many as `limit` allows.

        A caller that stops at the first page believes it has everything, and
        nothing about the result says otherwise.
        """
        items: list = []
        page = self.get(path, **params)
        pages = 0
        while True:
            items.extend(page.get("value", []))
            next_link = page.get("@odata.nextLink")
            pages += 1
            if not next_link or len(items) >= limit or pages >= MAX_PAGES:
                break
            page = self._request("GET", next_link)
        return items[:limit]

    def delta(self, path: str, *, token: str = "", limit: int = 1000) -> dict:
        """What changed since `token`, or everything plus a token to store.

        The token is handed back, never kept here. A delta token cached inside a
        client outlives the collection it describes and produces a silent
        resync -- or worse, a quiet gap.
        """
        url = token or self._url(path, {})
        items: list = []
        pages = 0
        delta_link = ""
        while True:
            page = self._request("GET", url)
            items.extend(page.get("value", []))
            pages += 1
            delta_link = page.get("@odata.deltaLink", delta_link)
            next_link = page.get("@odata.nextLink")
            if not next_link or len(items) >= limit or pages >= MAX_PAGES:
                break
            url = next_link
        return {"items": items[:limit], "delta_token": delta_link, "pages": pages}

    # ----------------------------------------------------------------- request

    def _url(self, path: str, params: dict) -> str:
        if path.startswith("http"):
            return path
        import urllib.parse

        url = f"{GRAPH_ROOT}/{path.lstrip('/')}"
        clean = {k: v for k, v in params.items() if v not in (None, "")}
        return f"{url}?{urllib.parse.urlencode(clean)}" if clean else url

    def _request(self, method: str, url: str, *, payload: dict | None = None,
                 raw: bytes | None = None, content_type: str = "",
                 want_bytes: bool = False, _refreshed: bool = False):
        try:
            token = self.token_provider.access_token()
        except Exception as exc:  # noqa: BLE001 - auth failures are reported, not raised through
            raise GraphUnauthorized(str(exc), status=401, retryable=False) from exc

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif raw is not None:
            headers["Content-Type"] = content_type or "application/octet-stream"

        attempt = 0
        while True:
            attempt += 1
            request = urllib.request.Request(url, data=body, headers=headers, method=method)
            self.calls.append({"method": method, "url": url.split("?")[0], "attempt": attempt})
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    content = response.read()
                    if want_bytes:
                        return content
                    if not content:
                        return {}
                    return json.loads(content.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                detail, code = _read_error(exc)

                if status == 401 and not _refreshed:
                    # One refresh, one retry. A second 401 after a fresh token is
                    # a permissions problem, and retrying it changes nothing.
                    return self._request(
                        method, url, payload=payload, raw=raw, content_type=content_type,
                        want_bytes=want_bytes, _refreshed=True,
                    )
                if status in RETRYABLE_STATUS and attempt < self.max_attempts:
                    self.sleeper(_wait_for(exc, attempt))
                    continue
                raise GraphError(
                    f"{status} {code or exc.reason}: {detail}".strip(),
                    status=status, code=code, retryable=status in RETRYABLE_STATUS,
                ) from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_attempts:
                    self.sleeper(min(2 ** attempt, 30))
                    continue
                raise GraphError(f"could not reach Microsoft Graph: {exc.reason}",
                                 retryable=True) from exc


def _read_error(exc) -> tuple[str, str]:
    """Graph's JSON error body says far more than the HTTP status."""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return "", ""
    error = payload.get("error", {})
    return error.get("message", ""), error.get("code", "")


def _wait_for(exc, attempt: int) -> float:
    """Retry-After when Graph gives one; exponential backoff when it does not.

    The header is authoritative. Backing off on a schedule of your own while
    Microsoft is telling you the number is how a client gets throttled harder.
    """
    header = ""
    try:
        header = exc.headers.get("Retry-After", "") or ""
    except Exception:  # noqa: BLE001
        header = ""
    if header.strip().isdigit():
        return float(header.strip())
    return float(min(2 ** attempt, 30))
