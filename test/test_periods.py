"""The boundary between WIKI's two reported periods is one date, and a day falls on the side R-026 says."""
from datetime import date

from neonrain.universe import periods


def test_the_boundary_is_the_first_day_of_the_second_period() -> None:
    assert periods.BOUNDARY == date(2014, 4, 1)


def test_the_day_before_the_boundary_is_survivor_only() -> None:
    assert periods.wiki_period(date(2014, 3, 31)) == periods.SURVIVOR_ONLY


def test_the_boundary_itself_starts_the_second_period() -> None:
    assert periods.wiki_period(date(2014, 4, 1)) == periods.FROM_BOUNDARY


def test_a_later_day_is_in_the_second_period() -> None:
    assert periods.wiki_period(date(2017, 11, 7)) == periods.FROM_BOUNDARY
