"""R-026 (c): how much a survivor-only sample flatters a result, measured on the synthetic market (NR-F-09).

Each scorer is run through the frozen harness (labels with their delisting ends, folds, ticker groups, HAR-07's metrics,
the portfolio, HAR-08's dispersion) on a synthetic market with delistings and again on the same market with its
delisted names taken out of prices, universe and features, as a survivor-only source would give them. That
construction is `survivorship_market` and `mean_forward` of test/test_harness_adversarial.py (TODO 1.6), copied here
because a test file is not importable. Prints tables and writes nothing but the JSON path it is given. Synthetic only,
and nothing here appends to harness/trials.tsv: a run of this probe is a measurement of the harness, not a trial (HAR-09).

    python scripts/probe/survivorship.py [SEEDS] [OUT.json]
"""
import json
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import NamedTuple

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from neonrain import targets  # noqa: E402
from neonrain.harness import dispersion, metrics, portfolio, split, synthetic  # noqa: E402
from neonrain.harness.market import Market  # noqa: E402

# Choices (each is named in NR-F-09): the market has no planted reversal or momentum, only the `edge` column.
CONFIG = synthetic.MarketConfig(tickers=160, days=1200, rho=0.0, delist_below=0.4)  # ~4.8 years, default folds (HAR-03)
SEEDS = 8  # one seed leaves the sign of a Sharpe difference to chance; eight give a seed sd and a count of seeds above zero
WORKERS = 4  # one process per seed, spawned (polars does not survive a fork, J-013)
SCORERS = {"random": 0, "reversal-5": 5, "reversal-21": 21, "momentum-126": 126}  # name: lookback in sessions
METRICS = ["ic", "sharpe_10bps", "dsr_1"]
KEYS = ["ticker", "date"]
GROUP_SEED = 5  # the seed of the ticker groups; the goldens use the same (HAR-14)


class Result(NamedTuple):
    """One scorer at one horizon: the per-cell values on each market, keyed by (fold, group)."""

    scorer: str
    horizon: int
    seed: int
    full: dict[str, dict[tuple[int, int], float | None]]
    survivors: dict[str, dict[tuple[int, int], float | None]]


def delisted(m: Market) -> list[str]:
    """The tickers whose last price comes before the calendar's last date (test_harness_adversarial.delisted)."""
    last = m.prices.group_by("ticker").agg(pl.col("date").max().alias("last"))
    return sorted(last.filter(pl.col("last") < m.calendar[-1])["ticker"].to_list())


def survivors_only(m: Market) -> Market:
    """The market with its delisted tickers out of prices, universe and features entirely (mean_forward's `removed`)."""
    keep = ~pl.col("ticker").is_in(delisted(m))
    return m._replace(prices=m.prices.filter(keep), universe=m.universe.filter(keep), features=m.features.filter(keep))


def scores(m: Market, name: str, seed: int) -> pl.DataFrame:
    """ticker, date, score. Reversal-L: minus the L-session return (losers high); momentum-L: plus it; random: a draw hashed from (ticker, date, seed).

    A ticker's rows are consecutive sessions, so shifting L rows is L sessions. The first L rows of a ticker have none.
    """
    lookback = SCORERS[name]
    if name == "random":
        # Hashed from the cell's own key, so a cell present in both markets gets the same score in each.
        draw = pl.struct(KEYS).hash(seed=seed + 1000).cast(pl.Float64) / 2.0**64
        return m.features.select(*KEYS, draw.alias("score"))
    prices = m.prices.sort(KEYS)
    past = (pl.col("close") / pl.col("close").shift(lookback).over("ticker") - 1.0).alias("score")
    sign = -1.0 if name.startswith("reversal") else 1.0
    return prices.select(*KEYS, past).drop_nulls("score").with_columns(pl.col("score") * sign)


def cell(m: Market, rows: pl.DataFrame, scored: pl.DataFrame, fold: split.Fold, group: int,
         horizon: int) -> dict[str, float | None]:
    """One (fold, group) cell's IC (its mean), long-short Sharpe at 10 bps and one-trial DSR, as goldens.cell_numbers
    works them but at the one cost level asked for (HAR-07, R-021: the portfolio is scored on every universe row)."""
    groups = split.ticker_groups(m.features["ticker"].unique().to_list(), split.GROUPS, GROUP_SEED)
    _, test = split.cell(rows, fold, m.calendar, horizon, groups, group)
    held = [name for name, found in groups.items() if found == group]
    tested = split.testing(scored, fold, m.calendar).filter(pl.col("ticker").is_in(held))
    net = portfolio.daily(tested, m.prices.filter(pl.col("ticker").is_in(held)), m.calendar, horizon,
                          portfolio.DEFAULT_COST_BPS)["net"].to_numpy()
    ic = metrics.information_coefficient(test.select("date", "score", "rank"))
    return {"ic": ic.mean, "sharpe_10bps": metrics.sharpe(net), "dsr_1": metrics.deflated_sharpe(net, 1, None)}


def grid(m: Market, scored: pl.DataFrame, horizon: int) -> dict[str, dict[tuple[int, int], float | None]]:
    """The harness's cells for one horizon at default folds (HAR-03): metric -> (fold, group) -> value."""
    found = targets.labels(m.prices, m.universe, m.calendar, horizon)
    rows = found.frame.join(scored, on=KEYS)
    out: dict[str, dict[tuple[int, int], float | None]] = {name: {} for name in METRICS}
    for fold in split.folds(len(m.calendar)):
        for group in range(split.GROUPS):
            for name, value in cell(m, rows, scored, fold, group, horizon).items():
                out[name][(fold.number, group)] = value
    return out


def measure(config: synthetic.MarketConfig, seed: int) -> list[Result]:
    """Every scorer at every horizon on the full market and on its survivors, for one seed."""
    full = synthetic.generate(config._replace(seed=seed))
    alone = survivors_only(full)
    out = []
    for name in SCORERS:
        on_full, on_alone = scores(full, name, seed), scores(alone, name, seed)
        for horizon in targets.HORIZONS:
            out.append(Result(name, horizon, seed, grid(full, on_full, horizon), grid(alone, on_alone, horizon)))
    return out


def cell_mean(cells: dict[tuple[int, int], float | None]) -> float | None:
    """The mean of the defined cells."""
    found = [v for v in cells.values() if v is not None]
    return float(np.mean(found)) if found else None


def differences(results: list[Result], metric: str) -> dict[tuple[int, int], float | None]:
    """Survivors minus full in each (fold, group) cell, averaged over the seeds that define both."""
    keys = sorted(results[0].full[metric])
    out: dict[tuple[int, int], float | None] = {}
    for key in keys:
        pairs = [r.survivors[metric][key] - r.full[metric][key] for r in results
                 if r.survivors[metric][key] is not None and r.full[metric][key] is not None]
        out[key] = float(np.mean(pairs)) if pairs else None
    return out


def row(results: list[Result], metric: str) -> dict[str, object]:
    """One table row: the two markets' means, the difference, HAR-08's dispersion of it, and its spread over seeds."""
    spread = dispersion.dispersion(differences(results, metric))
    per_seed = []
    for r in results:
        a, b = cell_mean(r.survivors[metric]), cell_mean(r.full[metric])
        if a is not None and b is not None:
            per_seed.append(a - b)
    means = [cell_mean(r.full[metric]) for r in results], [cell_mean(r.survivors[metric]) for r in results]
    full, alone = (float(np.mean([v for v in m if v is not None])) for m in means)
    undefined = [sum(1 for v in cells.values() if v is None) for r in results for cells in (r.full[metric], r.survivors[metric])]
    return {"full": full, "survivors": alone, "diff": alone - full, "undefined_full": sum(undefined[0::2]),
            "undefined_survivors": sum(undefined[1::2]),
            "folds_sd": spread.folds.sd if spread.folds else None, "groups_sd": spread.groups.sd if spread.groups else None,
            "seed_sd": float(np.std(per_seed, ddof=1)) if len(per_seed) > 1 else None,
            "seeds_positive": sum(1 for d in per_seed if d > 0), "seeds": len(per_seed)}


def table(results: list[Result]) -> dict[str, dict[str, dict[str, object]]]:
    """scorer -> horizon -> metric -> row."""
    out: dict[str, dict[str, dict[str, object]]] = {}
    for name in SCORERS:
        for horizon in targets.HORIZONS:
            mine = [r for r in results if r.scorer == name and r.horizon == horizon]
            out.setdefault(name, {})[str(horizon)] = {metric: row(mine, metric) for metric in METRICS}
    return out


def counts(config: synthetic.MarketConfig, seeds: int) -> dict[str, float]:
    """The share of tickers delisted, and the labels' delisting ends at 63 days, averaged over the seeds."""
    shares, ends, gaps = [], [], []
    for seed in range(seeds):
        m = synthetic.generate(config._replace(seed=seed))
        alone = survivors_only(m)
        shares.append(len(delisted(m)) / config.tickers)
        found = targets.labels(m.prices, m.universe, m.calendar, 63)
        ends.append(found.delisting_ends)
        survived = targets.labels(alone.prices, alone.universe, alone.calendar, 63)
        gaps.append(survived.frame["forward"].mean() - found.frame["forward"].mean())  # the check test_harness_adversarial makes
    return {"delisted_share": float(np.mean(shares)), "delisting_ends_63": float(np.mean(ends)),
            "mean_forward_63_inflation": float(np.mean(gaps))}


def show(found: dict[str, dict[str, dict[str, object]]]) -> None:
    """Print the table: survivors minus full, per scorer and horizon, with the dispersions."""
    print("scorer | h | metric | full | survivors | diff | undefined cells (full, survivors) | folds sd | groups sd | seed sd | seeds + / n")
    for name, by_horizon in found.items():
        for horizon, by_metric in by_horizon.items():
            for metric, r in by_metric.items():
                sd = [("-" if r[k] is None else f"{r[k]:.4f}") for k in ("folds_sd", "groups_sd", "seed_sd")]
                print(f"{name} | {horizon} | {metric} | {r['full']:.4f} | {r['survivors']:.4f} | {r['diff']:+.4f} | "
                      f"{r['undefined_full']}, {r['undefined_survivors']} | "
                      f"{sd[0]} | {sd[1]} | {sd[2]} | {r['seeds_positive']}/{r['seeds']}")


def run(config: synthetic.MarketConfig, seeds: int) -> dict[str, object]:
    """The whole measurement for `seeds` seeds."""
    os.environ.setdefault("POLARS_MAX_THREADS", "1")  # a worker per core; the children inherit it
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(WORKERS, mp_context=context) as pool:
        results = [r for batch in pool.map(measure, [config] * seeds, range(seeds)) for r in batch]
    return {"config": config._asdict(), "seeds": seeds, "scorers": SCORERS, **counts(config, seeds), "table": table(results)}


def main() -> None:
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else SEEDS
    started = time.time()
    found = run(CONFIG, seeds)
    print(f"seeds {seeds}; delisted share {found['delisted_share']:.3f}; delisting ends at 63 days {found['delisting_ends_63']:.0f}; "
          f"mean 63-day forward return, survivors minus full {found['mean_forward_63_inflation']:+.4f}")
    show(found["table"])  # type: ignore[arg-type]
    print(f"seconds {time.time() - started:.0f}")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(found, indent=1, default=str))


if __name__ == "__main__":
    main()
