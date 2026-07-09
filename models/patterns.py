"""Named pattern vocabulary: shared helpers every model module builds on.

Mirrors the pattern vocabulary in Masterworks' budget-redux MODELING_PATTERNS.md:
corkscrew, growth, pct_of, flat. Kept as plain functions here (no dependency-graph
engine). See README.md for why.
"""

import pandas as pd


def corkscrew(bop0: float, additions: pd.Series, subtractions: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Balance rollforward: close(t) = open(t) + additions(t) - subtractions(t); open(t) = close(t-1)."""
    index = additions.index
    bop, eop = [], []
    balance = float(bop0)
    for t in index:
        bop.append(balance)
        balance = balance + additions[t] - subtractions[t]
        eop.append(balance)
    return pd.Series(bop, index=index), pd.Series(eop, index=index)


def growth(value0: float, rate: float, index: pd.DatetimeIndex) -> pd.Series:
    """value(t) = value(t-1) * (1 + rate), starting from value0 at t=-1."""
    values = []
    prior = float(value0)
    for _ in index:
        prior = prior * (1 + rate)
        values.append(prior)
    return pd.Series(values, index=index)


def pct_of(driver: pd.Series, pct: float) -> pd.Series:
    """value(t) = pct * driver(t)."""
    return driver * pct


def flat(value: float, index: pd.DatetimeIndex) -> pd.Series:
    """value(t) = value, unchanged across the index."""
    return pd.Series(value, index=index)


def average_balance(bop: pd.Series, eop: pd.Series) -> pd.Series:
    return (bop + eop) / 2


def year_end_index(start_year: int, years: int) -> pd.DatetimeIndex:
    return pd.date_range(start=f"{start_year}-12-31", periods=years, freq="YE")
