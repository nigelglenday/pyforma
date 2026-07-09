"""Funding tab: deposits and borrowings, growth pattern, interest expense."""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import growth, pct_of, year_end_index

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class FundingResult:
    deposits_eop: pd.Series          # "Deposits"
    borrowings_eop: pd.Series        # "Borrowings"
    deposit_interest_expense: pd.Series
    borrowing_interest_expense: pd.Series

    @property
    def total_interest_expense(self) -> pd.Series:
        return self.deposit_interest_expense + self.borrowing_interest_expense

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Deposits": self.deposits_eop,
            "Borrowings": self.borrowings_eop,
            "Deposit Interest Expense": self.deposit_interest_expense,
            "Borrowing Interest Expense": self.borrowing_interest_expense,
            "Total Interest Expense": self.total_interest_expense,
        })


def run(assumptions: dict | None = None) -> FundingResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    horizon = assumptions["horizon"]
    cfg = assumptions["funding"]
    index = year_end_index(horizon["start_year"], horizon["years"])

    # === CALCULATIONS ===
    deposits_eop = growth(cfg["deposits_bop_yr0"], cfg["deposit_growth_rate"], index)
    borrowings_eop = growth(cfg["borrowings_bop_yr0"], cfg["borrowings_growth_rate"], index)

    deposit_interest_expense = pct_of(deposits_eop, cfg["cost_of_deposits"])
    borrowing_interest_expense = pct_of(borrowings_eop, cfg["cost_of_borrowings"])

    return FundingResult(
        deposits_eop=deposits_eop,
        borrowings_eop=borrowings_eop,
        deposit_interest_expense=deposit_interest_expense,
        borrowing_interest_expense=borrowing_interest_expense,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Funding tab")
    parser.parse_args()

    result = run()
    print("\nFUNDING")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.0f}".format, "display.width", 160):
        print(result.summary().T)
    print()
