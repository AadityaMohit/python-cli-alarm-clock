"""The scheduling core.

Two concerns, kept apart on purpose:

* ``next_ring_at`` -- a pure function answering "when will this alarm next
  ring?" Used to show the user feedback and fully unit-tested without a clock.

* ``Scheduler`` -- the polling loop. On each tick it fires alarms whose
  scheduled minute has arrived, de-duplicates so an alarm fires at most once per
  minute, consumes one-shots, honours snooze, and re-reads the store so alarms
  added in another terminal are picked up live.

Firing is decided by matching the current HH:MM (and weekday, for recurring
alarms), not by ``next_ring_at``: a polling clock lands *inside* the target
minute, never exactly on its first second, so minute-matching is the robust
rule. ``next_ring_at`` is strictly-future and would skip an exactly-due alarm.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .clock import Clock, SystemClock
from .models import Alarm
from .ringer import SNOOZE, Ringer
from .store import AlarmStore


def next_ring_at(alarm: Alarm, now: datetime) -> Optional[datetime]:
    """Next datetime at which ``alarm`` should ring, strictly after ``now``.

    Returns ``None`` for a disabled alarm. Recurring alarms search up to a week
    ahead for the next matching weekday; one-shots fire today if the time is
    still ahead, otherwise tomorrow.
    """
    if not alarm.enabled:
        return None

    if alarm.is_recurring:
        for offset in range(0, 8):
            day = (now + timedelta(days=offset)).date()
            if day.weekday() in alarm.repeat:
                candidate = datetime.combine(day, alarm.time)
                if candidate > now:
                    return candidate
        return None

    candidate = datetime.combine(now.date(), alarm.time)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class Scheduler:
    def __init__(
        self,
        store: AlarmStore,
        ringer: Ringer,
        clock: Clock | None = None,
        poll_interval: float = 1.0,
        snooze_minutes: int = 9,
        reload: bool = True,
    ):
        self.store = store
        self.ringer = ringer
        self.clock = clock or SystemClock()
        self.poll_interval = poll_interval
        self.snooze_minutes = snooze_minutes
        self.reload = reload

        self._alarms: list[Alarm] = []
        self._snoozes: dict[int, tuple[datetime, Alarm]] = {}
        self._snooze_counter = 0
        # alarm id -> the minute (datetime truncated) it last fired, so a
        # second-by-second poll fires each alarm only once per minute.
        self._last_fired: dict[str, datetime] = {}

    def _current_alarms(self) -> list[Alarm]:
        if self.reload or not self._alarms:
            self._alarms = self.store.load()
        return self._alarms

    @staticmethod
    def _is_due(alarm: Alarm, now: datetime) -> bool:
        if not alarm.enabled:
            return False
        if (now.hour, now.minute) != (alarm.time.hour, alarm.time.minute):
            return False
        if alarm.is_recurring and now.weekday() not in alarm.repeat:
            return False
        return True

    def _fire(self, alarm: Alarm) -> None:
        action = self.ringer.ring(alarm)
        if action == SNOOZE:
            self._snooze_counter += 1
            self._snoozes[self._snooze_counter] = (
                self.clock.now() + timedelta(minutes=self.snooze_minutes),
                alarm,
            )

    def tick(self, now: datetime) -> list[Alarm]:
        """Process a single scheduler tick; return the alarms that fired.

        Separated from ``run`` so the firing logic can be exercised with a fake
        clock -- no sleeping, no infinite loop.
        """
        fired: list[Alarm] = []
        minute = now.replace(second=0, microsecond=0)

        # Snoozes are time-specific; fire once their moment has arrived.
        for sid, (ring_at, alarm) in sorted(
            self._snoozes.items(), key=lambda kv: kv[1][0]
        ):
            if now >= ring_at:
                self._snoozes.pop(sid, None)
                self._fire(alarm)
                fired.append(alarm)

        for alarm in self._current_alarms():
            if not self._is_due(alarm, now):
                continue
            if self._last_fired.get(alarm.id) == minute:
                continue
            self._last_fired[alarm.id] = minute
            self._fire(alarm)
            fired.append(alarm)
            if not alarm.is_recurring:
                # Consume the one-shot so it never rings again.
                self.store.set_enabled(alarm.id, False)
                self._alarms = self.store.load()

        return fired

    def run(self, max_ticks: Optional[int] = None) -> None:
        """Main loop. ``max_ticks`` bounds the loop in tests; ``None`` = forever."""
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            self.tick(self.clock.now())
            self.clock.sleep(self.poll_interval)
            ticks += 1
