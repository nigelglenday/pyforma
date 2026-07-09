"""Entry point: runs the full model and prints a pres-output-style summary.

Usage: python3 main.py
"""

import pandas as pd
import yaml

from models.model import run_all

CONFIG_PATH = "config/assumptions.yaml"


def main():
    with open(CONFIG_PATH) as f:
        assumptions = yaml.safe_load(f)

    result = run_all(assumptions)
    income = result.income
    balance_sheet = result.balance_sheet

    summary = pd.DataFrame({
        "Cash and Equivalents": balance_sheet.cash,
        "Securities": balance_sheet.securities,
        "Loans, Net": balance_sheet.loans_net,
        "Total Assets": balance_sheet.total_assets,
        "Deposits": balance_sheet.deposits,
        "Borrowings": balance_sheet.borrowings,
        "Common Equity": balance_sheet.common_equity,
        "Net Income": income.net_income,
        "Net Interest Margin (%)": result.net_interest_margin * 100,
    })

    print("\nSTANDARD OPERATING MODEL: Python port")
    print("=" * 100)
    with pd.option_context("display.float_format", "{:,.1f}".format, "display.width", 160):
        print(summary.T)
    print()
    check = (balance_sheet.total_liabilities + balance_sheet.common_equity
             - balance_sheet.total_assets).abs().max()
    print(f"Check: liabilities + equity - assets == 0 across all years: {check < 1e-9} ({check:.2e})")
    print(f"Borrowings plug converged in {result.iterations} passes.")
    print()


if __name__ == "__main__":
    main()
