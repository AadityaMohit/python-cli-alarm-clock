from datetime import time

import pytest

from alarmclock.parsing import parse_repeat, parse_time


@pytest.mark.parametrize(
    "text,expected",
    [
        ("07:30", time(7, 30)),
        ("7:30", time(7, 30)),
        ("19:05", time(19, 5)),
        ("00:00", time(0, 0)),
        ("23:59", time(23, 59)),
        ("7:30am", time(7, 30)),
        ("7:30AM", time(7, 30)),
        ("12:00am", time(0, 0)),  # midnight
        ("12:00pm", time(12, 0)),  # noon
        ("11:45pm", time(23, 45)),
        ("7am", time(7, 0)),
        ("  08:15  ", time(8, 15)),
    ],
)
def test_parse_time_valid(text, expected):
    assert parse_time(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "25:00", "07:60", "noon", "7:30xm", "13:00pm", "-1:00", "abc"],
)
def test_parse_time_invalid(text):
    with pytest.raises(ValueError):
        parse_time(text)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", ()),
        ("   ", ()),
        ("daily", (0, 1, 2, 3, 4, 5, 6)),
        ("everyday", (0, 1, 2, 3, 4, 5, 6)),
        ("weekdays", (0, 1, 2, 3, 4)),
        ("weekends", (5, 6)),
        ("mon,wed,fri", (0, 2, 4)),
        ("fri,mon,mon", (0, 4)),  # sorted + de-duplicated
        ("monday,sunday", (0, 6)),
        ("MON, TUE", (0, 1)),  # case / whitespace tolerant
    ],
)
def test_parse_repeat_valid(text, expected):
    assert parse_repeat(text) == expected


@pytest.mark.parametrize("text", ["funday", "mon,blursday", "1,2,3"])
def test_parse_repeat_invalid(text):
    with pytest.raises(ValueError):
        parse_repeat(text)
