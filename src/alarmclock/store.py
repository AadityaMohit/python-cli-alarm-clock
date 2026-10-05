"""Persistence.

Alarms are stored as a JSON array in a single file. A plain file is chosen
deliberately over a database (per the exercise constraints, and because the
data is tiny and human-inspectable). Writes are atomic: we write to a temp file
and ``os.replace`` it into place, so an interrupted write can never corrupt the
existing alarm list.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import time
from pathlib import Path

from .models import WEEKDAYS, Alarm


def default_store_path() -> Path:
    """Where alarms live by default.

    Honours ``ALARMCLOCK_HOME`` (useful for tests and for running isolated
    instances); otherwise falls back to ``~/.alarmclock/alarms.json``.
    """
    base = os.environ.get("ALARMCLOCK_HOME")
    root = Path(base) if base else Path.home() / ".alarmclock"
    return root / "alarms.json"


def _to_dict(alarm: Alarm) -> dict:
    return {
        "id": alarm.id,
        "time": alarm.time.strftime("%H:%M"),
        "label": alarm.label,
        "repeat": [WEEKDAYS[i] for i in alarm.repeat],
        "enabled": alarm.enabled,
    }


def _from_dict(data: dict) -> Alarm:
    hour, minute = (int(part) for part in data["time"].split(":"))
    repeat = tuple(sorted(WEEKDAYS.index(name) for name in data.get("repeat", [])))
    return Alarm(
        id=data["id"],
        time=time(hour, minute),
        label=data.get("label", ""),
        repeat=repeat,
        enabled=data.get("enabled", True),
    )


class AlarmStore:
    """Load/save alarms with a few convenience mutators."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> list[Alarm]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"could not read alarms from {self.path}: {exc}") from exc
        return [_from_dict(item) for item in raw]

    def save(self, alarms: list[Alarm]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([_to_dict(a) for a in alarms], indent=2)
        # Atomic replace: write to a sibling temp file, then rename.
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, self.path)
        except BaseException:
            # Best-effort cleanup; never leave a stray temp file behind.
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise

    # --- convenience mutators (load / modify / save) ---------------------

    def add(self, alarm: Alarm) -> Alarm:
        alarms = self.load()
        alarms.append(alarm)
        self.save(alarms)
        return alarm

    def remove(self, alarm_id: str) -> bool:
        alarms = self.load()
        kept = [a for a in alarms if a.id != alarm_id]
        if len(kept) == len(alarms):
            return False
        self.save(kept)
        return True

    def set_enabled(self, alarm_id: str, enabled: bool) -> bool:
        from dataclasses import replace

        alarms = self.load()
        found = False
        for i, alarm in enumerate(alarms):
            if alarm.id == alarm_id:
                alarms[i] = replace(alarm, enabled=enabled)
                found = True
                break
        if found:
            self.save(alarms)
        return found

    def clear(self) -> int:
        count = len(self.load())
        self.save([])
        return count
