"""Consolidated solve: the model tab as a whole.

Borrowings balance the sheet, and borrowings carry interest expense. So:

    borrowings -> interest expense -> net income -> equity -> borrowings

Income statement and balance sheet are mutually dependent and neither can import
the other. The loop is closed by iterating to a fixed point: guess the borrowings
balance, run the P&L, run the balance sheet, read the plug that falls out, repeat
until it stops moving.

The source workbook has the same circularity and resolves it the same way, with
Excel's iterative calculation enabled. (It originally dodged the loop by leaving
borrowing interest expense out of the P&L entirely, which was a defect, since
corrected in the workbook at F73 = F49 + F54.)

The feedback contracts hard. A dollar of extra borrowing costs a cent of interest,
of which the after-tax, after-payout fraction reaches equity, which moves the plug
by well under a cent on the next pass.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.loans import LoansResult, run as run_loans
from models.securities import SecuritiesResult, run as run_securities
from models.funding import FundingResult, run as run_funding
from models.income_statement import IncomeStatementResult, run as run_income_statement
from models.balance_sheet import BalanceSheetResult, run as run_balance_sheet

CONFIG_PATH = "config/assumptions.yaml"

# Balances are in millions, so a millionth is far below the model's precision.
TOLERANCE = 1e-9
MAX_ITERATIONS = 100


@dataclass
class ModelResult:
    loans: LoansResult
    securities: SecuritiesResult
    funding: FundingResult
    income: IncomeStatementResult
    balance_sheet: BalanceSheetResult
    iterations: int          # passes needed to converge, for diagnostics

    @property
    def average_earning_assets(self) -> pd.Series:
        """Loans, securities, and cash earn. Fixed and other assets do not."""
        return (
            self.loans.average_balance
            + self.securities.securities
            + self.securities.cash
        )

    @property
    def net_interest_margin(self) -> pd.Series:
        return self.income.net_interest_income_before_provisions / self.average_earning_assets


def run_all(assumptions: dict | None = None) -> ModelResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    # Loans and securities sit upstream of the loop: neither depends on borrowings,
    # so they are solved once and held fixed across passes.
    loans = run_loans(assumptions)
    securities = run_securities(assumptions)

    # === SOLVE ===
    borrowings = pd.Series(float(assumptions["funding"]["borrowings_opening"]), index=loans.eop_balance.index)
    for iteration in range(1, MAX_ITERATIONS + 1):
        funding = run_funding(assumptions, borrowings=borrowings)
        income = run_income_statement(assumptions, funding=funding)
        balance_sheet = run_balance_sheet(assumptions, income=income)
        solved = balance_sheet.borrowings
        moved = (solved - borrowings).abs().max()
        borrowings = solved
        if moved < TOLERANCE:
            break
    else:
        raise RuntimeError(
            f"Borrowings did not converge in {MAX_ITERATIONS} passes. Last move: {moved:.9f}"
        )

    # Re-run the tabs once more on the converged plug so that every result object
    # reflects the same borrowings balance the balance sheet reports.
    funding = run_funding(assumptions, borrowings=borrowings)
    income = run_income_statement(assumptions, funding=funding)
    balance_sheet = run_balance_sheet(assumptions, income=income)

    return ModelResult(
        loans=loans,
        securities=securities,
        funding=funding,
        income=income,
        balance_sheet=balance_sheet,
        iterations=iteration,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidated solve")
    parser.parse_args()

    result = run_all()
    print(f"\nConverged in {result.iterations} passes.")
    for title, frame in (
        ("INCOME STATEMENT", result.income.summary()),
        ("BALANCE SHEET", result.balance_sheet.summary()),
    ):
        print(f"\n{title}")
        print("=" * 100)
        with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
            print(frame.T)
    print()
