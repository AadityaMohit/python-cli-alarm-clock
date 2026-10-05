"""Parsing of user-supplied time and repeat strings.

Kept separate from the CLI so the rules are unit-tested in isolation and the
same parsers can be reused by any future front-end.
"""

from __future__ import annotations

import re
from datetime import time

from .models import WEEKDAYS

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([ap]m)?\s*$", re.IGNORECASE)

# Accept both three-letter and full weekday names.
_DAY_NAMES = {
    **{name: i for i, name in enumerate(WEEKDAYS)},
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_REPEAT_ALIASES = {
    "daily": tuple(range(7)),
    "everyday": tuple(range(7)),
    "all": tuple(range(7)),
    "weekdays": (0, 1, 2, 3, 4),
    "weekends": (5, 6),
}


def parse_time(text: str) -> time:
    """Parse '07:30', '7:30', '7:30am', '7am', '19:05' into a ``time``.

    Raises ``ValueError`` with an actionable message on bad input.
    """
    match = _TIME_RE.match(text or "")
    if not match:
        raise ValueError(
            f"invalid time {text!r}: use 24h 'HH:MM' (e.g. 07:30) or '7:30am'"
        )

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError(f"invalid 12-hour time {text!r}: hour must be 1-12")
        meridiem = meridiem.lower()
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        else:  # pm
            hour = 12 if hour == 12 else hour + 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"invalid time {text!r}: out of range")

    return time(hour, minute)


def parse_repeat(text: str) -> tuple[int, ...]:
    """Parse a repeat spec into sorted, de-duplicated weekday indices.

    Accepts aliases ('daily', 'weekdays', 'weekends') or a comma-separated list
    of day names ('mon,wed,fri'). Empty input means a one-shot alarm.
    """
    if not text or not text.strip():
        return ()

    key = text.strip().lower()
    if key in _REPEAT_ALIASES:
        return _REPEAT_ALIASES[key]

    days: set[int] = set()
    for token in key.split(","):
        token = token.strip()
        if not token:
            continue
        if token not in _DAY_NAMES:
            valid = ", ".join(WEEKDAYS)
            raise ValueError(
                f"invalid day {token!r}: use one of {valid}, or an alias "
                f"(daily, weekdays, weekends)"
            )
        days.add(_DAY_NAMES[token])

    return tuple(sorted(days))
