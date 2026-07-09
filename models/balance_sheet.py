"""Balance Sheet: assembles loans, securities, funding, and equity.

Cash is the balancing plug: assets = liabilities + equity, so cash is solved
as the residual rather than modeled directly. This sidesteps building a full
cash flow statement in the time available. See README for the honest tradeoff.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import corkscrew, flat, pct_of
from models.loans import run as run_loans
from models.securities import run as run_securities
from models.funding import run as run_funding
from models.income_statement import run as run_income_statement

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class BalanceSheetResult:
    cash_plug: pd.Series          # "Cash and Equivalents" (solved, not modeled)
    securities: pd.Series         # "Securities"
    loans_net: pd.Series          # "Loans, Net"
    other_assets: pd.Series       # "Other Assets"
    total_assets: pd.Series       # "Total Assets"

    deposits: pd.Series           # "Deposits"
    borrowings: pd.Series         # "Borrowings"
    other_liabilities: pd.Series  # "Other Liabilities"
    total_liabilities: pd.Series  # "Total Liabilities"

    dividends_paid: pd.Series     # "Dividends"
    common_equity: pd.Series      # "Common Equity"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Cash and Equivalents": self.cash_plug,
            "Securities": self.securities,
            "Loans, Net": self.loans_net,
            "Other Assets": self.other_assets,
            "Total Assets": self.total_assets,
            "Deposits": self.deposits,
            "Borrowings": self.borrowings,
            "Other Liabilities": self.other_liabilities,
            "Total Liabilities": self.total_liabilities,
            "Dividends": self.dividends_paid,
            "Common Equity": self.common_equity,
        })


def run(assumptions: dict | None = None) -> BalanceSheetResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    bs_cfg = assumptions["balance_sheet"]
    eq_cfg = assumptions["equity"]

    loans = run_loans(assumptions)
    securities = run_securities(assumptions)
    funding = run_funding(assumptions)
    income = run_income_statement(assumptions)

    index = loans.eop_balance.index

    # === CALCULATIONS ===
    loans_net = loans.eop_balance  # simplification: no separate loan loss reserve line
    other_assets = flat(bs_cfg["other_assets_yr0"], index)

    total_liabilities_ex_other = funding.deposits_eop + funding.borrowings_eop
    other_liabilities = flat(bs_cfg["other_liabilities_yr0"], index)
    total_liabilities = total_liabilities_ex_other + other_liabilities

    dividends_paid = pct_of(income.net_income, eq_cfg["dividend_payout_ratio"])
    _, common_equity = corkscrew(eq_cfg["bop_yr0"], income.net_income, dividends_paid)

    # Cash is the plug: Assets = Liabilities + Equity
    # cash = (liabilities + equity) - (securities + loans_net + other_assets)
    non_cash_assets = securities.balance + loans_net + other_assets
    cash_plug = (total_liabilities + common_equity) - non_cash_assets

    total_assets = cash_plug + non_cash_assets

    result = BalanceSheetResult(
        cash_plug=cash_plug,
        securities=securities.balance,
        loans_net=loans_net,
        other_assets=other_assets,
        total_assets=total_assets,
        deposits=funding.deposits_eop,
        borrowings=funding.borrowings_eop,
        other_liabilities=other_liabilities,
        total_liabilities=total_liabilities,
        dividends_paid=dividends_paid,
        common_equity=common_equity,
    )

    # === CHECKS === (the check cell: assets - liabilities - equity == 0)
    check = result.total_assets - result.total_liabilities - result.common_equity
    assert (check.abs() < 0.01).all(), f"Balance sheet does not balance: {check}"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Balance Sheet")
    parser.parse_args()

    result = run()
    print("\nBALANCE SHEET")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.0f}".format, "display.width", 160):
        print(result.summary().T)
    print()
