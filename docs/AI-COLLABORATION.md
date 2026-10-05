# How I used AI on this exercise

The brief asked to see *how I direct AI, review its output, and validate the
result* — not just the code. This is an honest account of that.

## My working model

I treat an AI assistant as a fast, literal pair-programmer: excellent at
producing a first pass quickly, but it needs a human to **own the problem
definition, catch the subtle bugs, and decide what "done" means.** I stay the
engineer; the AI is leverage.

My loop for this task was: **frame → direct → review → validate → correct.**

## 1. Frame (before any code)

I didn't ask the AI to "build an alarm clock." I first used it as a thinking
partner to surface the *decisions hidden in the brief*: How does it ring — a
daemon or a foreground process? One-shot vs recurring? Where does state live
given "no database"? Is snooze in scope? I pushed back on answers that added
complexity without earning it (e.g. a background service) and settled on the
scope now written up in `DESIGN.md §1`. Defining the problem was the highest-
leverage step, so it got the most of my attention.

## 2. Direct

I gave specific, constraint-led instructions rather than open prompts — the
constraints *are* the senior input:

- "Standard library only. No runtime dependencies."
- "Separate a pure scheduling function from all I/O, behind an injectable clock,
  so it's testable without sleeping."
- "Atomic file writes — an interrupted save must not corrupt existing alarms."
- "ASCII-only output; don't assume a UTF-8 console on Windows."
- "Non-interactive contexts must auto-dismiss, never block on input."

Each of these is a decision I made and then handed down, not something I let the
model choose by default.

## 3. Review — where I caught the real issue

The most important moment was **not** accepting the obvious first design. The
natural implementation computes each alarm's next fire instant and fires when
`now` reaches it. Reviewing that against how a *polling* loop actually behaves, I
caught the bug: the loop lands a fraction of a second inside the target minute,
never exactly on it, so a strict "fire at the precomputed instant" check misses.

I split the design into two clearly-named mechanisms — a strictly-future
`next_ring_at` for display, and minute-matching with a once-per-minute guard for
firing — and documented *why they differ* so the next maintainer isn't tempted
to "simplify" them back into the bug. That's the kind of judgement the AI won't
reliably apply on its own; it's the reviewer's job.

Other review corrections: tightened the one-shot "consume after firing" path,
made the snooze re-arm in-memory rather than polluting the stored schedule, and
kept the CLI a thin dispatch layer so logic stayed in tested modules.

## 4. Validate — I trust behaviour, not claims

I didn't take "it works" on faith:

- Wrote the behaviour down as **57 tests** and ran them (green, <1s).
- Drove the **real CLI** end-to-end: set/list/remove, a rejected bad time
  returning exit code 2, and — the one that matters — set an alarm for the
  current minute, ran the watcher in a background job, and confirmed it actually
  printed `>>> ALARM 11:48 - Fires now`. The screen recording shows this.
- That live run also *confirmed the subtle design point*: the one-shot showed
  "next ring: tomorrow" (strictly-future `next_ring_at`) yet still fired this
  minute (minute-match). Seeing both behaviours agree was the validation that
  the two-mechanism split was correct.

## 5. What I owned vs. what the AI accelerated

- **Mine:** the problem definition and scope; the architecture and its seams;
  the decision to split due-detection; the scope cuts in `DESIGN.md §6`; what
  counts as validated.
- **AI-accelerated:** boilerplate (dataclass, argparse wiring, serialization),
  first-draft docstrings and tests, and quick iteration on wording — all read
  and corrected before being kept.

The through-line: AI made me faster, but every decision that a senior would be
accountable for, I made and can defend.
