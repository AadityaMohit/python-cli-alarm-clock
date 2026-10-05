# alarmclock

<!-- After pushing, replace OWNER/REPO below with your GitHub path so the CI badge goes live. -->
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Runtime deps](https://img.shields.io/badge/runtime%20dependencies-0-brightgreen)
![Tests](https://img.shields.io/badge/tests-57%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

A small, dependency-free alarm clock for the terminal. Set one-shot or
recurring alarms, then run a watcher that rings them when they are due.

```
$ alarm set 07:30 --label "Wake up" --repeat weekdays
Set alarm f34429bb for 07:30 [weekdays] "Wake up"
  next ring: Tue 07:30 (in 19h42m)

$ alarm list
ID        TIME   ON   REPEAT       LABEL              NEXT
----------------------------------------------------------------
f34429bb  07:30  yes  weekdays     Wake up            Tue 07:30 (in 19h42m)

$ alarm run
Watching 1 enabled alarm(s). Press Ctrl+C to stop.

>>> ALARM 07:30 - Wake up
    [d]ismiss / [s]nooze >
```

## Why it's built this way

This was a time-boxed exercise. The guiding principle was **right-sized
engineering**: a small, correct core with the seams a senior engineer would
insist on, and nothing speculative. The reasoning is written up in
[`docs/DESIGN.md`](docs/DESIGN.md); how AI was used to get there is in
[`docs/AI-COLLABORATION.md`](docs/AI-COLLABORATION.md).

Headline decisions:

- **Zero runtime dependencies** — standard library only. Trivial to install and
  audit; no supply-chain surface for a tool this small.
- **Foreground watcher, not a daemon** — `alarm run` is an explicit,
  observable process. No OS service plumbing, no silent background state.
- **Plain JSON file for storage** (per the "no database" constraint), written
  **atomically** so an interrupted write can't corrupt your alarms.
- **A pure scheduling core** (`next_ring_at`) separated from all I/O, behind an
  injectable `Clock`, so the time logic is tested deterministically without
  ever sleeping.

## Install

Requires Python 3.10+.

```bash
# from the repo root
python -m pip install -e .
```

This installs the `alarm` command. You can also run it without installing:

```bash
PYTHONPATH=src python -m alarmclock <command>
```

## Usage

| Command | What it does |
| --- | --- |
| `alarm set TIME [--label L] [--repeat R]` | Create an alarm. |
| `alarm list` | Show all alarms and when each next rings. |
| `alarm remove ID` | Delete an alarm. |
| `alarm enable ID` / `alarm disable ID` | Toggle an alarm without deleting it. |
| `alarm clear` | Remove all alarms. |
| `alarm run [--no-sound] [--snooze MIN] [--interval SEC]` | Watch and ring alarms. |

**Time formats:** `07:30`, `7:30`, `19:05`, or 12-hour `7:30am` / `11:45pm`.

**Repeat formats:** `daily`, `weekdays`, `weekends`, or a comma list such as
`mon,wed,fri` (3-letter or full day names, in any case). Omit `--repeat` for a
one-shot alarm that fires once and is then consumed.

**While `run` is active:**
- When an alarm rings in an interactive terminal, press `d` to dismiss or `s`
  to snooze (default 9 minutes, configurable with `--snooze`).
- In a non-interactive context (a pipe, CI, a background job), alarms
  auto-dismiss — the tool never blocks waiting for input it can't get.
- `run` re-reads the alarm file every tick, so you can `alarm set` in another
  terminal and the watcher picks it up live, without a restart.

## Where alarms are stored

Default: `~/.alarmclock/alarms.json`. Override with the `ALARMCLOCK_HOME`
environment variable, or per-command with `--store /path/to/alarms.json`
(handy for keeping separate alarm sets, and used throughout the tests).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest        # 57 tests, runs in well under a second
```

The suite covers input parsing (incl. edge cases like `12:00am`/`12:00pm`),
JSON round-tripping and atomic writes, the scheduling core (one-shot rollover,
recurring day-of-week selection, week wrap-around), and the end-to-end CLI.

## Project layout

```
src/alarmclock/
  models.py      # the immutable Alarm value type
  parsing.py     # time + repeat string parsing (reusable, pure)
  store.py       # JSON persistence with atomic writes
  clock.py       # Clock protocol + SystemClock (the testability seam)
  scheduler.py   # next_ring_at (pure) + the polling run loop
  ringer.py      # cross-platform sound + dismiss/snooze interaction
  cli.py         # argument parsing and command dispatch
tests/           # unit + end-to-end tests
docs/            # DESIGN.md, AI-COLLABORATION.md
```

## Known limitations / what I'd do next

See the end of [`docs/DESIGN.md`](docs/DESIGN.md). In short: the watcher must be
running for alarms to fire (by design — no daemon); audio is a simple beep; and
there's no timezone/DST handling beyond the host's local time. Each of these was
a conscious scope cut, not an oversight.

## License

MIT — see [`LICENSE`](LICENSE).
