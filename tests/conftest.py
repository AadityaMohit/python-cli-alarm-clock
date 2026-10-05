"""Shared test fixtures and fakes."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from alarmclock.clock import Clock
from alarmclock.models import Alarm
from alarmclock.store import AlarmStore


class FakeClock(Clock):
    """A controllable clock. ``sleep`` advances virtual time instead of waiting."""

    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def sleep(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class RecordingRinger:
    """Stand-in for Ringer that records what rang and scripts snooze replies."""

    def __init__(self, actions=None):
        self.rung: list[Alarm] = []
        self._actions = list(actions or [])

    def ring(self, alarm: Alarm) -> str:
        self.rung.append(alarm)
        return self._actions.pop(0) if self._actions else "dismiss"


@pytest.fixture
def store(tmp_path) -> AlarmStore:
    return AlarmStore(tmp_path / "alarms.json")
