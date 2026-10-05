"""Domain model: the Alarm.

An ``Alarm`` is deliberately immutable (``frozen=True``). Edits go through
``dataclasses.replace`` and produce a new value, which keeps the store logic
simple to reason about and avoids accidental shared-state mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import time

# Index matches datetime.weekday(): Monday == 0 ... Sunday == 6.
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class Alarm:
    """A single alarm.

    An empty ``repeat`` means a one-shot alarm (fires once at the next
    occurrence of ``time`` and is then consumed). A non-empty ``repeat`` is a
    recurring alarm that fires on each listed weekday.
    """

    time: time
    label: str = ""
    repeat: tuple[int, ...] = ()  # sorted, unique weekday indices
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def is_recurring(self) -> bool:
        return bool(self.repeat)

    def repeat_label(self) -> str:
        """Human-friendly description of the repeat schedule."""
        days = set(self.repeat)
        if not days:
            return "once"
        if days == set(range(7)):
            return "daily"
        if days == {0, 1, 2, 3, 4}:
            return "weekdays"
        if days == {5, 6}:
            return "weekends"
        return ",".join(WEEKDAYS[i] for i in self.repeat)
