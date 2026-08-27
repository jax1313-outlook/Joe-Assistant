"""The JOE window.

Renders what AssistantService returns. Holds no business logic: it collects a
request, hands it to the service, and draws the response.

Work that can take time - Outlook, voice - runs on a worker thread so the
window never freezes. Results come back through a queue and are drawn on the
main thread.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox

TITLE = "JOE, the Level 1 Assistant"

BG = "#0f1216"
PANEL = "#181d24"
PANEL2 = "#1f252e"
INK = "#e9ecf1"
MUTED = "#98a3b3"
ACCENT = "#4c8dff"
GOOD = "#3fb950"
WARN = "#d29922"
BAD = "#f85149"

# The two appearances of the VOICE button. Defined here so the audit and the
# tests can assert them without reaching into the widget's construction.
VOICE_OFF_TEXT = "voice"
VOICE_ON_TEXT = "VOICE"
VOICE_OFF_FONT = ("Segoe UI", 11)
VOICE_ON_FONT = ("Segoe UI Semibold", 13)
VOICE_OFF_COLOURS = {"bg": "#1b2029", "fg": "#5f6b7d",
                     "activebackground": "#232a35", "activeforeground": "#8b97a8"}
VOICE_ON_COLOURS = {"bg": "#1f7a3d", "fg": "#ffffff",
                    "activebackground": "#249349", "activeforeground": "#ffffff"}

MONO = ("Consolas", 10)
UI = ("Segoe UI", 10)
UI_BOLD = ("Segoe UI Semibold", 10)


def _mode_colour(status) -> str:
    if status.live_connection:
        return GOOD
    if status.mode == "SAMPLE":
        return WARN
    if status.mode == "READY":
        return ACCENT
    return BAD


class AssistantWindow:
    def __init__(self, service, voice_test: bool = False) -> None:
        self.service = service
        self.voice_test = voice_test
        self.voice_test_log: list = []
        self._speak_after = False
        self.results: queue.Queue = queue.Queue()
        self.busy = False
        # Built on first use. Startup must never open the microphone.
        self.voice_loop = None

        self.root = tk.Tk()
        self.root.title(TITLE)
        self.root.geometry("1180x820")
        self.root.minsize(980, 660)
        self.root.configure(bg=BG)

        self._build()
        self.service.reload_history()
        self._refresh_status()
        self._refresh_history()
        if voice_test:
            self._show_voice_test()
        else:
            self._show_welcome()
        self.root.after(120, self._drain)

    # ================================================================
    # Layout
    # ================================================================

    def _build(self) -> None:
        # ---- header -------------------------------------------------
        header = tk.Frame(self.root, bg=PANEL)
        header.pack(fill="x")
        tk.Label(
            header, text="Level 1 Assistant", bg=PANEL, fg=INK,
            font=("Segoe UI Semibold", 16), anchor="w",
        ).pack(fill="x", padx=18, pady=(12, 0))
        tk.Label(
            header,
            text=(
                "Dispatch Plugin  -  Dispatch remains the System of Record and "
                "Operational Authority. JOE may recommend; it may not "
                "approve, decide, or change operational truth."
            ),
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w",
            wraplength=1100, justify="left",
        ).pack(fill="x", padx=18, pady=(2, 6))

        self.mode_label = tk.Label(
            header, text="", bg=PANEL, fg=ACCENT, font=UI_BOLD, anchor="w",
        )
        self.mode_label.pack(fill="x", padx=18, pady=(0, 4))

        # ---- capability status strip --------------------------------
        self.status_strip = tk.Frame(header, bg=PANEL)
        self.status_strip.pack(fill="x", padx=14, pady=(0, 12))
        self.status_labels: dict[str, tk.Label] = {}

        # ---- body ---------------------------------------------------
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # left: history
        left = tk.Frame(body, bg=BG, width=330)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        tk.Label(left, text="Interaction history", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")
        hwrap = tk.Frame(left, bg=BG)
        hwrap.pack(fill="both", expand=True, pady=(4, 8))
        hscroll = tk.Scrollbar(hwrap, orient="vertical")
        hscroll.pack(side="right", fill="y")
        self.history = tk.Listbox(
            hwrap, bg=PANEL, fg=INK, font=MONO, selectbackground=ACCENT,
            selectforeground="#ffffff", borderwidth=0, highlightthickness=0,
            activestyle="none", yscrollcommand=hscroll.set,
        )
        self.history.pack(side="left", fill="both", expand=True)
        hscroll.config(command=self.history.yview)
        self.history.bind("<<ListboxSelect>>", self._on_select)

        self.selected_label = tk.Label(
            left, text="Nothing selected", bg=BG, fg=MUTED,
            font=("Segoe UI", 9), anchor="w", wraplength=310, justify="left",
        )
        self.selected_label.pack(fill="x", pady=(0, 6))

        # action buttons
        actions = tk.Frame(left, bg=BG)
        actions.pack(fill="x")
        self.action_buttons: dict[str, tk.Button] = {}
        for label, intent in (
            ("Save", "LEVEL_2"),
            ("Level 3", "LEVEL_3"),
            ("Print", "PRINT"),
            ("Delete", "DELETE"),
        ):
            button = tk.Button(
                actions, text=label,
                command=lambda i=intent: self._on_action(i),
                bg=PANEL2, fg=INK, font=UI, relief="flat",
                padx=10, pady=7, cursor="hand2", disabledforeground="#5a6472",
            )
            button.pack(side="left", padx=(0, 6))
            self.action_buttons[intent] = button

        # right: response
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="Response", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")

        rwrap = tk.Frame(right, bg=BG)
        rwrap.pack(fill="both", expand=True, pady=(4, 8))
        rscroll = tk.Scrollbar(rwrap, orient="vertical")
        rscroll.pack(side="right", fill="y")
        self.response = tk.Text(
            rwrap, bg=PANEL, fg=INK, font=MONO, wrap="word",
            borderwidth=0, highlightthickness=0, padx=12, pady=10,
            yscrollcommand=rscroll.set, insertbackground=INK,
        )
        self.response.pack(side="left", fill="both", expand=True)
        rscroll.config(command=self.response.yview)
        for tag, colour, font in (
            ("answer", INK, ("Consolas", 12, "bold")),
            ("head", ACCENT, ("Segoe UI Semibold", 10)),
            ("muted", MUTED, MONO),
            ("warn", WARN, MONO),
            ("bad", BAD, MONO),
            ("good", GOOD, MONO),
        ):
            self.response.tag_configure(tag, foreground=colour, font=font)
        self.response.configure(state="disabled")

        # quick access
        quick = tk.Frame(right, bg=BG)
        quick.pack(fill="x", pady=(0, 8))
        for label, handler in (
            ("Library search", self._on_library),
            ("Research", self._on_research),
            ("Calendar", lambda: self._ask_text("What is on my calendar?")),
            ("Unread mail", lambda: self._ask_text("Show me unread mail")),
            ("Speak answer", self._on_speak),
            ("Help", lambda: self._ask_text("help")),
            ("Settings", self._on_settings),
        ):
            tk.Button(
                quick, text=label, command=handler, bg=PANEL2, fg=MUTED,
                font=("Segoe UI", 9), relief="flat", padx=9, pady=5,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

        # input
        entry_row = tk.Frame(right, bg=BG)
        entry_row.pack(fill="x")
        self.entry = tk.Entry(
            entry_row, bg=PANEL, fg=INK, insertbackground=INK,
            font=("Segoe UI", 12), relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self._on_send())
        self.entry.focus_set()
        self.send_button = tk.Button(
            entry_row, text="Ask", command=self._on_send, bg=ACCENT,
            fg="#ffffff", font=("Segoe UI Semibold", 11), relief="flat",
            padx=26, pady=8, cursor="hand2",
        )
        self.send_button.pack(side="left")

        # The VOICE button. Its appearance IS the status indicator - lowercase
        # and subdued when off, uppercase and white when listening. Mike should
        # be able to tell whether JOE is listening from the far side of the cab
        # without reading a word of it.
        self.voice_button = tk.Button(
            entry_row, text=VOICE_OFF_TEXT, command=self._on_voice_toggle,
            font=VOICE_OFF_FONT, relief="flat", padx=22, pady=8,
            cursor="hand2", **VOICE_OFF_COLOURS,
        )
        self.voice_button.pack(side="left", padx=(8, 0))

        # ---- status line --------------------------------------------
        self.status_line = tk.Label(
            self.root, text="Ready.", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        )
        self.status_line.pack(fill="x", side="bottom", ipady=8, ipadx=18)

    # ================================================================
    # Rendering
    # ================================================================

    def _write(self, chunks) -> None:
        self.response.configure(state="normal")
        self.response.delete("1.0", tk.END)
        for text, tag in chunks:
            self.response.insert(tk.END, text, tag)
        self.response.configure(state="disabled")
        self.response.see("1.0")

    def _show_welcome(self) -> None:
        statuses = self.service.status()
        chunks = [
            ("Ask in ordinary words.\n\n", "answer"),
            ("Examples\n", "head"),
            (
                "  What matters about tomorrow's run?\n"
                "  Find the broker packet\n"
                "  Explain that in plain language\n"
                "  Research the road restriction\n"
                "  Save this      Level 3 this under Ideas      Print this      Delete this\n\n",
                "muted",
            ),
            ("What is connected right now\n", "head"),
        ]
        for status in statuses:
            tag = (
                "good" if status.live_connection
                else "warn" if status.mode == "SAMPLE"
                else "muted" if status.mode == "READY"
                else "bad"
            )
            chunks.append(("  " + status.display() + "\n", tag))
        chunks.append(
            (
                "\nAnything marked SAMPLE DATA is not live. Anything marked NOT "
                "CONNECTED was not contacted, and I will say so rather than "
                "substitute something.\n",
                "muted",
            )
        )
        self._write(chunks)

    def _render_response(self, interaction) -> None:
        response = interaction.response
        chunks = [(response.answer + "\n\n", "answer")]

        if response.notices:
            for notice in response.notices:
                tag = "warn" if "SAMPLE" in notice or "older than" in notice else "muted"
                chunks.append(("  ! " + notice + "\n", tag))
            chunks.append(("\n", "muted"))

        if not response.ok:
            chunks.append(("  This did not complete: " + response.failure + "\n\n", "bad"))

        chunks.append(("Written response\n", "head"))
        chunks.append((response.written + "\n\n", None))

        if response.uncertainty:
            chunks.append(("Uncertainty\n", "head"))
            chunks.append(("  " + response.uncertainty + "\n\n", "warn"))

        if response.provenance:
            chunks.append(("Sources\n", "head"))
            for provenance in response.provenance:
                tag = "good" if provenance.is_live else "warn"
                chunks.append(("  " + provenance.line() + "\n", tag))
            chunks.append(("\n", "muted"))

        chunks.append(("Authority\n", "head"))
        chunks.append(
            (
                "  This is information and, where offered, a recommendation.\n"
                "  approved=False   decided=False   acted_on=False   "
                "operational_write=False\n"
                "  Dispatch remains the System of Record. "
                "Mike Zachary remains final authority.\n",
                "muted",
            )
        )
        self._write(chunks)

    def _refresh_status(self) -> None:
        self.mode_label.config(text="Operating mode:  " + self.service.operating_mode())
        for widget in self.status_strip.winfo_children():
            widget.destroy()
        self.status_labels = {}
        for status in self.service.status():
            label = tk.Label(
                self.status_strip, text="  " + status.chip() + "  ",
                bg=PANEL2, fg=_mode_colour(status), font=("Consolas", 9),
                padx=6, pady=4,
            )
            label.pack(side="left", padx=(4, 0))
            # Hovering a chip shows the full detail, so the strip stays short
            # without hiding anything.
            self._tooltip(label, status.display() + (
                "  |  " + status.blocker if status.blocker else ""
            ))
            self.status_labels[status.name] = label

    def _tooltip(self, widget, text: str) -> None:
        """Plain hover text. No queue, no click, nothing to dismiss."""
        holder = {"win": None}

        def show(_event=None):
            if holder["win"] is not None:
                return
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.wm_geometry("+%d+%d" % (x, y))
            tk.Label(
                win, text=text, bg="#2b333f", fg=INK, font=("Consolas", 9),
                padx=8, pady=5, justify="left",
            ).pack()
            holder["win"] = win

        def hide(_event=None):
            if holder["win"] is not None:
                holder["win"].destroy()
                holder["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _refresh_history(self) -> None:
        rows = self.service.history()
        self.history.delete(0, tk.END)
        self._rows = rows
        selected_index = None
        for index, row in enumerate(rows):
            marker = ">" if row["selected"] else " "
            level = row["level"].replace("LEVEL_", "L")
            self.history.insert(
                tk.END,
                "{0} {1:<11} {2:<3} {3}".format(
                    marker, row["state"][:11], level, row["request"][:26]
                ),
            )
            if row["selected"]:
                selected_index = index
        if selected_index is not None:
            self.history.selection_clear(0, tk.END)
            self.history.selection_set(selected_index)
            self.history.see(selected_index)
            row = rows[selected_index]
            self.selected_label.config(
                text=(
                    "Selected: " + row["state"] + " / " + row["level"]
                    + ("  (expires " + row["expires_at"][11:16] + "Z)"
                       if row["expires_at"] else "  (no expiration)")
                )
            )
        else:
            self.selected_label.config(text="Nothing selected")
        enabled = tk.NORMAL if rows and selected_index is not None else tk.DISABLED
        for button in self.action_buttons.values():
            button.config(state=enabled)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.busy = busy
        self.send_button.config(state=tk.DISABLED if busy else tk.NORMAL)
        if message:
            self.status_line.config(text=message)

    # ================================================================
    # Events
    # ================================================================

    def _on_send(self) -> None:
        self._ask_text(self.entry.get())

    def _ask_text(
        self, text: str, channel: str = "text", speak_after: bool = False
    ) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            self.status_line.config(text="Nothing to ask.")
            return
        if self.busy:
            self.status_line.config(text="Still working on the last request.")
            return
        self.entry.delete(0, tk.END)
        self._set_busy(True, "Working: " + cleaned[:60])
        self._speak_after = speak_after
        threading.Thread(
            target=self._work, args=(cleaned, channel), daemon=True
        ).start()

    def _work(self, text: str, channel: str = "text") -> None:
        try:
            interaction = self.service.ask(text, channel=channel)
            self.results.put(("interaction", interaction))
        except Exception as error:  # never let a worker kill the window
            self.results.put(("error", str(error)))

    def _on_action(self, intent: str) -> None:
        if self.busy:
            return
        selected = self.service.selected()
        if selected is None:
            self.status_line.config(text="Select an interaction first.")
            return
        if intent == "DELETE":
            if not messagebox.askyesno(
                "Delete interaction",
                "Delete this interaction?\n\nIts content is purged and cannot be "
                "recovered. Nothing outside JOE is affected.",
            ):
                return
        response = self.service.apply_retention(selected.record_id, intent)
        self._render_response(
            type("R", (), {"response": response})()
        )
        self._refresh_history()
        self.status_line.config(text=response.answer[:120])

    def _on_select(self, _event=None) -> None:
        picked = self.history.curselection()
        if not picked:
            return
        index = picked[0]
        if 0 <= index < len(self._rows):
            self.service.select(self._rows[index]["record_id"])
            interaction = self.service.selected()
            if interaction:
                self._render_response(interaction)
        self._refresh_history()

    def _on_library(self) -> None:
        term = self.entry.get().strip()
        self._ask_text("Find " + term if term else "Find ")

    def _on_research(self) -> None:
        term = self.entry.get().strip()
        if not term:
            self.status_line.config(text="Type what to research, then press Research.")
            return
        self._ask_text("Research " + term)

    def _on_settings(self) -> None:
        """Open the Microsoft 365 Copilot connection panel."""
        from ui.settings_panel import SettingsPanel

        SettingsPanel(self.root, self.service)

    def _on_speak(self) -> None:
        interaction = self.service.selected()
        if interaction is None:
            self.status_line.config(text="Nothing selected to speak.")
            return
        if self.busy:
            return
        self._set_busy(True, "Speaking...")
        text = interaction.response.spoken_summary or interaction.response.answer
        threading.Thread(
            target=lambda: self.results.put(("speak", self.service.speak(text))),
            daemon=True,
        ).start()

    def _on_voice_toggle(self) -> None:
        """Turn continuous Driver Mode on or off."""
        loop = self._voice_loop()
        if loop.is_on:
            loop.stop()
            self.status_line.config(text="Voice off. Typed input still works.")
        else:
            probe = self.service.voice.probe()
            if not probe.get("stt_engine_available"):
                # A microphone problem must never disable JOE. Say so and stay
                # in text mode rather than leaving a dead button.
                self.status_line.config(
                    text="Voice input is unavailable on this machine. "
                         + (probe.get("blocker") or "") + " Text mode still works."
                )
                return
            loop.start()
            self.status_line.config(text="VOICE on. Just talk - no buttons.")
        self._paint_voice_button()

    def _voice_loop(self):
        """Build the loop on first use, so startup never touches the mic."""
        if getattr(self, "voice_loop", None) is None:
            from app.driver_voice import DriverVoiceLoop

            self.voice_loop = DriverVoiceLoop(
                listen=self._voice_listen,
                speak=self._voice_speak,
                ask=self._voice_ask,
                on_state=lambda state: self.root.after(0, self._paint_voice_button),
                on_turn=lambda turn: self.root.after(0, self._refresh_history),
            )
        return self.voice_loop

    def _voice_listen(self, seconds):
        return (self.service.listen(seconds or 6) or {}).get("text", "")

    def _voice_speak(self, text):
        return bool((self.service.speak(text) or {}).get("spoken"))

    def _voice_ask(self, text, short=False, save=False):
        """One spoken request through the ordinary path. Returns (spoken, id).

        Voice is transport, so this is the SAME path typed input takes. A
        separate voice path would drift from the typed one and the two would
        stop agreeing about what JOE can do."""
        if save:
            selected = self.service.selected()
            if selected is not None:
                response = self.service.apply_retention(
                    selected.record_id, "LEVEL_2")
                self.root.after(0, self._refresh_history)
                return (response.answer or "Saved."), selected.record_id
            return "There is nothing selected to save.", ""

        result = self.service.ask(text, channel="voice")
        response = result.response
        self.root.after(0, lambda: self._render_response(result))
        self.root.after(0, self._refresh_history)
        spoken = response.spoken_summary or response.answer or ""
        if short:
            spoken = spoken.split(".")[0].strip() + "."
        return spoken, getattr(result, "record_id", "")

    def _paint_voice_button(self) -> None:
        """The button's appearance is the status indicator."""
        loop = getattr(self, "voice_loop", None)
        button = getattr(self, "voice_button", None)
        if button is None:
            return
        if loop is None or not loop.is_on:
            button.config(text=VOICE_OFF_TEXT, font=VOICE_OFF_FONT,
                          **VOICE_OFF_COLOURS)
            return
        colours = dict(VOICE_ON_COLOURS)
        text = VOICE_ON_TEXT
        if loop.is_speaking:
            # Speaking is visually distinct from listening, so Mike is never
            # talking over JOE or waiting on a JOE that is not listening.
            colours["bg"] = "#8a5a00"
            colours["activebackground"] = "#a06a00"
            text = "SPEAKING"
        button.config(text=text, font=VOICE_ON_FONT, **colours)

    def _on_listen(self) -> None:
        if self.busy:
            return
        self._set_busy(True, "LISTENING - speak now...")
        self._write([
            ("LISTENING - speak now.\n\n", "answer"),
            ("Say your request. What I hear will be shown here before "
             "anything is done with it.\n", "muted"),
        ])
        threading.Thread(
            target=lambda: self.results.put(("listen", self.service.listen(7))),
            daemon=True,
        ).start()

    def _show_voice_test(self) -> None:
        """The voice-input test card. Shown only with --voice-test."""
        self._write([
            ("VOICE INPUT TEST\n\n", "answer"),
            ("  1. Press Listen.\n"
             "  2. Say:  What is on my calendar tomorrow?\n"
             "  3. Wait for the recognized text to appear here.\n"
             "  4. Confirm whether the displayed text matches what you said.\n\n",
             None),
            ("What must be observed before voice input is called proven\n", "head"),
            ("  microphone access succeeded\n"
             "  audio was received\n"
             "  recognized text was produced\n"
             "  recognized text was visibly displayed\n"
             "  the recognized request entered the normal workflow\n"
             "  a written response was produced\n"
             "  a spoken response was heard\n"
             "  the written record was retained\n\n", "muted"),
            ("No microphone audio is kept. Only the recognized text is "
             "retained, under Level 1 rules.\n\n", "muted"),
            ("If it fails it will say so plainly, and text mode stays "
             "available.\n", "muted"),
        ])

    def _record_voice_step(self, step: str, detail: str) -> None:
        if self.voice_test:
            self.voice_test_log.append({"step": step, "detail": detail})

    def _handle_listen_result(self, payload: dict) -> None:
        """Show what was heard, then run it through the normal text path.

        The recognized text is displayed before processing, so Mike can see
        what the machine believed he said. A failure states what failed;
        nothing is assumed and nothing is invented.
        """
        heard = (payload.get("text") or "").strip()
        if not payload.get("recognized") or not heard:
            reason = payload.get("error") or "Speech was not recognized."
            lowered = reason.lower()
            if "no recognition engine" in lowered or "not available" in lowered:
                message = "Voice input is unavailable. Text mode remains available."
            elif "nothing was recognized" in lowered:
                message = "Speech was not recognized. Please try again."
            else:
                message = reason
            self._record_voice_step("recognition_failed", message)
            self.status_line.config(text=message)
            self._write([
                ("Voice input did not produce text.\n\n", "answer"),
                (message + "\n\n", "bad"),
                ("Nothing was assumed and nothing was invented.\n"
                 "Type your request instead - text mode is unaffected.\n", "muted"),
            ])
            self._set_busy(False)
            return

        confidence = round(float(payload.get("confidence", 0.0) or 0.0), 2)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, heard)
        self._record_voice_step(
            "recognized", heard + "  (confidence " + str(confidence) + ")"
        )
        self._write([
            ("HEARD:  " + heard + "\n\n", "answer"),
            ("confidence " + str(confidence) + "\n\n", "muted"),
            ("Sending that through the same path as typed input...\n", "muted"),
        ])
        self.status_line.config(
            text="Heard: " + heard + "   (confidence " + str(confidence) + ")"
        )
        self._set_busy(False)
        # Voice is transport. The recognized text takes the typed-input path.
        self._ask_text(heard, channel="voice", speak_after=True)

    # ================================================================
    # Worker results
    # ================================================================

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.results.get_nowait()
                if kind == "interaction":
                    self._render_response(payload)
                    self._refresh_history()
                    self._refresh_status()
                    self.status_line.config(text=payload.response.answer[:130])
                    self._record_voice_step(
                        "written_answer", payload.response.answer[:120]
                    )
                    self._record_voice_step("record_retained", payload.record_id)
                    if self._speak_after:
                        self._speak_after = False
                        spoken = (
                            payload.response.spoken_summary
                            or payload.response.answer
                        )
                        self._record_voice_step("speaking", spoken[:120])
                        threading.Thread(
                            target=lambda t=spoken: self.results.put(
                                ("speak", self.service.speak(t))
                            ),
                            daemon=True,
                        ).start()
                elif kind == "error":
                    self.status_line.config(text="That request failed: " + payload)
                elif kind == "speak":
                    if payload.get("spoken"):
                        self._record_voice_step("spoken_aloud", "True")
                        self.status_line.config(text="Spoken aloud.")
                    else:
                        message = (
                            "Voice output is unavailable. The written answer is "
                            "still shown. " + payload.get("error", "")
                        )
                        self._record_voice_step("speak_failed", message)
                        self.status_line.config(text=message)
                elif kind == "listen":
                    self._handle_listen_result(payload)
                    continue
                self._set_busy(False)
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    # ================================================================
    # Lifecycle
    # ================================================================

    def run(self) -> None:  # pragma: no cover - needs a display
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    def _close(self) -> None:  # pragma: no cover - needs a display
        if self.voice_loop is not None:
            self.voice_loop.stop()
        self.service.shutdown()
        self.root.destroy()
