"""NR-F-09's probe (scripts/probe/survivorship.py): a small run has the right shape. It checks no number's size."""
import pytest

from neonrain import targets
from neonrain.harness import synthetic
from scripts.probe import survivorship

SMALL = synthetic.MarketConfig(tickers=60, days=1000, rho=0.0, delist_below=0.4)


def test_the_survivors_market_has_no_delisted_name_left() -> None:
    full = synthetic.generate(SMALL)
    alone = survivorship.survivors_only(full)
    assert len(survivorship.delisted(full)) > 0 and survivorship.delisted(alone) == []
    assert alone.prices["ticker"].n_unique() < full.prices["ticker"].n_unique()
    assert targets.labels(alone.prices, alone.universe, alone.calendar, 63, min_tickers=10).delisting_ends == 0


@pytest.mark.slow
def test_a_small_run_gives_a_row_for_every_scorer_horizon_and_metric() -> None:
    results = survivorship.measure(SMALL, 0)
    assert len(results) == len(survivorship.SCORERS) * len(targets.HORIZONS)
    found = survivorship.table(results)
    assert list(found) == list(survivorship.SCORERS)
    for by_horizon in found.values():
        assert list(by_horizon) == [str(h) for h in targets.HORIZONS]
        for by_metric in by_horizon.values():
            assert list(by_metric) == survivorship.METRICS
            for row in by_metric.values():
                assert {"full", "survivors", "diff", "folds_sd", "groups_sd", "seed_sd", "seeds_positive", "seeds"} <= set(row)
