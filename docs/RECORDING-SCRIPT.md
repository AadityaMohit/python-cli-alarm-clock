# Screen-recording narration script (~6-8 min)

The recording should show *how you think*, not just a demo. Narrate decisions,
not keystrokes. Suggested arc below — adapt to your own voice; don't read it
verbatim. Record with OBS Studio / Loom / the Windows Game Bar (Win+G).

> Tip: have `README.md`, `docs/DESIGN.md`, and a terminal open before you start.

---

## 0. Intro (30s)
- "Hi, I'm [name]. The task was an alarm clock as a Python CLI, no spec. I'll
  walk through how I framed it, the key engineering decisions, and how I
  validated it — I care more about those than feature count."

## 1. Framing the problem (60-90s) — open `docs/DESIGN.md §1`
- "With no spec, the first job is to find the decisions hidden in the brief."
- Talk through the decision table: **how it rings** (foreground watcher, not a
  daemon, and why), one-shot **and** recurring, JSON file for "no database",
  snooze in scope, **zero runtime dependencies**.
- "I used AI here as a thinking partner to surface these questions, then made
  the calls myself and wrote them down."

## 2. Architecture (60s) — open `docs/DESIGN.md §2` + the `src/alarmclock` tree
- "The spine of the design is separating a pure core from the I/O edges."
- Point at `scheduler.py` (pure brain), `clock.py` (the injectable seam that
  makes time testable), `store.py` (atomic writes), `ringer.py` (platform mess
  quarantined).

## 3. The interesting bug I designed against (90s) — `scheduler.py` + `DESIGN.md §3`
- "The decision I spent the most time on: detecting when an alarm is *due*."
- Explain the trap: a polling loop lands *inside* the minute, never exactly on
  `HH:MM:00`, so firing on a precomputed instant misses.
- Show the two mechanisms: strictly-future `next_ring_at` for display vs
  minute-matching + once-per-minute guard for firing. "I documented why they
  differ so nobody 'simplifies' it back into the bug."

## 4. Validate — prove it works (2-3 min) — terminal
Run these live and narrate:
```bash
python -m pytest                       # 57 green, <1s — "behaviour written down"
alarm set 07:30 --label "Wake up" --repeat weekdays
alarm set 6:45am --label Gym --repeat mon,wed,fri
alarm list                             # show the NEXT column
alarm set 99:99                         # rejected -> exit code 2, clear message
# the one that matters: set an alarm for THIS minute and run the watcher
alarm set <current HH:MM> --label "Fires now"
alarm run --no-sound                    # watch it print >>> ALARM ...
```
- Call out the subtlety live: the one-shot shows "next ring tomorrow" yet still
  fires this minute — the two-mechanism design agreeing in practice.
- Optionally: in a second terminal `alarm set` while `run` is active → "picked
  up live, no restart."

## 5. How I directed & reviewed the AI (45s) — `docs/AI-COLLABORATION.md`
- "AI drafted boilerplate and first-pass tests fast; I owned the problem
  definition, the architecture, catching the due-detection bug, and deciding
  what 'validated' means. Everything it produced I read and corrected."

## 6. Wrap (20s)
- "Conscious scope cuts are in DESIGN §6 — background daemon, custom sounds,
  timezones. Left out on purpose, not half-built. Thanks for watching."

---

### Checklist before you hit record
- [ ] `pip install -e ".[dev]"` already done so `pytest`/`alarm` resolve.
- [ ] Terminal font large enough to read.
- [ ] Mic tested; close noisy apps.
- [ ] Know the current time so your "fires now" alarm actually rings on camera.
