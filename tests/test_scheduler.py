from datetime import datetime, time, timedelta

from alarmclock.models import Alarm
from alarmclock.scheduler import Scheduler, next_ring_at

from conftest import FakeClock, RecordingRinger

# A fixed reference: Wednesday 2024-01-03, 08:00:00.
WED_0800 = datetime(2024, 1, 3, 8, 0, 0)


# --- next_ring_at: the pure scheduling brain --------------------------------


def test_one_shot_later_today():
    alarm = Alarm(time=time(9, 30))
    assert next_ring_at(alarm, WED_0800) == datetime(2024, 1, 3, 9, 30)


def test_one_shot_already_passed_rolls_to_tomorrow():
    alarm = Alarm(time=time(7, 30))  # earlier than 08:00
    assert next_ring_at(alarm, WED_0800) == datetime(2024, 1, 4, 7, 30)


def test_disabled_alarm_has_no_next():
    assert next_ring_at(Alarm(time=time(9, 0), enabled=False), WED_0800) is None


def test_recurring_picks_today_when_time_ahead():
    # Wednesday == weekday 2; alarm repeats on weekdays, 09:00 still ahead.
    alarm = Alarm(time=time(9, 0), repeat=(0, 1, 2, 3, 4))
    assert next_ring_at(alarm, WED_0800) == datetime(2024, 1, 3, 9, 0)


def test_recurring_skips_to_next_matching_day():
    # Repeats Mon/Fri only. From Wednesday 08:00 the next is Friday.
    alarm = Alarm(time=time(6, 0), repeat=(0, 4))
    assert next_ring_at(alarm, WED_0800) == datetime(2024, 1, 5, 6, 0)


def test_recurring_wraps_to_next_week():
    # Repeats Monday only; Wednesday -> next Monday (2024-01-08).
    alarm = Alarm(time=time(6, 0), repeat=(0,))
    assert next_ring_at(alarm, WED_0800) == datetime(2024, 1, 8, 6, 0)


# --- Scheduler.tick: firing, dedup, one-shot consumption, snooze ------------


def _scheduler(store, ringer, start):
    return Scheduler(store, ringer, clock=FakeClock(start), reload=True)


def test_tick_fires_due_alarm_once_per_minute(store):
    store.add(Alarm(time=time(8, 0), id="x", label="Standup"))
    ringer = RecordingRinger()
    sched = _scheduler(store, ringer, WED_0800)

    sched.tick(WED_0800)  # 08:00:00 -> fires
    sched.tick(WED_0800 + timedelta(seconds=30))  # still 08:00 -> no refire
    assert len(ringer.rung) == 1

    sched.tick(WED_0800 + timedelta(minutes=1))  # 08:01 -> not due
    assert len(ringer.rung) == 1


def test_one_shot_is_consumed_after_firing(store):
    store.add(Alarm(time=time(8, 0), id="x"))
    ringer = RecordingRinger()
    sched = _scheduler(store, ringer, WED_0800)

    sched.tick(WED_0800)
    assert store.load()[0].enabled is False  # disabled in the store
    # Next day at the same time it must not ring again.
    sched.tick(WED_0800 + timedelta(days=1))
    assert len(ringer.rung) == 1


def test_recurring_fires_on_each_matching_day(store):
    store.add(Alarm(time=time(8, 0), repeat=(2, 3), id="x"))  # Wed, Thu
    ringer = RecordingRinger()
    sched = _scheduler(store, ringer, WED_0800)

    sched.tick(WED_0800)  # Wed
    sched.tick(WED_0800 + timedelta(days=1))  # Thu
    sched.tick(WED_0800 + timedelta(days=2))  # Fri -> not in repeat
    assert len(ringer.rung) == 2


def test_snooze_reschedules_and_rings_again(store):
    store.add(Alarm(time=time(8, 0), id="x", label="Wake"))
    ringer = RecordingRinger(actions=["snooze"])  # snooze on first ring
    sched = Scheduler(
        store, ringer, clock=FakeClock(WED_0800), snooze_minutes=9
    )

    sched.tick(WED_0800)  # rings, user snoozes -> re-armed for 08:09
    assert len(ringer.rung) == 1
    sched.tick(WED_0800 + timedelta(minutes=5))  # too early
    assert len(ringer.rung) == 1
    sched.tick(WED_0800 + timedelta(minutes=9))  # snooze fires
    assert len(ringer.rung) == 2


def test_run_loop_fires_with_fake_clock(store):
    # Alarm two minutes out; poll once per minute for three ticks.
    store.add(Alarm(time=time(8, 2), id="x"))
    ringer = RecordingRinger()
    sched = Scheduler(
        store, ringer, clock=FakeClock(WED_0800), poll_interval=60.0
    )
    sched.run(max_ticks=3)  # 08:00, 08:01, 08:02
    assert len(ringer.rung) == 1
