from datetime import time

from alarmclock.models import Alarm
from alarmclock.store import AlarmStore


def test_load_missing_file_is_empty(store: AlarmStore):
    assert store.load() == []


def test_round_trip_preserves_all_fields(store: AlarmStore):
    alarm = Alarm(
        time=time(6, 45),
        label="Gym",
        repeat=(0, 2, 4),
        enabled=False,
        id="abc123",
    )
    store.save([alarm])
    (loaded,) = store.load()
    assert loaded == alarm


def test_add_and_remove(store: AlarmStore):
    a = store.add(Alarm(time=time(7, 0)))
    b = store.add(Alarm(time=time(8, 0)))
    assert {x.id for x in store.load()} == {a.id, b.id}

    assert store.remove(a.id) is True
    assert [x.id for x in store.load()] == [b.id]
    assert store.remove("nope") is False


def test_set_enabled(store: AlarmStore):
    a = store.add(Alarm(time=time(7, 0)))
    assert store.set_enabled(a.id, False) is True
    assert store.load()[0].enabled is False
    assert store.set_enabled("nope", True) is False


def test_clear(store: AlarmStore):
    store.add(Alarm(time=time(7, 0)))
    store.add(Alarm(time=time(8, 0)))
    assert store.clear() == 2
    assert store.load() == []


def test_save_is_atomic_no_tempfiles_left(store: AlarmStore):
    store.add(Alarm(time=time(7, 0)))
    leftovers = list(store.path.parent.glob("*.tmp"))
    assert leftovers == []
