"""The two periods a WIKI result is reported for (R-026, NR-F-03): the date that divides them, kept in one place.

WIKI holds no ticker leaving before 2014-04-01, so a result for the years before is survivor-only (an optimistic
upper bound) and one from that date is closer to honest. Code that splits a result by period uses BOUNDARY, never
its own copy of the date; docs/RESULTS.md names the periods in its Period column.
"""
from datetime import date

# Decision: R-026 (b); finding NR-F-03: the first date of the second period, the earliest last date of any WIKI ticker.
BOUNDARY = date(2014, 4, 1)
SURVIVOR_ONLY = "survivor-only"
FROM_BOUNDARY = "from-2014-04-01"


def wiki_period(day: date) -> str:
    """The period a date on WIKI is reported in: SURVIVOR_ONLY before BOUNDARY, FROM_BOUNDARY on it and after."""
    return SURVIVOR_ONLY if day < BOUNDARY else FROM_BOUNDARY
