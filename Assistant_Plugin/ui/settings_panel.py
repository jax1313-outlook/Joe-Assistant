"""Settings - Microsoft 365 Copilot connection panel.

Shows the connection state, lets Mike sign in, and lets him disconnect and
clear the stored authentication.

NOTHING SENSITIVE IS SHOWN HERE. Tenant id and client id are not secrets - a
public-client id is safe to display. No token, no secret, and no password is
ever rendered, stored by this panel, or written anywhere by it.

The panel does not create the Entra app registration, does not grant consent,
and does not sign in on Mike's behalf. Sign-in opens Microsoft's own device
page and waits for him to complete it there.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

BG = "#0f1216"
PANEL = "#181d24"
PANEL2 = "#1f252e"
INK = "#e9ecf1"
MUTED = "#98a3b3"
ACCENT = "#4c8dff"
GOOD = "#3fb950"
WARN = "#d29922"
BAD = "#f85149"

MONO = ("Consolas", 10)


class SettingsPanel:
    """A separate window for the Copilot connection."""

    def __init__(self, parent, service) -> None:
        self.service = service
        self.flow = None
        self.window = tk.Toplevel(parent)
        self.window.title("JOE Settings  -  Microsoft 365 Copilot")
        self.window.geometry("820x680")
        self.window.configure(bg=BG)
        self._build()
        self.refresh()

    # ---- layout -------------------------------------------------------

    def _build(self) -> None:
        header = tk.Frame(self.window, bg=PANEL)
        header.pack(fill="x")
        tk.Label(
            header, text="Microsoft 365 Copilot connection", bg=PANEL, fg=INK,
            font=("Segoe UI Semibold", 14), anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(
            header,
            text=(
                "PILOT / PREVIEW  -  Microsoft states that /beta APIs are not "
                "supported for production use."
            ),
            bg=PANEL, fg=WARN, font=("Segoe UI", 9), anchor="w",
            wraplength=780, justify="left",
        ).pack(fill="x", padx=16, pady=(0, 12))

        body = tk.Frame(self.window, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self.status_text = tk.Text(
            body, bg=PANEL, fg=INK, font=MONO, wrap="word", height=22,
            borderwidth=0, highlightthickness=0, padx=12, pady=10,
        )
        self.status_text.pack(fill="both", expand=True)
        for tag, colour in (
            ("head", ACCENT), ("good", GOOD), ("warn", WARN),
            ("bad", BAD), ("muted", MUTED),
        ):
            self.status_text.tag_configure(tag, foreground=colour)
        self.status_text.configure(state="disabled")

        buttons = tk.Frame(self.window, bg=BG)
        buttons.pack(fill="x", padx=16, pady=(0, 8))
        for label, handler, colour in (
            ("Sign in to Microsoft 365", self._on_sign_in, ACCENT),
            ("Disconnect and clear authentication", self._on_sign_out, PANEL2),
            ("Refresh", lambda: self.refresh(), PANEL2),
            ("Close", self.window.destroy, PANEL2),
        ):
            tk.Button(
                buttons, text=label, command=handler,
                bg=colour, fg="#ffffff" if colour == ACCENT else INK,
                font=("Segoe UI", 10), relief="flat", padx=14, pady=7,
                cursor="hand2",
            ).pack(side="left", padx=(0, 8))

        self.line = tk.Label(
            self.window, text="", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9), anchor="w", wraplength=790, justify="left",
        )
        self.line.pack(fill="x", side="bottom", ipady=8, ipadx=16)

    # ---- rendering ----------------------------------------------------

    def _write(self, chunks) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        for text, tag in chunks:
            self.status_text.insert(tk.END, text, tag)
        self.status_text.configure(state="disabled")

    def refresh(self) -> None:
        status = self.service.copilot_status()
        chunks = []

        if not status.get("provider_selected"):
            chunks += [
                ("Microsoft 365 Copilot is not the selected provider.\n\n", "warn"),
                (status.get("blocker", "") + "\n\n", None),
                ("To select it\n", "head"),
                ('  Set  "provider": "m365_copilot"  under  "reasoning"  in\n'
                 "  configuration\\joe.config.json, then restart JOE.\n\n",
                 "muted"),
            ]
            self._write(chunks)
            self.line.config(text="Copilot is not selected.")
            return

        state = status.get("state", "")
        signed_in = bool(status.get("signed_in"))
        tag = "good" if signed_in else "warn"

        chunks += [
            ("Connection\n", "head"),
            ("  state                 " + state + "\n", tag),
            ("  reasoning status      " + str(status.get("status", "")) + "\n", tag),
            ("  account               "
             + (status.get("account") or "(nobody signed in)") + "\n\n", None),

            ("Configuration  (neither value is a secret)\n", "head"),
            ("  msal installed        " + str(status.get("msal_available")) + "\n", None),
            ("  tenant id set         " + str(status.get("tenant_id_set")) + "\n", None),
            ("  client id set         " + str(status.get("client_id_set")) + "\n", None),
            ("  client secret used    " + str(status.get("client_secret_used", False))
             + "   (a public desktop client never uses one)\n\n", "muted"),

            ("Token storage\n", "head"),
            ("  encrypted at rest     " + str(status.get("cache_encrypted")) + "\n",
             "good" if status.get("cache_encrypted") else "warn"),
            ("  persists between runs " + str(status.get("cache_persisted")) + "\n", None),
            ("  location              " + str(status.get("cache_location", "")) + "\n", "muted"),
            ("  Tokens are held by MSAL and encrypted with Windows DPAPI.\n"
             "  No token is ever written in plain text, logged, or displayed.\n\n", "muted"),

            ("Delegated permissions requested\n", "head"),
        ]
        for scope in status.get("scopes", []):
            chunks.append(("  " + scope + "\n", "muted"))
        chunks.append(
            ("  All seven are required by Microsoft for the Chat API.\n"
             "  Several need administrator consent.\n\n", "muted")
        )


        chunks += self._microphone_chunks()
        chunks += self._account_chunks()

        chunks += [
            ("What this provider may not do\n", "head"),
            ("  approve   decide   send   schedule   modify Outlook   modify Dispatch\n\n",
             "muted"),
        ]

        blocker = status.get("blocker") or ""
        if blocker:
            chunks += [("What is blocking\n", "head"), ("  " + blocker + "\n\n", "warn")]

        if not signed_in:
            chunks += [
                ("What only Mike can do\n", "head"),
                ("  1. Create an Entra app registration (public client, device code)\n"
                 "  2. Put its tenant id and client id in the configuration\n"
                 "  3. Review the delegated permissions above\n"
                 "  4. Grant administrator consent\n"
                 "  5. Sign in below\n\n", None),
                ("  JOE does none of these for you and cannot consent\n"
                 "  on your behalf.\n", "muted"),
            ]
        self._write(chunks)
        self.line.config(
            text=("Signed in as " + status["account"]) if signed_in
            else "Not signed in. Text mode and every local capability still work."
        )

    def _account_chunks(self):
        """Email accounts, and which one answers which kind of question.

        Friendly names only. No connection ids, no COM terms, no store paths -
        those belong in diagnostics, not in the screen Mike reads to find out
        whether JOE can see his mail.
        """
        try:
            self.service.mailboxes.discover()
            report = self.service.mailboxes.report()
        except Exception as error:
            return [("Email accounts\n", "head"),
                    ("  could not be read: " + str(error)[:70] + "\n\n", "warn")]

        connections = report.get("connections", [])
        chunks = [("Email accounts\n", "head")]
        if not connections:
            chunks.append(("  none configured. JOE will not read any mailbox.\n\n",
                           "warn"))
            return chunks

        for row in connections:
            state = row["display"]
            tag = {"LIVE": "good", "NOT MOUNTED": "warn",
                   "UNKNOWN": "warn", "OFF": "muted"}.get(state, "muted")
            chunks.append(("  " + row["friendly_name"].ljust(18)
                           + row["address"].ljust(26) + state + "\n", tag))
            holdings = row.get("holdings") or {}
            if holdings:
                counts = []
                for capability in ("mail", "calendar", "contacts"):
                    value = holdings.get(capability)
                    if value is None:
                        continue
                    counts.append(capability + "="
                                  + ("unreadable" if value < 0 else str(value)))
                if counts:
                    chunks.append(("      holds  " + "   ".join(counts) + "\n",
                                   "muted"))
            if row.get("failure_message"):
                chunks.append(("      " + row["failure_message"] + "\n", "warn"))

        chunks.append(("\n  Which mailbox answers what\n", None))
        for capability in ("mail", "calendar", "contacts"):
            chosen = report.get("sources", {}).get(capability) or ""
            chunks.append(("    " + capability.ljust(10)
                           + (chosen or "NONE - see below") + "\n",
                           "good" if chosen else "warn"))
        for capability, note in (report.get("notes") or {}).items():
            chunks.append(("    " + capability + ": " + note + "\n", "warn"))

        chunks.append(("\n  Read-only. JOE cannot send, delete, move, flag, or\n"
                       "  change anything in any mailbox.\n\n", "muted"))
        return chunks

    def _microphone_chunks(self):
        """What JOE will hear, and from which device.

        Shown in normal Settings rather than buried in a diagnostics page,
        because "JOE cannot hear me" is the first thing that goes wrong with a
        headset, and the answer is almost always which device Windows is using.
        """
        try:
            diag = self.service.microphones.diagnostics()
        except Exception as error:
            return [("Microphone\n", "head"),
                    ("  could not read the device list: "
                     + str(error)[:70] + "\n\n", "warn")]

        in_use = diag.get("in_use") or ""
        chunks = [
            ("Microphone\n", "head"),
            ("  JOE hears            " + (in_use or "NOTHING CONNECTED") + "\n",
             "good" if in_use else "bad"),
            ("  device status        " + str(diag.get("in_use_status", "")) + "\n",
             None),
            ("  your preference      "
             + (diag.get("preferred") or "(none - Windows default)") + "\n", None),
        ]
        if not diag.get("preference_honoured", True):
            chunks.append(("  PREFERENCE NOT IN USE - see below\n", "warn"))
        chunks.append(("\n  Recording devices Windows knows about\n", None))
        for device in diag.get("devices", []):
            mark = "  -> " if device["name"] == in_use else "     "
            tag = "good" if device["name"] == in_use else "muted"
            extra = ""
            if device.get("bluetooth"):
                extra = "   bluetooth"
            if device.get("is_loopback"):
                extra = "   loopback - never used"
            chunks.append((mark + device["name"][:30].ljust(32)
                           + device["status"] + extra + "\n", tag))
        if diag.get("blocker"):
            chunks.append(("\n  " + diag["blocker"] + "\n", "warn"))
        chunks.append(("\n  " + diag.get("selection_note", "") + "\n", "muted"))
        chunks.append(("  Test it with the MIC_TEST launcher.\n\n", "muted"))
        return chunks

    # ---- actions ------------------------------------------------------

    def _on_sign_in(self) -> None:
        auth = getattr(self.service, "copilot_auth", None)
        if auth is None:
            messagebox.showinfo(
                "Not selected",
                "Microsoft 365 Copilot is not the selected reasoning provider.",
            )
            return
        try:
            self.flow = auth.begin_device_flow()
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("Sign-in could not start", str(error))
            self.refresh()
            return

        self._write([
            ("SIGN IN TO MICROSOFT 365\n\n", "head"),
            ("  1. Open   " + self.flow.verification_uri + "\n", None),
            ("  2. Enter this code:\n\n", None),
            ("        " + self.flow.user_code + "\n\n", "good"),
            ("  3. Sign in with a work or school account that has a\n"
             "     Microsoft 365 Copilot licence.\n\n", None),
            ("  A personal Microsoft account will not work - the API does not\n"
             "  support them.\n\n", "muted"),
            ("  Waiting for you to finish...\n", "muted"),
        ])
        self.line.config(text="Waiting for Microsoft sign-in to complete...")
        threading.Thread(target=self._await_sign_in, daemon=True).start()

    def _await_sign_in(self) -> None:
        auth = self.service.copilot_auth
        try:
            ok, message = auth.complete_device_flow(self.flow)
        except Exception as error:  # noqa: BLE001
            ok, message = False, str(error)
        self.window.after(0, lambda: self._sign_in_done(ok, message))

    def _sign_in_done(self, ok: bool, message: str) -> None:
        self.refresh()
        self.line.config(text=message)
        if not ok:
            messagebox.showwarning("Not signed in", message)

    def _on_sign_out(self) -> None:
        if not messagebox.askyesno(
            "Disconnect Microsoft 365",
            "Sign out and delete the stored authentication?\n\n"
            "The encrypted token cache is removed. Reasoning returns to "
            "NOT CONFIGURED. Every local capability keeps working.",
        ):
            return
        message = self.service.copilot_sign_out()
        self.refresh()
        self.line.config(text=message)
