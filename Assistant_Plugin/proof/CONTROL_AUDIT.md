# JOE - Operator Control Audit

**Run:** 2026-08-26T23:31:51+00:00

Mike operated JOE and reported that some controls work and some do not. That finding governs. A passing test suite does not overrule it.

**20 controls audited. 0 need work.**

| Control | Expected | Actual | Result | Files |
| --- | --- | --- | --- | --- |
| Ask | typed question produces a written answer | answer rendered, 1123 chars | **PASS** | `ui/window.py::_on_send` |
| Entry cleared | the box empties so the next question can be typed | entry = '' | **PASS** | `ui/window.py::_on_send` |
| Busy released | controls usable again once the answer arrives | busy = False | **PASS** | `ui/window.py::_set_busy` |
| History select | clicking a row selects that interaction | selected MEM-20260825-115245-AE93ED | **PASS** | `ui/window.py::_on_select` |
| Save | Save -> SAVED on the SELECTED record | LEVEL_2 / SAVED | **PASS** | `ui/window.py::_on_action` |
| Save selection | the same record stays selected | MEM-20260826-233047-02E8B7 == MEM-20260826-233047-02E8B7 | **PASS** | `app/service.py::apply_retention` |
| Print | Print -> PRINT_READY on the SELECTED record | LEVEL_1 / PRINT_READY | **PASS** | `ui/window.py::_on_action` |
| Print selection | the same record stays selected | MEM-20260826-233050-84821F == MEM-20260826-233050-84821F | **PASS** | `app/service.py::apply_retention` |
| Level 3 | Level 3 -> FORMAL on the SELECTED record | LEVEL_3 / FORMAL | **PASS** | `ui/window.py::_on_action` |
| Level 3 selection | the same record stays selected | MEM-20260826-233053-0101AE == MEM-20260826-233053-0101AE | **PASS** | `app/service.py::apply_retention` |
| Delete | the selected interaction becomes DELETED | state = DELETED | **PASS** | `ui/window.py::_on_action` |
| Library search | searches the Library | something changed on screen | **PASS** | `ui/window.py` |
| Research | researches the typed subject | something changed on screen | **PASS** | `ui/window.py` |
| Calendar | reads the calendar | something changed on screen | **PASS** | `ui/window.py` |
| Unread mail | reads mail | something changed on screen | **PASS** | `ui/window.py` |
| Help | shows what JOE can do | something changed on screen | **PASS** | `ui/window.py` |
| Speak answer | speaks the selected answer | something changed on screen | **PASS** | `ui/window.py` |
| Settings | opens and shows connection state | opened, 2397 chars rendered | **PASS** | `ui/settings_panel.py` |
| Settings secrets | no token material on screen | leaked: none | **PASS** | `ui/settings_panel.py` |
| Status freshness | the chips match what the service reports | shown: Reasoning LIVE     Library LIVE     Outlook READY     Research LIVE    | **PASS** | `ui/window.py::_refresh_status` |

Every audited control behaved as expected in this pass.

That is not the same as Mike accepting them. Hands-on operation is the gate.
