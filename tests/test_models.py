from datetime import time

from alarmclock.models import Alarm


def test_one_shot_is_not_recurring():
    alarm = Alarm(time=time(7, 30))
    assert not alarm.is_recurring
    assert alarm.repeat_label() == "once"


def test_repeat_labels():
    assert Alarm(time=time(7, 0), repeat=tuple(range(7))).repeat_label() == "daily"
    assert Alarm(time=time(7, 0), repeat=(0, 1, 2, 3, 4)).repeat_label() == "weekdays"
    assert Alarm(time=time(7, 0), repeat=(5, 6)).repeat_label() == "weekends"
    assert Alarm(time=time(7, 0), repeat=(0, 2, 4)).repeat_label() == "mon,wed,fri"


def test_ids_are_unique():
    a, b = Alarm(time=time(7, 0)), Alarm(time=time(7, 0))
    assert a.id != b.id
