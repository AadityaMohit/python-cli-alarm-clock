"""Time source abstraction.

The scheduler depends on this `Clock` protocol rather than calling
``datetime.now()`` / ``time.sleep()`` directly. That single seam is what makes
the scheduling logic deterministically testable: tests inject a ``FakeClock``
and advance time by hand instead of waiting on the wall clock.
"""

from __future__ import annotations

import time as _time
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """A source of 'now' and a way to wait."""

    def now(self) -> datetime:
        ...

    def sleep(self, seconds: float) -> None:
        ...


class SystemClock:
    """Real wall-clock, used in production."""

    def now(self) -> datetime:
        return datetime.now()

    def sleep(self, seconds: float) -> None:
        _time.sleep(seconds)
