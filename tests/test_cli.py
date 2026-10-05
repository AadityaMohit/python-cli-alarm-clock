"""End-to-end CLI tests driving main() exactly as a user would."""

from alarmclock.cli import main
from alarmclock.store import AlarmStore


def run(args, store_path):
    return main(["--store", str(store_path), *args])


def test_set_list_remove_flow(tmp_path, capsys):
    path = tmp_path / "alarms.json"

    assert run(["set", "07:30", "--label", "Wake up", "--repeat", "weekdays"], path) == 0
    out = capsys.readouterr().out
    assert "Set alarm" in out and "weekdays" in out

    (alarm,) = AlarmStore(path).load()
    assert alarm.label == "Wake up"

    assert run(["list"], path) == 0
    assert "07:30" in capsys.readouterr().out

    assert run(["remove", alarm.id], path) == 0
    assert run(["list"], path) == 0
    assert "No alarms set" in capsys.readouterr().out


def test_set_rejects_bad_time(tmp_path, capsys):
    path = tmp_path / "alarms.json"
    assert run(["set", "99:99"], path) == 2
    assert "error" in capsys.readouterr().err


def test_remove_unknown_id_errors(tmp_path, capsys):
    path = tmp_path / "alarms.json"
    assert run(["remove", "deadbeef"], path) == 1
    assert "no alarm" in capsys.readouterr().err


def test_enable_disable(tmp_path, capsys):
    path = tmp_path / "alarms.json"
    run(["set", "07:30"], path)
    capsys.readouterr()
    alarm_id = AlarmStore(path).load()[0].id

    assert run(["disable", alarm_id], path) == 0
    assert AlarmStore(path).load()[0].enabled is False
    assert run(["enable", alarm_id], path) == 0
    assert AlarmStore(path).load()[0].enabled is True
