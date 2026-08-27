"""tkinter window for the Assistant UI.

A thin renderer over AssistantUIViewModel. Every decision lives in the view
model; this file only draws it and forwards clicks.

tkinter ships with Python on Windows. Nothing is installed and nothing
outside this folder is imported.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .actions import ActionKind
from .view_model import AssistantUIViewModel

BG = "#12151a"
PANEL = "#1b2028"
INK = "#e8eaed"
MUTED = "#9aa4b2"
ACCENT = "#4c8dff"


class AssistantWindow:
    """The driver-facing Assistant window."""

    def __init__(self, view_model: AssistantUIViewModel | None = None) -> None:
        self.vm = view_model or AssistantUIViewModel()
        self.root = tk.Tk()
        self.root.title(self.vm.view_state().title)
        self.root.geometry("900x680")
        self.root.minsize(720, 520)
        self.root.configure(bg=BG)
        self._build()
        self._refresh()

    # ---- layout -------------------------------------------------------

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=PANEL)
        header.pack(fill="x", padx=0, pady=0)
        tk.Label(
            header,
            text="Level 1 Assistant",
            bg=PANEL,
            fg=INK,
            font=("Segoe UI Semibold", 15),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(
            header,
            text=self.vm.view_state().banner,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=860,
            justify="left",
        ).pack(fill="x", padx=16, pady=(0, 12))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(
            body, text="Conversation", bg=BG, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x")

        list_wrap = tk.Frame(body, bg=BG)
        list_wrap.pack(fill="both", expand=True, pady=(4, 10))
        scroll = tk.Scrollbar(list_wrap, orient="vertical")
        scroll.pack(side="right", fill="y")
        self.history = tk.Listbox(
            list_wrap,
            bg=PANEL, fg=INK, font=("Consolas", 10),
            selectbackground=ACCENT, selectforeground="#ffffff",
            borderwidth=0, highlightthickness=0, activestyle="none",
            yscrollcommand=scroll.set,
        )
        self.history.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.history.yview)
        self.history.bind("<<ListboxSelect>>", self._on_select)

        entry_row = tk.Frame(body, bg=BG)
        entry_row.pack(fill="x", pady=(0, 10))
        self.entry = tk.Entry(
            entry_row, bg=PANEL, fg=INK, insertbackground=INK,
            font=("Segoe UI", 11), relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self.entry.bind("<Return>", lambda _event: self._on_send())
        tk.Button(
            entry_row, text="Send", command=self._on_send,
            bg=ACCENT, fg="#ffffff", font=("Segoe UI Semibold", 10),
            relief="flat", padx=20, pady=6, cursor="hand2",
        ).pack(side="left")

        button_row = tk.Frame(body, bg=BG)
        button_row.pack(fill="x", pady=(0, 10))
        self.buttons: dict[str, tk.Button] = {}
        for kind in ActionKind.ALL:
            button = tk.Button(
                button_row,
                text=kind.replace("_", " ").title(),
                command=lambda k=kind: self._on_action(k),
                bg=PANEL, fg=INK, font=("Segoe UI", 10),
                relief="flat", padx=18, pady=7, cursor="hand2",
                disabledforeground="#5a6472",
            )
            button.pack(side="left", padx=(0, 8))
            self.buttons[kind] = button

        tk.Label(
            body, text="Requests recorded in this window", bg=BG, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x")
        self.requests = tk.Listbox(
            body, bg=PANEL, fg=MUTED, font=("Consolas", 9),
            borderwidth=0, highlightthickness=0, height=5, activestyle="none",
        )
        self.requests.pack(fill="x", pady=(4, 10))

        self.status = tk.Label(
            self.root, text="", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        )
        self.status.pack(fill="x", side="bottom", ipady=7, ipadx=16)

    # ---- events -------------------------------------------------------

    def _on_send(self) -> None:
        self.vm.send(self.entry.get())
        self.entry.delete(0, tk.END)
        self._refresh()

    def _on_select(self, _event=None) -> None:
        picked = self.history.curselection()
        if not picked:
            return
        turns = self.vm.conversation.turns
        index = picked[0]
        if 0 <= index < len(turns):
            self.vm.select(turns[index].turn_id)
        self._refresh(keep_listbox_selection=True)

    def _on_action(self, kind: str) -> None:
        self.vm.press(kind)
        self._refresh()

    # ---- rendering ----------------------------------------------------

    def _refresh(self, keep_listbox_selection: bool = False) -> None:
        state = self.vm.view_state()

        if not keep_listbox_selection:
            self.history.delete(0, tk.END)
            for line in state.history:
                self.history.insert(tk.END, line)
            if state.selected_id:
                for index, turn in enumerate(self.vm.conversation.turns):
                    if turn.turn_id == state.selected_id:
                        self.history.selection_clear(0, tk.END)
                        self.history.selection_set(index)
                        self.history.see(index)
                        break

        self.requests.delete(0, tk.END)
        for line in state.action_history:
            self.requests.insert(tk.END, line)

        for button_state in state.buttons:
            self.buttons[button_state.kind].config(
                state=(tk.NORMAL if button_state.enabled else tk.DISABLED)
            )

        self.status.config(text=state.status)

    # ---- lifecycle ----------------------------------------------------

    def run(self) -> None:  # pragma: no cover - needs a display
        self.root.mainloop()


def main() -> int:  # pragma: no cover - needs a display
    AssistantWindow().run()
    return 0
