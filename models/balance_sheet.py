"""Balance Sheet and the capital rollforward. Source rows 88-113 and 120-129.

Borrowings are the plug (source F104):

    borrowings = total_assets - deposits - other_liabilities - equity

Cash is not. Cash is a modeled line that grows with the other asset lines, and
securities are pinned to a share of total assets. What actually flexes to make
the sheet balance is wholesale funding, which is how a bank works: deposits and
assets are what they are, and you borrow the difference.

Equity rolls forward as a corkscrew: opening plus net income less dividends.
Because equity sits inside the plug formula and net income depends on borrowing
interest expense, this module and income_statement.py are mutually dependent.
models/model.py resolves that by iteration.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import corkscrew, growth, pct_of
from models.loans import run as run_loans
from models.securities import run as run_securities
from models.funding import run as run_funding
from models.income_statement import IncomeStatementResult, run as run_income_statement

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class BalanceSheetResult:
    cash: pd.Series               # "Cash and Equivalents"
    securities: pd.Series         # "Securities"
    loans_gross: pd.Series        # "Loans, Gross"
    loan_loss_reserve: pd.Series  # "Loan Loss Reserve"
    loans_net: pd.Series          # "Loans, Net"
    fixed_assets: pd.Series       # "Fixed Assets"
    other_assets: pd.Series       # "Other Assets"
    total_assets: pd.Series       # "Total Assets"

    deposits: pd.Series           # "Deposits"
    borrowings: pd.Series         # "Borrowings" (the plug)
    other_liabilities: pd.Series  # "Other Liabilities"
    total_liabilities: pd.Series  # "Total Liabilities"

    net_income: pd.Series         # "Net Income" (capital rollforward)
    dividends: pd.Series          # "Dividends"
    common_equity: pd.Series      # "Common Equity"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Cash and Equivalents": self.cash,
            "Securities": self.securities,
            "Loans, Gross": self.loans_gross,
            "Loan Loss Reserve": self.loan_loss_reserve,
            "Loans, Net": self.loans_net,
            "Fixed Assets": self.fixed_assets,
            "Other Assets": self.other_assets,
            "Total Assets": self.total_assets,
            "Deposits": self.deposits,
            "Borrowings": self.borrowings,
            "Other Liabilities": self.other_liabilities,
            "Total Liabilities": self.total_liabilities,
            "Dividends": self.dividends,
            "Common Equity": self.common_equity,
        })


def run(
    assumptions: dict | None = None,
    income: IncomeStatementResult | None = None,
) -> BalanceSheetResult:
    """Build the balance sheet, solving borrowings as the plug.

    income is injected by models/model.py during the solve. Use run_all().
    """
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    other_cfg = assumptions["other"]
    eq_cfg = assumptions["equity"]

    loans = run_loans(assumptions)
    securities = run_securities(assumptions)
    funding = run_funding(assumptions)
    if income is None:
        income = run_income_statement(assumptions)

    index = loans.eop_balance.index

    # === CALCULATIONS ===
    total_assets = securities.non_securities_assets + securities.securities

    other_liabilities = growth(
        other_cfg["other_liabilities_opening"], other_cfg["growth_rate"], index
    )

    dividends = pct_of(income.net_income, eq_cfg["dividend_payout_ratio"])
    _, common_equity = corkscrew(eq_cfg["common_equity_opening"], income.net_income, dividends)

    # Borrowings are the plug: whatever wholesale funding makes the sheet balance.
    borrowings = total_assets - funding.deposits - other_liabilities - common_equity
    total_liabilities = funding.deposits + borrowings + other_liabilities

    result = BalanceSheetResult(
        cash=securities.cash,
        securities=securities.securities,
        loans_gross=loans.eop_balance,
        loan_loss_reserve=loans.loan_loss_reserve,
        loans_net=loans.loans_net,
        fixed_assets=securities.fixed_assets,
        other_assets=securities.other_assets,
        total_assets=total_assets,
        deposits=funding.deposits,
        borrowings=borrowings,
        other_liabilities=other_liabilities,
        total_liabilities=total_liabilities,
        net_income=income.net_income,
        dividends=dividends,
        common_equity=common_equity,
    )

    # === CHECKS === (the check cell, source row 113: L + E - A == 0)
    check = result.total_liabilities + result.common_equity - result.total_assets
    assert (check.abs() < 1e-9).all(), f"Balance sheet does not balance: {check}"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Balance Sheet")
    parser.parse_args()

    # run_all(), not run(): borrowings depend on a P&L that charges their interest.
    from models.model import run_all

    result = run_all().balance_sheet
    print("\nBALANCE SHEET")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(result.summary().T)
    print()
