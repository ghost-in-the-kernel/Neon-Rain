"""A naive, independent mirror of HAR-06 and HAR-07, written from the spec text alone."""

import math
from datetime import date
from statistics import NormalDist

EULER_GAMMA = 0.5772156649
TRADING_DAYS = 252


def _predicts_up(score: float) -> bool:
    """The direction prediction: up only when the score is strictly above 0.5."""
    return score > 0.5


def accuracy(rows: list[tuple[float, int | None]]) -> float | None:
    """Fraction of labelled rows whose prediction matches the label; None with no labelled rows."""
    total = 0
    right = 0
    for score, direction in rows:
        if direction is None:
            continue
        total += 1
        if _predicts_up(score) == (direction == 1):
            right += 1
    if total == 0:
        return None
    return right / total


def balanced_accuracy(rows: list[tuple[float, int | None]]) -> float | None:
    """Mean of the two per-class recalls; None when either class has no rows."""
    tp = fn = tn = fp = 0
    for score, direction in rows:
        if direction is None:
            continue
        up = _predicts_up(score)
        if direction == 1:
            if up:
                tp += 1
            else:
                fn += 1
        else:
            if up:
                fp += 1
            else:
                tn += 1
    if tp + fn == 0 or tn + fp == 0:
        return None
    return (tp / (tp + fn) + tn / (tn + fp)) / 2


def _average_ranks(values: list[float]) -> list[float]:
    """Ranks 1..n of the values, tied values sharing their average rank."""
    order = sorted(range(len(values)), key=lambda k: values[k])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + 1 + j + 1) / 2
        for m in range(i, j + 1):
            ranks[order[m]] = average
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation of two equal-length lists, assumed non-constant."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = 0.0
    sxx = 0.0
    syy = 0.0
    for x, y in zip(xs, ys):
        sxy += (x - mx) * (y - my)
        sxx += (x - mx) ** 2
        syy += (y - my) ** 2
    return sxy / math.sqrt(sxx * syy)


def _sample_sd(values: list[float]) -> float:
    """Sample standard deviation, divisor n - 1 (needs at least two values)."""
    n = len(values)
    mean = sum(values) / n
    total = 0.0
    for v in values:
        total += (v - mean) ** 2
    return math.sqrt(total / (n - 1))


def _all_equal(values: list[float]) -> bool:
    """True when every value equals the first."""
    for v in values:
        if v != values[0]:
            return False
    return True


def _daily_ics(rows: list[tuple[date, float, float]], min_tickers: int) -> tuple[list[float], int, int]:
    """Per-date Spearman ICs, with the counts of thin dates and all-equal dates dropped."""
    by_date: dict[date, list[tuple[float, float]]] = {}
    for day, score, q in rows:
        by_date.setdefault(day, []).append((score, q))
    ics: list[float] = []
    thin = 0
    flat = 0
    for day in sorted(by_date):
        pairs = by_date[day]
        if len(pairs) < min_tickers:
            thin += 1
            continue
        scores = [p[0] for p in pairs]
        labels = [p[1] for p in pairs]
        if _all_equal(scores) or _all_equal(labels):
            flat += 1
            continue
        ics.append(_pearson(_average_ranks(scores), _average_ranks(labels)))
    return ics, thin, flat


def information_coefficient(rows: list[tuple[date, float, float]], min_tickers: int = 20) -> tuple[float | None, float | None, float | None, int, int, int]:
    """Mean daily Spearman IC, its standard error and t, and the date counts."""
    ics, thin, flat = _daily_ics(rows, min_tickers)
    n = len(ics)
    if n == 0:
        return None, None, None, 0, thin, flat
    mean = sum(ics) / n
    if n < 2:
        return mean, None, None, n, thin, flat
    se = _sample_sd(ics) / math.sqrt(n)
    t_stat = None if se == 0 else mean / se
    return mean, se, t_stat, n, thin, flat


def _pick_legs(day_scores: list[tuple[str, float]], day: date, closes: dict[tuple[str, date], float]) -> tuple[list[str], list[str]]:
    """The long (top decile) and short (bottom decile) names for a date; empty when n = 0."""
    tested = []
    for ticker, score in day_scores:
        if (ticker, day) in closes:
            tested.append((score, ticker))
    tested.sort()
    n = len(tested) // 10
    if n == 0:
        return [], []
    short = [ticker for _, ticker in tested[:n]]
    long = [ticker for _, ticker in tested[len(tested) - n:]]
    return long, short


def _run_leg(names: list[str], k: int, end: int, calendar: list[date], closes: dict[tuple[str, date], float]) -> tuple[list[float], list[int]]:
    """Summed daily returns of a leg over days k+1..end, and each name's close-out index."""
    sums = [0.0] * (end - k)
    close_at: list[int] = []
    for name in names:
        closed = end
        for j in range(k + 1, end + 1):
            price = closes.get((name, calendar[j]))
            if price is None:
                closed = j - 1
                break
            sums[j - k - 1] += price / closes[(name, calendar[j - 1])] - 1
        close_at.append(closed)
    return sums, close_at


def _add_sleeve(k: int, long: list[str], short: list[str], calendar: list[date], closes: dict[tuple[str, date], float], horizon: int, cost_bps: float, gross: dict[int, float], cost: dict[int, float]) -> int:
    """Book one sleeve's returns and costs by calendar index; return its last touched index."""
    n = len(long)
    end = min(k + horizon, len(calendar) - 1)
    long_sums, long_close = _run_leg(long, k, end, calendar, closes)
    short_sums, short_close = _run_leg(short, k, end, calendar, closes)
    for j in range(k + 1, end + 1):
        sleeve_return = long_sums[j - k - 1] / n - short_sums[j - k - 1] / n
        gross[j] = gross.get(j, 0.0) + sleeve_return / horizon
    per_name = (cost_bps / 10000) * (1 / horizon) * (1 / n)
    cost[k] = cost.get(k, 0.0) + per_name * 2 * n
    for idx in long_close + short_close:
        cost[idx] = cost.get(idx, 0.0) + per_name
    return end


def portfolio_daily(scores: list[tuple[str, date, float]], closes: dict[tuple[str, date], float], calendar: list[date], horizon: int, cost_bps: float) -> list[tuple[date, float, float, float]]:
    """Daily (date, gross, cost, net) of the overlapping long-short decile sleeves."""
    if not scores:
        return []
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    by_date: dict[date, list[tuple[str, float]]] = {}
    for ticker, day, score in scores:
        by_date.setdefault(day, []).append((ticker, score))
    index = {day: i for i, day in enumerate(calendar)}
    for day in by_date:
        if day not in index:
            raise ValueError(f"test date {day} is not in the calendar")
    test_dates = sorted(by_date)
    gross: dict[int, float] = {}
    cost: dict[int, float] = {}
    last = -1
    for day in test_dates:
        long, short = _pick_legs(by_date[day], day, closes)
        if long:
            touched = _add_sleeve(index[day], long, short, calendar, closes, horizon, cost_bps, gross, cost)
            last = max(last, touched)
    if last < 0:
        last = min(index[test_dates[-1]] + horizon, len(calendar) - 1)
    out = []
    for i in range(index[test_dates[0]], last + 1):
        g = gross.get(i, 0.0)
        c = cost.get(i, 0.0)
        out.append((calendar[i], g, c, g - c))
    return out


def _plain_sharpe(daily: list[float]) -> float | None:
    """Non-annualized Sharpe mean / sd (divisor T - 1); None for T < 2 or sd = 0."""
    if len(daily) < 2:
        return None
    sd = _sample_sd(daily)
    if sd == 0:
        return None
    return (sum(daily) / len(daily)) / sd


def sharpe(daily: list[float]) -> float | None:
    """Annualized Sharpe of a daily series, excess of zero."""
    sr = _plain_sharpe(daily)
    if sr is None:
        return None
    return sr * math.sqrt(TRADING_DAYS)


def _skew_kurt(daily: list[float]) -> tuple[float, float]:
    """Moment skewness m3/m2^1.5 and (non-excess) kurtosis m4/m2^2, divisor T."""
    t = len(daily)
    mean = sum(daily) / t
    m2 = m3 = m4 = 0.0
    for x in daily:
        m2 += (x - mean) ** 2
        m3 += (x - mean) ** 3
        m4 += (x - mean) ** 4
    m2 /= t
    m3 /= t
    m4 /= t
    return m3 / m2 ** 1.5, m4 / m2 ** 2


def _sr_zero(trials: int, variance: float | None) -> float:
    """The expected maximum Sharpe under the null across the trials (0 for one trial)."""
    if trials == 1:
        return 0.0
    if variance is None or variance < 0:
        raise ValueError("variance must be a non-negative number when trials > 1")
    inv = NormalDist().inv_cdf
    bracket = (1 - EULER_GAMMA) * inv(1 - 1 / trials) + EULER_GAMMA * inv(1 - 1 / (trials * math.e))
    return math.sqrt(variance) * bracket


def deflated_sharpe(daily: list[float], trials: int, variance: float | None) -> float | None:
    """Bailey and Lopez de Prado's deflated Sharpe ratio of the daily series."""
    if trials < 1:
        raise ValueError("trials must be at least 1")
    sr0 = _sr_zero(trials, variance)
    sr = _plain_sharpe(daily)
    if sr is None:
        return None
    skew, kurt = _skew_kurt(daily)
    term = 1 - skew * sr + ((kurt - 1) / 4) * sr ** 2
    if term <= 0:
        return None
    return NormalDist().cdf((sr - sr0) * math.sqrt(len(daily) - 1) / math.sqrt(term))
