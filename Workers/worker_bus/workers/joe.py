"""Joe: the voice at 70 MPH. Reads back, captures, and asks for confirmation.

Joe is a plug-in (`Dispatch/CLAUDE.md` section 5.4), and the clause that shapes
this worker is in the same paragraph: **"No direct Dispatch write authority may
be granted to Assistant."**

So Joe answers questions and *proposes* changes. A proposal is a structured
description of a change plus the exact words a person would have to say to
confirm it. Dispatch applies it, or does not. There is no path through this
worker by which speech becomes a database write, which is the only design that
survives a misheard word at speed -- and a driver's cab is the worst listening
environment any of this software will ever be used in.

The read-back contract is the D2 rule in code: a driver who is moving, tired and
has one hand gets the answer in one sentence, the most important thing first,
and never a list to scan.

**Portal entry (Mike Zachary's direction, 2026-09-13).** Joe performs the work of
the Library PIN Service: creating and resetting PINs, adding customer load numbers,
enabling and disabling users, and validating a PIN for a portal. These are Library
records, not Dispatch writes, so the clause above is untouched. Every administrative
action names the person Joe is acting for (`for_person`); a system identity is
refused. A PIN is never repeated in a response, and the bus audit records payloads
by shape only, so no PIN reaches a log.

The rules are the Library's, and Joe passes along how he was asked (`channel`):
an Operations PIN is authorized by Mike Zachary by voice (`VOICE`) or in the dialog
box (`DIALOG`), and nothing else; drivers choose their own PIN in the Driver portal,
so Joe only clears one (`pin_clear_driver`) so the driver can choose again; a
customer's load number is their PIN.
"""

from __future__ import annotations

from dataclasses import dataclass

from worker_bus.contracts import Capability, Finding, WorkerRequest, WorkerResponse, refuse


@dataclass
class JoeWorker:
    worker_id: str = "JOE"
    reader: object | None = None
    #: The bounded reasoner. None means Joe can still read back facts -- which is
    #: most of what a driver asks for -- and cannot answer anything open-ended.
    reasoner: object | None = None
    #: The Library PIN Service (`dispatch_library.catalog.PinService`), when the
    #: persistent Library is configured. None means portal entry is not managed here.
    pins: object | None = None

    PIN_CAPABILITIES = ("pin_create", "pin_add_customer_load", "pin_reset", "pin_clear_driver", "pin_enable",
                        "pin_disable", "pin_validate")

    def capabilities(self) -> tuple[Capability, ...]:
        pin_work = (
            Capability("pin_create", "Give an Operations user a PIN, as Mike Zachary authorizes by voice or dialog.",
                       produces="the user's record, never the PIN"),
            Capability("pin_add_customer_load", "Make a customer load number a Customer portal PIN.",
                       produces="the customer's record, never the load number"),
            Capability("pin_reset", "Replace an Operations user's PIN, as Mike Zachary authorizes by voice or dialog.",
                       produces="confirmation, never the PIN"),
            Capability("pin_clear_driver", "Clear a driver's PIN so the driver chooses a new one.",
                       produces="confirmation"),
            Capability("pin_enable", "Let a user into their portal again.", produces="the user's status"),
            Capability("pin_disable", "Stop a user entering their portal.", produces="the user's status"),
            Capability("pin_validate", "Check a PIN for a portal.",
                       produces="Authenticated with role, or Denied"),
        )
        return pin_work + (
            Capability(
                "read_back_load",
                "Say what the driver needs about the current load, in one sentence.",
                produces="spoken text, shortest-useful-answer first",
                reads=("load", "milestones", "appointment times"),
            ),
            Capability(
                "answer_question",
                "Answer a question about what is on file. Refuses anything not on file.",
                produces="an answer with its provenance",
                reads=("load", "driver", "equipment"),
            ),
            Capability(
                "propose_capture",
                "Turn something the driver said into a proposed change, with the words "
                "that would confirm it.",
                produces="a proposal, never a write",
            ),
        )

    def status(self) -> str:
        if self.reader is None:
            return "UNCONFIGURED"
        return "LIVE" if self.reasoner is not None else "CONFIGURED"

    def handle(self, request: WorkerRequest, deps) -> WorkerResponse:
        if request.capability in self.PIN_CAPABILITIES:
            return self._pin_work(request)
        if self.reader is None:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail="Joe cannot see Dispatch on this machine, so he has nothing to read back.",
            )
        return {
            "read_back_load": self._read_back,
            "answer_question": self._answer,
            "propose_capture": self._propose,
        }[request.capability](request)

    # ------------------------------------------------------------ portal entry

    def _pin_work(self, request: WorkerRequest) -> WorkerResponse:
        def answer(status, detail, artifacts=None):
            return WorkerResponse(worker=self.worker_id, capability=request.capability, status=status,
                                  correlation_id=request.correlation_id, detail=detail,
                                  artifacts=artifacts or {})

        if self.pins is None:
            return answer("UNCONFIGURED", "Portal entry is not managed on this machine: the persistent "
                                          "Library (DISPATCH_LIBRARY_CATALOG) is not configured.")
        p = request.payload
        if request.capability == "pin_validate":
            result = self.pins.validate(p.get("role", ""), p.get("pin", ""), client_key=p.get("client_key"),
                                        account=p.get("driver_ref"))
            return answer("LIVE", result.answer()["result"], {"answer": result.answer()})

        person = (p.get("for_person") or "").strip()
        channel = (p.get("channel") or "JOE").strip().upper()
        try:
            if request.capability == "pin_create":
                done = self.pins.create_pin(p.get("role", ""), p.get("name", ""), p.get("pin", ""),
                                            requested_by=person, subject_ref=p.get("subject_ref"), channel=channel)
                detail = f"{p.get('name')} can now enter the {p.get('role', '').title()} portal."
            elif request.capability == "pin_add_customer_load":
                done = self.pins.add_customer_load(p.get("customer", ""), p.get("load_number", ""),
                                                   requested_by=person, channel=channel)
                detail = (f"That load number already opens {p.get('customer')}'s view." if done.get("already_present")
                          else f"That load number now opens {p.get('customer')}'s view, and only theirs.")
            elif request.capability == "pin_reset":
                done = self.pins.reset_pin(p.get("role", ""), p.get("name", ""), p.get("pin", ""),
                                           requested_by=person, channel=channel)
                detail = f"{p.get('name')}'s PIN is changed. The old one no longer works."
            elif request.capability == "pin_clear_driver":
                done = self.pins.clear_driver_pin(p.get("driver_ref", ""), requested_by=person, channel=channel)
                detail = f"{done.get('display_name')}'s PIN is cleared. They choose a new one next time they sign in."
            else:
                enabled = request.capability == "pin_enable"
                done = self.pins.set_enabled(p.get("role", ""), p.get("name", ""), enabled, requested_by=person,
                                             channel=channel)
                detail = f"{p.get('name')} is {'enabled' if enabled else 'disabled'}."
        except (ValueError, KeyError) as exc:
            # The Library's refusals never contain a PIN; they are safe to say back.
            return refuse(request, self.worker_id, "pin_service_refused", str(exc).strip("'\""))
        return answer("LIVE", detail, {"record": {k: v for k, v in done.items() if k != "pin_hash"}})

    # ----------------------------------------------------------------- work

    def _read_back(self, request: WorkerRequest) -> WorkerResponse:
        load_id = request.payload.get("load_id", "")
        load = self.reader.get_load(load_id) if load_id else None
        if not load:
            return refuse(
                request, self.worker_id, "subject_not_found",
                f"There is no load {load_id!r} on file.",
                "Joe reads back what is recorded. He does not fill in a gap out loud.",
            )

        try:
            from conversation.readback import read_back_load
        except ImportError as exc:
            # The conversation layer is a separate package and may simply not
            # be installed here. That is UNCONFIGURED -- a thing not set up --
            # not UNAVAILABLE, which means something that should be reachable
            # is not. A raw ModuleNotFoundError in `detail` is a traceback, not
            # a status, and a driver reading it learns nothing.
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail=(
                    "Joe's conversation layer is not installed on this machine, "
                    f"so he cannot read a load back ({exc})."
                ),
            )

        spoken = read_back_load(load, aspect=request.payload.get("aspect", ""))
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability, status="LIVE",
            correlation_id=request.correlation_id,
            artifacts={"spoken": spoken.text, "aspect": spoken.aspect,
                       "unknown": list(spoken.unknown)},
            findings=tuple(
                Finding("NOT_ON_FILE", f"{name} is not recorded.", confidence="ABSENT")
                for name in spoken.unknown
            ),
            detail=spoken.text,
        )

    def _answer(self, request: WorkerRequest) -> WorkerResponse:
        question = (request.payload.get("question") or "").strip()
        if not question:
            return refuse(request, self.worker_id, "nothing_asked", "No question was given.")
        if self.reasoner is None:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail=(
                    "No reasoning provider is configured, so Joe cannot answer an "
                    "open question. He can still read back anything that is on file."
                ),
            )
        answer = self.reasoner.answer(question, context=request.payload.get("context", ""))
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status=getattr(answer, "status", "UNVERIFIED"),
            correlation_id=request.correlation_id,
            artifacts={"spoken": getattr(answer, "text", ""),
                       "provenance": getattr(answer, "provenance", "")},
            detail=getattr(answer, "text", "")[:300],
        )

    def _propose(self, request: WorkerRequest) -> WorkerResponse:
        try:
            from conversation.capture import propose_change
        except ImportError as exc:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail=(
                    "Joe's conversation layer is not installed on this machine, "
                    f"so he cannot turn what the driver said into a proposal ({exc})."
                ),
            )

        proposal = propose_change(
            heard=request.payload.get("heard", ""),
            load_id=request.payload.get("load_id", ""),
            confidence=float(request.payload.get("confidence", 0.0)),
        )
        if proposal is None:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNVERIFIED", correlation_id=request.correlation_id,
                detail=(
                    "Joe did not understand that well enough to propose anything. "
                    "Saying nothing is the correct answer to a misheard sentence."
                ),
            )
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status="LIVE", correlation_id=request.correlation_id,
            artifacts={
                "proposal": proposal.to_dict(),
                "spoken": proposal.confirmation_prompt,
                # There is no field here by which this becomes a write. Dispatch
                # applies a proposal, or does not.
                "applies_itself": False,
            },
            recommendations=(proposal.confirmation_prompt,),
            detail=proposal.summary,
        )
