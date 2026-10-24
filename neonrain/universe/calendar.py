"""The NYSE trading calendar, derived by rule (TODO 2.1a, J-033): weekends, holidays, special closures.

Pure: years in, dates out; no clock, no network, no data file. `sessions` is the harness's `calendar` input
(docs/HARNESS.md): an ascending list of `date`s. Whole days only: an early close is still a session and is not
recorded. The rules are sure from FIRST_YEAR (1998, the first Martin Luther King Jr. Day) and are not claimed
before it. Each rule holds only in the years it held (Juneteenth from 2022).
"""
from datetime import date, timedelta

FIRST_YEAR = 1998
JUNETEENTH_FROM = 2022

SPECIAL_CLOSURES: dict[date, str] = {
    date(2001, 9, 11): "September 11 attacks",
    date(2001, 9, 12): "September 11 attacks",
    date(2001, 9, 13): "September 11 attacks",
    date(2001, 9, 14): "September 11 attacks",
    date(2004, 6, 11): "national day of mourning, Ronald Reagan",
    date(2007, 1, 2): "national day of mourning, Gerald Ford",
    date(2012, 10, 29): "Hurricane Sandy",
    date(2012, 10, 30): "Hurricane Sandy",
    date(2018, 12, 5): "national day of mourning, George H. W. Bush",
    date(2025, 1, 9): "national day of mourning, Jimmy Carter",
}


def easter(year: int) -> date:
    """Western Easter Sunday (the anonymous Gregorian algorithm, Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (b + 8) // 25
    h = (b - g + 1) // 3
    i = (19 * a + b - d - h + 15) % 30
    k, m = c // 4, c % 4
    el = (32 + 2 * e + 2 * k - i - m) % 7
    n = (a + 11 * i + 22 * el) // 451
    month = (i + el - 7 * n + 114) // 31
    return date(year, month, (i + el - 7 * n + 114) % 31 + 1)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th (1-based) given weekday (Monday 0) of a month."""
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def memorial_day(year: int) -> date:
    """The last Monday of May."""
    end = date(year, 5, 31)
    return end - timedelta(days=end.weekday())


def observed(day: date) -> date | None:
    """Where the NYSE observes a fixed-date holiday: Saturday to Friday, Sunday to Monday (Rule 7.2)."""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def new_years_day(year: int) -> date | None:
    """January 1 observed; a Saturday one is not moved to the Friday (31 December of the year before)."""
    day = date(year, 1, 1)
    return None if day.weekday() == 5 else observed(day)


def holidays(year: int) -> dict[date, str]:
    """The regular holidays observed in a year, with names (a Saturday 1 January is observed on none)."""
    found = {
        nth_weekday(year, 1, 0, 3): "Martin Luther King Jr. Day",
        nth_weekday(year, 2, 0, 3): "Washington's Birthday",
        easter(year) - timedelta(days=2): "Good Friday",
        memorial_day(year): "Memorial Day",
        observed(date(year, 7, 4)): "Independence Day",
        nth_weekday(year, 9, 0, 1): "Labor Day",
        nth_weekday(year, 11, 3, 4): "Thanksgiving Day",
        observed(date(year, 12, 25)): "Christmas Day",
    }
    if new_years_day(year) is not None:
        found[new_years_day(year)] = "New Year's Day"
    if year >= JUNETEENTH_FROM:
        found[observed(date(year, 6, 19))] = "Juneteenth"
    return found


def closures(year: int) -> dict[date, str]:
    """Every weekday the exchange was closed in a year: regular holidays and special closures, with reasons."""
    found = {day: why for day, why in SPECIAL_CLOSURES.items() if day.year == year}
    return {**found, **holidays(year)}


def sessions(first_year: int, last_year: int) -> list[date]:
    """The trading sessions of first_year through last_year inclusive, ascending."""
    if not FIRST_YEAR <= first_year <= last_year:
        raise ValueError(f"years must satisfy {FIRST_YEAR} <= first_year <= last_year, got {first_year}, {last_year}")
    shut = {day for year in range(first_year, last_year + 1) for day in closures(year)}
    span = (date(last_year, 12, 31) - date(first_year, 1, 1)).days + 1
    days = (date(first_year, 1, 1) + timedelta(days=d) for d in range(span))
    return [day for day in days if day.weekday() < 5 and day not in shut]
