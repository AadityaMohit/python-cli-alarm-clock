# Design notes

This document captures the thinking behind the build: how I turned a one-line
brief ("build an alarm clock as a Python CLI") into a defined problem, the
decisions I made, the trade-offs behind them, and what I deliberately left out.

## 1. Framing the problem

The brief is intentionally open. The first job is to turn it into something
specific enough to build and judge. I wrote down the questions a real spec would
answer, and chose a defensible default for each:

| Question | Decision | Rationale |
| --- | --- | --- |
| How does an alarm *actually ring*? Daemon, OS service, or foreground process? | **Foreground watcher** (`alarm run`). | A visible, Ctrl-C-able process. No OS-specific service installation, no hidden background state. Honest about the fact that *something has to be running* for an alarm to fire. |
| One-shot alarms, recurring, or both? | **Both.** | A one-shot-only alarm clock is a toy; recurring (weekdays/weekends/specific days) is what makes it useful, and the extra logic is small and testable. |
| Where does state live? ("no database") | **A single JSON file.** | Tiny data, human-readable, no dependency. Atomic writes give us crash-safety without a DB. |
| Snooze? | **Yes, lightweight.** | It's the one feature people actually associate with an alarm clock. Implemented in-memory in the watcher — no schema impact. |
| Third-party libraries? | **None at runtime.** | For a tool this small, stdlib `argparse` is enough and zero-dep means trivial install and nothing to audit. `pytest` is a dev-only dependency. |

### Scope: MoSCoW

- **Must:** set an alarm; it rings at the right time; list alarms; persistence
  across runs; works on the reviewer's machine first try.
- **Should:** recurring schedules; remove/enable/disable; snooze; clear error
  messages; tests for the logic that's easy to get wrong.
- **Could:** live reload of the alarm file; 12-hour time input; configurable
  snooze/poll interval.
- **Won't (this round):** real daemon/background service, custom sound files,
  timezones/DST, a TUI. Called out in §6 as conscious cuts.

## 2. Architecture

The design separates a **pure core** from the **I/O edges**, so the logic that's
worth testing can be tested without mocking the world.

```
cli.py ──▶ store.py ──▶ alarms.json     (persistence edge)
   │
   └─────▶ scheduler.py                 (pure brain: next_ring_at)
              │   └── clock.py           (time edge, injectable)
              └── ringer.py              (sound/interaction edge)
                    models.py            (Alarm value type)
                    parsing.py           (pure input parsing)
```

Module responsibilities:

- **`models.py`** — an immutable `Alarm` (`frozen=True`). Immutability keeps the
  store logic simple: edits produce new values, so there's no shared mutable
  state to reason about.
- **`parsing.py`** — pure functions that turn user strings into domain types.
  Separated from the CLI so the fiddly rules (12-hour `am/pm`, day aliases) are
  unit-tested directly.
- **`store.py`** — load/save plus small mutators. Writes are **atomic**
  (temp file + `os.replace`): an interrupted save can never corrupt the existing
  alarm list.
- **`clock.py`** — a `Clock` protocol with `SystemClock` for production. This
  single seam is what makes scheduling deterministically testable.
- **`scheduler.py`** — the heart. `next_ring_at` is a **pure function**; the
  `Scheduler` loop is a thin wrapper around it.
- **`ringer.py`** — all the platform- and terminal-specific messiness (audio,
  interactive prompt) quarantined in one place.
- **`cli.py`** — argument parsing and dispatch only; every command returns an
  exit code so the tool scripts cleanly.

## 3. The decision I spent the most time on: how to detect "due"

My first instinct was to make `next_ring_at` do everything: compute each
alarm's next fire time and fire when we reach it. Writing it, I found the
sharp edge: a polling loop never lands *exactly* on `HH:MM:00`. It lands a
fraction of a second *inside* the target minute. If "fire" means "now equals the
precomputed instant," the alarm is missed.

So I split the responsibility into two clearly-named mechanisms:

- **`next_ring_at(alarm, now)`** is **strictly future** — it answers "when
  next?" for display ("next ring: Tue 07:30"). Strictly-future is the right
  semantics for that question.
- **Firing** is decided by **minute-matching** in `Scheduler._is_due`: the
  current `HH:MM` equals the alarm's, and the weekday matches for recurring
  alarms. A per-alarm "last fired minute" guard means each alarm fires **once
  per minute** no matter how fast we poll.

This is deliberately documented in `scheduler.py`, because the two functions
look like they should be the same and a future maintainer will wonder why
they aren't. Having both lets me assert the subtle behaviour in tests: a
one-shot set for the *current* minute still fires this minute, even though
`next_ring_at` already reports tomorrow.

## 4. Correctness concerns I designed against

- **Double-firing.** The per-minute guard (`_last_fired`) plus consuming
  one-shots on fire prevents an alarm ringing twice.
- **Crash-safe writes.** Atomic replace in `store.save`, verified by a test
  that asserts no `.tmp` files are left behind.
- **Never crash in the ring path.** Audio is best-effort — any failure
  (no sound device, headless CI) degrades to the printed banner. Output is
  ASCII-only because we can't assume a UTF-8 console on Windows, and a
  `UnicodeEncodeError` while ringing would be the worst possible failure.
- **Non-interactive safety.** `run` checks `stdin.isatty()`; in a pipe/CI/job it
  auto-dismisses instead of blocking forever on input it will never receive.
- **Bad input is a clear error, not a traceback.** Parsing raises `ValueError`
  with an actionable message; the CLI maps it to a non-zero exit code.

## 5. Testing strategy

57 tests, running in under a second, with no real sleeping:

- **Parsing** — valid forms and the edges that bite (`12:00am` = midnight,
  `12:00pm` = noon, out-of-range, bad day names).
- **Store** — round-trip fidelity, add/remove/enable/clear, no temp-file litter.
- **Scheduler** — `next_ring_at` across one-shot rollover, recurring day
  selection, and week wrap-around; and the `Scheduler` loop driven by a
  `FakeClock` to prove once-per-minute firing, one-shot consumption, recurring
  repetition, and snooze re-arming — all in virtual time.
- **CLI** — `main()` driven exactly as a user would, including exit codes.

The `FakeClock` (its `sleep` advances virtual time) is why the whole suite is
fast and deterministic: tests fast-forward through days without waiting.

## 6. Limitations & what I'd do next

Conscious scope cuts, roughly in the order I'd pick them up:

1. **Background operation.** Today the watcher must be running. Next step: a
   `--detach` mode or an OS-native scheduler integration (launchd / Task
   Scheduler / systemd), chosen per-platform.
2. **Richer sound.** Custom audio files and a continuous ring until dismissed
   (needs a non-blocking input loop or a worker thread so beeping and the
   prompt coexist).
3. **Timezones / DST.** Everything is host local time. A recurring 07:30 alarm
   across a DST change deserves an explicit, tested policy.
4. **Concurrency on the store.** Two processes writing at once is currently
   last-writer-wins; file locking would make it safe.

None of these were needed to demonstrate a correct, well-structured alarm
clock, so they were left out on purpose rather than half-built.
