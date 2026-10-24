"""The NYSE calendar (TODO 2.1a): each holiday's rule at its edge cases, Good Friday, Juneteenth, the special closures, year counts.

Every date below was checked by hand against a wall calendar; the year counts are weekdays minus closures:
2023 starts on a Sunday, so 260 weekdays; 10 holidays (1 January fell on a Sunday and moved to the 2nd) gives 250.
"""
from datetime import date

import pytest

from neonrain.harness.market import check_calendar
from neonrain.universe import calendar as nyse


def shut(day: date) -> bool:
    """True when the exchange was closed on a weekday."""
    return day.weekday() < 5 and day not in nyse.sessions(day.year, day.year)


def test_weekends_are_closed_and_output_is_ascending() -> None:
    days = nyse.sessions(2023, 2023)
    assert all(day.weekday() < 5 for day in days)
    assert days == sorted(set(days))
    check_calendar(days)


EASTERS = (  # Western Easter Sunday as month-day, from printed tables: every year 1998-2030, and a spread beyond
    "1998 4-12,1999 4-4,2000 4-23,2001 4-15,2002 3-31,2003 4-20,2004 4-11,2005 3-27,2006 4-16,2007 4-8,2008 3-23,"
    "2009 4-12,2010 4-4,2011 4-24,2012 4-8,2013 3-31,2014 4-20,2015 4-5,2016 3-27,2017 4-16,2018 4-1,2019 4-21,"
    "2020 4-12,2021 4-4,2022 4-17,2023 4-9,2024 3-31,2025 4-20,2026 4-5,2027 3-28,2028 4-16,2029 4-1,2030 4-21,"
    "1818 3-22,2285 3-22,1943 4-25,1954 4-18,1981 4-19,1961 4-2,1900 4-15,2100 3-28,2038 4-25"
).split(",")


@pytest.mark.parametrize("entry", EASTERS)
def test_easter(entry: str) -> None:
    year, monthday = entry.split()
    month, day = monthday.split("-")
    assert nyse.easter(int(year)) == date(int(year), int(month), int(day))


def oudin(year: int) -> date:
    """Easter by Oudin's 1940 algorithm, a different computation from the module's, for the cross-check below."""
    c, n = year // 100, year % 19
    k = (c - 17) // 25
    i = c - c // 4 - (c - k) // 3 + 19 * n + 15
    i = i % 30
    i = i - (i // 28) * (1 - (i // 28) * (29 // (i + 1)) * ((21 - n) // 11))
    j = (year + year // 4 + i + 2 - c + c // 4) % 7
    month_day = i - j + 28
    month = 3 + (i - j + 40) // 44
    return date(year, month, month_day - 31 * (month // 4))


def test_easter_agrees_with_a_second_algorithm_from_1583_to_2600() -> None:
    for year in range(1583, 2601):
        assert nyse.easter(year) == oudin(year), year


@pytest.mark.parametrize("day", [date(2000, 4, 21), date(2011, 4, 22), date(2015, 4, 3), date(2024, 3, 29), date(2026, 4, 3)])
def test_good_friday_is_closed(day: date) -> None:
    assert shut(day) and nyse.holidays(day.year)[day] == "Good Friday"


def test_saturday_new_years_day_closes_nothing() -> None:
    assert "New Year's Day" not in nyse.holidays(2022).values()
    assert nyse.sessions(2022, 2022)[0] == date(2022, 1, 3)
    assert date(2021, 12, 31) in nyse.sessions(2021, 2021)


@pytest.mark.parametrize("day", [date(2006, 1, 2), date(2012, 1, 2), date(2023, 1, 2)])
def test_sunday_new_years_day_moves_to_monday(day: date) -> None:
    assert shut(day) and nyse.holidays(day.year)[day] == "New Year's Day"


def test_new_years_day_on_a_weekday() -> None:
    assert shut(date(2021, 1, 1)) and shut(date(2025, 1, 1)) and shut(date(2024, 1, 1))


@pytest.mark.parametrize("day", [date(2009, 7, 3), date(2020, 7, 3), date(2026, 7, 3), date(2010, 7, 5), date(2021, 7, 5), date(2023, 7, 4)])
def test_independence_day_observance(day: date) -> None:
    assert shut(day)


@pytest.mark.parametrize("day", [date(2009, 7, 6), date(2020, 7, 6), date(2010, 7, 2), date(2021, 7, 2), date(2023, 7, 3)])
def test_independence_day_neighbours_are_open(day: date) -> None:
    assert not shut(day)


@pytest.mark.parametrize("day", [date(2004, 12, 24), date(2010, 12, 24), date(2005, 12, 26), date(2011, 12, 26), date(2021, 12, 24), date(2022, 12, 26)])
def test_christmas_observance(day: date) -> None:
    assert shut(day) and nyse.holidays(day.year)[day] == "Christmas Day"


def test_christmas_neighbours_are_open() -> None:
    assert not shut(date(2004, 12, 27)) and not shut(date(2005, 12, 23)) and not shut(date(2021, 12, 31))


@pytest.mark.parametrize("day,name", [
    (date(1998, 1, 19), "Martin Luther King Jr. Day"), (date(2024, 1, 15), "Martin Luther King Jr. Day"),
    (date(2024, 2, 19), "Washington's Birthday"), (date(2015, 2, 16), "Washington's Birthday"),
    (date(2024, 5, 27), "Memorial Day"), (date(2020, 5, 25), "Memorial Day"), (date(2019, 5, 27), "Memorial Day"),
    (date(2023, 9, 4), "Labor Day"), (date(2022, 9, 5), "Labor Day"),
    (date(2023, 11, 23), "Thanksgiving Day"), (date(2021, 11, 25), "Thanksgiving Day"), (date(2020, 11, 26), "Thanksgiving Day"),
])
def test_floating_holidays(day: date, name: str) -> None:
    assert nyse.holidays(day.year)[day] == name and shut(day)


def test_fixed_holiday_names() -> None:
    assert nyse.holidays(2023)[date(2023, 7, 4)] == "Independence Day"
    assert nyse.holidays(2023)[date(2023, 6, 19)] == "Juneteenth"
    assert nyse.holidays(2023)[date(2023, 12, 25)] == "Christmas Day"


def test_the_neighbours_of_floating_holidays_are_open() -> None:
    assert not shut(date(2024, 5, 28)) and not shut(date(2023, 11, 24)) and not shut(date(2024, 5, 20))


def test_juneteenth_from_2022_only() -> None:
    assert not shut(date(2021, 6, 18)) and not shut(date(2020, 6, 19)) and not shut(date(2021, 6, 21))
    assert shut(date(2022, 6, 20)) and not shut(date(2022, 6, 17))  # Sunday the 19th moves to Monday
    assert shut(date(2023, 6, 19)) and shut(date(2024, 6, 19)) and shut(date(2025, 6, 19))
    assert shut(date(2027, 6, 18))  # Saturday the 19th moves to Friday


@pytest.mark.parametrize("day,why", [
    (date(2001, 9, 11), "September 11"), (date(2001, 9, 14), "September 11"), (date(2012, 10, 29), "Sandy"),
    (date(2012, 10, 30), "Sandy"), (date(2004, 6, 11), "Reagan"), (date(2007, 1, 2), "Ford"),
    (date(2018, 12, 5), "Bush"), (date(2025, 1, 9), "Carter"),
])
def test_special_closures(day: date, why: str) -> None:
    assert shut(day) and why in nyse.closures(day.year)[day]


def test_special_closure_edges_are_open() -> None:
    assert not shut(date(2001, 9, 10)) and not shut(date(2001, 9, 17))
    assert not shut(date(2012, 10, 26)) and not shut(date(2012, 10, 31))
    assert not shut(date(2025, 1, 8)) and not shut(date(2025, 1, 10)) and not shut(date(2007, 1, 3))


def test_special_closures_are_weekdays_apart_from_regular_holidays() -> None:
    for day in nyse.SPECIAL_CLOSURES:
        assert day.weekday() < 5 and day not in nyse.holidays(day.year)


@pytest.mark.parametrize("year,count", [(2001, 248), (2012, 250), (2021, 252), (2022, 251), (2023, 250), (2024, 252), (2025, 250), (2026, 251)])
def test_sessions_per_year(year: int, count: int) -> None:
    assert len(nyse.sessions(year, year)) == count


def test_sessions_span_years() -> None:
    assert len(nyse.sessions(2023, 2024)) == 250 + 252
    assert nyse.sessions(2000, 2026)[0] == date(2000, 1, 3)
    assert nyse.sessions(2000, 2026)[-1] == date(2026, 12, 31)


def test_years_before_the_rules_are_refused() -> None:
    with pytest.raises(ValueError, match="1997, 2000"):
        nyse.sessions(nyse.FIRST_YEAR - 1, 2000)
    with pytest.raises(ValueError):
        nyse.sessions(2005, 2004)
    assert nyse.sessions(nyse.FIRST_YEAR, nyse.FIRST_YEAR)[0] == date(1998, 1, 2)
