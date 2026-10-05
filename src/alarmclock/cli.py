"""Command-line interface.

Thin by design: it parses arguments, delegates to the store / scheduler, and
formats output. All real logic lives in the tested modules. Every command
returns an exit code so the tool composes well in scripts.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional, Sequence

from . import __version__
from .models import Alarm
from .parsing import parse_repeat, parse_time
from .ringer import Ringer
from .scheduler import Scheduler, next_ring_at
from .store import AlarmStore, default_store_path


def _format_next(alarm: Alarm, now: datetime) -> str:
    target = next_ring_at(alarm, now)
    if target is None:
        return "disabled"
    delta = target - now
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    when = target.strftime("%a %H:%M")
    return f"{when} (in {hours}h{minutes:02d}m)"


def cmd_set(args: argparse.Namespace, store: AlarmStore) -> int:
    try:
        alarm = Alarm(
            time=parse_time(args.time),
            label=args.label or "",
            repeat=parse_repeat(args.repeat or ""),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    store.add(alarm)
    print(
        f"Set alarm {alarm.id} for {alarm.time:%H:%M} "
        f"[{alarm.repeat_label()}]"
        + (f' "{alarm.label}"' if alarm.label else "")
    )
    print(f"  next ring: {_format_next(alarm, datetime.now())}")
    return 0


def cmd_list(args: argparse.Namespace, store: AlarmStore) -> int:
    alarms = store.load()
    if not alarms:
        print("No alarms set. Add one with:  alarm set 07:30 --label 'Wake up'")
        return 0

    now = datetime.now()
    alarms.sort(key=lambda a: (a.time.hour, a.time.minute))
    header = f"{'ID':<9} {'TIME':<6} {'ON':<4} {'REPEAT':<12} {'LABEL':<18} NEXT"
    print(header)
    print("-" * len(header))
    for alarm in alarms:
        state = "yes" if alarm.enabled else "no"
        nxt = _format_next(alarm, now) if alarm.enabled else "-"
        label = (alarm.label[:15] + "...") if len(alarm.label) > 18 else alarm.label
        print(
            f"{alarm.id:<9} {alarm.time:%H:%M}  {state:<4} "
            f"{alarm.repeat_label():<12} {label:<18} {nxt}"
        )
    return 0


def cmd_remove(args: argparse.Namespace, store: AlarmStore) -> int:
    if store.remove(args.id):
        print(f"Removed alarm {args.id}")
        return 0
    print(f"error: no alarm with id {args.id!r}", file=sys.stderr)
    return 1


def _set_enabled(args: argparse.Namespace, store: AlarmStore, enabled: bool) -> int:
    if store.set_enabled(args.id, enabled):
        print(f"{'Enabled' if enabled else 'Disabled'} alarm {args.id}")
        return 0
    print(f"error: no alarm with id {args.id!r}", file=sys.stderr)
    return 1


def cmd_enable(args: argparse.Namespace, store: AlarmStore) -> int:
    return _set_enabled(args, store, True)


def cmd_disable(args: argparse.Namespace, store: AlarmStore) -> int:
    return _set_enabled(args, store, False)


def cmd_clear(args: argparse.Namespace, store: AlarmStore) -> int:
    count = store.clear()
    print(f"Cleared {count} alarm(s)")
    return 0


def cmd_run(args: argparse.Namespace, store: AlarmStore) -> int:
    interactive = sys.stdin.isatty()
    ringer = Ringer(
        play_sound=not args.no_sound,
        input_fn=input if interactive else None,
    )
    scheduler = Scheduler(
        store=store,
        ringer=ringer,
        poll_interval=args.interval,
        snooze_minutes=args.snooze,
    )

    count = len([a for a in store.load() if a.enabled])
    print(f"Watching {count} enabled alarm(s). Press Ctrl+C to stop.")
    if not interactive:
        print("(non-interactive: alarms auto-dismiss)")
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alarm",
        description="A small, dependency-free alarm clock for the terminal.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--store",
        default=None,
        help="path to the alarms file (default: ~/.alarmclock/alarms.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="create an alarm")
    p_set.add_argument("time", help="24h HH:MM (e.g. 07:30) or 12h (e.g. 7:30am)")
    p_set.add_argument("--label", "-l", help="a name for the alarm")
    p_set.add_argument(
        "--repeat",
        "-r",
        help="daily | weekdays | weekends | comma list (e.g. mon,wed,fri)",
    )
    p_set.set_defaults(func=cmd_set)

    p_list = sub.add_parser("list", help="list all alarms")
    p_list.set_defaults(func=cmd_list)

    p_remove = sub.add_parser("remove", help="delete an alarm by id")
    p_remove.add_argument("id")
    p_remove.set_defaults(func=cmd_remove)

    p_enable = sub.add_parser("enable", help="enable an alarm by id")
    p_enable.add_argument("id")
    p_enable.set_defaults(func=cmd_enable)

    p_disable = sub.add_parser("disable", help="disable an alarm by id")
    p_disable.add_argument("id")
    p_disable.set_defaults(func=cmd_disable)

    p_clear = sub.add_parser("clear", help="remove all alarms")
    p_clear.set_defaults(func=cmd_clear)

    p_run = sub.add_parser("run", help="watch alarms and ring them when due")
    p_run.add_argument("--no-sound", action="store_true", help="banner only, no beeps")
    p_run.add_argument(
        "--snooze", type=int, default=9, metavar="MIN", help="snooze length (default 9)"
    )
    p_run.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="SEC",
        help="poll interval in seconds (default 1.0)",
    )
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = AlarmStore(args.store or default_store_path())
    try:
        return args.func(args, store)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
