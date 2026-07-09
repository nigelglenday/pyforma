"""Funding tab: deposits and borrowings. Source rows 44-54.

Deposits compound at their own growth rate. Borrowings do not: they are the
balancing item on the balance sheet, solved in balance_sheet.py and injected
back here so their interest expense can be struck.

That injection is what makes the model circular. Borrowings balance the sheet,
borrowings carry interest expense, interest expense moves net income, net income
moves equity, and equity moves the plug. models/model.py closes the loop.

Both interest lines are struck on average balances (source F48, F53).
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import average_balance, flat, growth, pct_of, prepend_opening, year_end_index

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class FundingResult:
    deposits: pd.Series                     # "Deposit Balance"
    deposit_interest_expense: pd.Series     # source row 49
    borrowings: pd.Series                   # "Borrowing Balance"
    borrowing_interest_expense: pd.Series   # source row 54

    @property
    def interest_expense(self) -> pd.Series:
        """"Interest Expense" (source row 73).

        The source workbook computed borrowing interest expense and then omitted
        it from this total, referencing deposits alone. That was a defect; it has
        since been corrected in the workbook (F73 = F49 + F54, with iterative
        calculation enabled to resolve the circularity it creates).
        """
        return self.deposit_interest_expense + self.borrowing_interest_expense

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Deposits": self.deposits,
            "Deposit Interest Expense": self.deposit_interest_expense,
            "Borrowings": self.borrowings,
            "Borrowing Interest Expense": self.borrowing_interest_expense,
            "Interest Expense": self.interest_expense,
        })


def run(
    assumptions: dict | None = None,
    borrowings: pd.Series | None = None,
) -> FundingResult:
    """Run the funding tab.

    borrowings is the closing balance series, injected by models/model.py during
    the solve. It defaults to a flat opening balance so this module still runs
    standalone, but that default is not the solved plug. Use run_all().
    """
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    horizon = assumptions["horizon"]
    cfg = assumptions["funding"]
    index = year_end_index(horizon["start_year"], horizon["years"])

    # === CALCULATIONS ===
    deposits = growth(cfg["deposits_opening"], cfg["deposit_growth_rate"], index)
    deposit_interest_expense = pct_of(
        average_balance(prepend_opening(deposits, cfg["deposits_opening"]), deposits),
        cfg["cost_of_deposits"],
    )

    if borrowings is None:
        borrowings = flat(cfg["borrowings_opening"], index)
    borrowing_interest_expense = pct_of(
        average_balance(prepend_opening(borrowings, cfg["borrowings_opening"]), borrowings),
        cfg["cost_of_borrowings"],
    )

    return FundingResult(
        deposits=deposits,
        deposit_interest_expense=deposit_interest_expense,
        borrowings=borrowings,
        borrowing_interest_expense=borrowing_interest_expense,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Funding tab")
    parser.parse_args()

    # run_all(), not run(): borrowings are the solved plug.
    from models.model import run_all

    result = run_all().funding
    print("\nFUNDING")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(result.summary().T)
    print()
