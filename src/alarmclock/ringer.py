"""Making noise when an alarm fires.

Audio on the CLI is inherently platform-specific, so it lives behind one small
class. On Windows we use ``winsound.Beep``; elsewhere we fall back to the
terminal bell (``\\a``). Any failure degrades silently to the printed banner --
a missing sound device must never crash the alarm.

Output is ASCII-only on purpose: we cannot assume the terminal encoding is
UTF-8 (Windows consoles often are not), and a UnicodeEncodeError in the ring
path would be the worst possible time to crash.
"""

from __future__ import annotations

import platform
import sys
from typing import Callable, TextIO

from .models import Alarm

# Actions the ringer can report back to the scheduler.
DISMISS = "dismiss"
SNOOZE = "snooze"


class Ringer:
    def __init__(
        self,
        play_sound: bool = True,
        beeps: int = 3,
        stream: TextIO | None = None,
        input_fn: Callable[[str], str] | None = None,
    ):
        """
        :param play_sound: emit audible beeps (disable with ``--no-sound``).
        :param stream: where banners are written (defaults to stdout).
        :param input_fn: how to prompt for dismiss/snooze. ``None`` means
            non-interactive -- ring and auto-dismiss (correct for pipes/CI).
        """
        self.play_sound = play_sound
        self.beeps = beeps
        self.stream = stream or sys.stdout
        self.input_fn = input_fn

    def _beep(self) -> None:
        try:
            if platform.system() == "Windows":
                import winsound

                winsound.Beep(880, 350)
            else:
                self.stream.write("\a")
                self.stream.flush()
        except Exception:
            # A beep is best-effort; the visible banner is the real signal.
            pass

    def ring(self, alarm: Alarm) -> str:
        """Announce the alarm and return the chosen action (dismiss/snooze)."""
        label = alarm.label or "Alarm"
        self.stream.write(
            f"\n>>> ALARM {alarm.time.strftime('%H:%M')} - {label}\n"
        )
        self.stream.flush()

        if self.play_sound:
            for _ in range(self.beeps):
                self._beep()

        if self.input_fn is None:
            return DISMISS

        while True:
            try:
                choice = self.input_fn("    [d]ismiss / [s]nooze > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.stream.write("\n")
                return DISMISS
            if choice in ("", "d", "dismiss"):
                return DISMISS
            if choice in ("s", "snooze"):
                return SNOOZE
            self.stream.write("    (please type 'd' or 's')\n")
            self.stream.flush()
