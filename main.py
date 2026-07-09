"""Entry point: runs the full model and prints a pres-output-style summary.

Usage: python3 main.py
"""

import pandas as pd
import yaml

from models.loans import run as run_loans
from models.securities import run as run_securities
from models.funding import run as run_funding
from models.income_statement import run as run_income_statement
from models.balance_sheet import run as run_balance_sheet

CONFIG_PATH = "config/assumptions.yaml"


def main():
    with open(CONFIG_PATH) as f:
        assumptions = yaml.safe_load(f)

    loans = run_loans(assumptions)
    securities = run_securities(assumptions)
    funding = run_funding(assumptions)
    income = run_income_statement(assumptions)
    balance_sheet = run_balance_sheet(assumptions)

    nim = income.net_interest_income / loans.average_balance

    summary = pd.DataFrame({
        "Cash and Equivalents": balance_sheet.cash_plug,
        "Loans, Net": balance_sheet.loans_net,
        "Total Assets": balance_sheet.total_assets,
        "Deposits": balance_sheet.deposits,
        "Common Equity": balance_sheet.common_equity,
        "Net Income": income.net_income,
        "Net Interest Margin (%)": nim * 100,
    })

    print("\nSTANDARD OPERATING MODEL: Python port")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(summary.T)
    print()
    print(f"Check: total assets - total liabilities - equity == 0 across all years: "
          f"{((balance_sheet.total_assets - balance_sheet.total_liabilities - balance_sheet.common_equity).abs() < 0.01).all()}")
    print()


if __name__ == "__main__":
    main()
