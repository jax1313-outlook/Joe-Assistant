"""When: turning ordinary date words into a calendar range.

Deterministic. No model. "tomorrow", "today", "next week", "on the 30th",
"September 2", "next" - each maps to a range a reviewer can predict.

Used only for reading a calendar. Nothing here writes or schedules anything.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}

# "what is next", "next scheduled item" - the soonest thing, not a whole day.
_NEXT = (
    r"\bnext (?:scheduled )?(?:item|thing|appointment|stop|meeting|event)\b",
    r"\bwhat(?:'s| is) next\b",
    r"\bcoming up next\b",
)


def _midnight(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def wants_next_item(text: str) -> bool:
    lowered = " ".join((text or "").lower().split())
    return any(re.search(pattern, lowered) for pattern in _NEXT)


def parse_when(text: str, now: datetime | None = None) -> tuple[str, datetime | None]:
    """Return (kind, anchor).

    kind is one of: today, tomorrow, this week, next week, date, next, default.
    `anchor` is set only for `kind == "date"`.
    """
    moment = now or datetime.now()
    lowered = " ".join((text or "").lower().split())

    if wants_next_item(lowered):
        return "next", None
    if re.search(r"\btomorrow\b", lowered):
        return "tomorrow", None
    if re.search(r"\btoday\b|\bthis morning\b|\bthis afternoon\b|\btonight\b", lowered):
        return "today", None
    if re.search(r"\bnext week\b", lowered):
        return "next week", None
    if re.search(r"\bthis week\b|\brest of the week\b", lowered):
        return "this week", None

    # "on Friday", "Friday"
    weekday = re.search(r"\b(?:on |this |next )?(" + "|".join(WEEKDAYS) + r")\b", lowered)
    if weekday:
        target_dow = WEEKDAYS[weekday.group(1)]
        ahead = (target_dow - moment.weekday()) % 7
        if ahead == 0 and "next" in lowered:
            ahead = 7
        return "date", _midnight(moment) + timedelta(days=ahead)

    # "September 2", "2 September", "Sep 2nd"
    month_first = re.search(
        r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", lowered
    )
    day_first = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + "|".join(MONTHS) + r")\b", lowered
    )
    if month_first or day_first:
        if month_first:
            month, day = MONTHS[month_first.group(1)], int(month_first.group(2))
        else:
            month, day = MONTHS[day_first.group(2)], int(day_first.group(1))
        year = moment.year
        try:
            anchor = datetime(year, month, day)
        except ValueError:
            return "default", None
        if anchor < _midnight(moment) - timedelta(days=1):
            try:
                anchor = datetime(year + 1, month, day)
            except ValueError:
                return "default", None
        return "date", anchor

    # "on the 30th"
    ordinal = re.search(r"\bon the (\d{1,2})(?:st|nd|rd|th)\b", lowered)
    if ordinal:
        day = int(ordinal.group(1))
        anchor = None
        for offset in (0, 1):
            month = moment.month + offset
            year = moment.year + (1 if month > 12 else 0)
            month = month - 12 if month > 12 else month
            try:
                candidate = datetime(year, month, day)
            except ValueError:
                continue
            if candidate >= _midnight(moment):
                anchor = candidate
                break
        if anchor:
            return "date", anchor

    return "default", None
