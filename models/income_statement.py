"""Income Statement: assembles loans, securities, and funding into NII, then
fee income, opex, and tax down to net income.

Cross-module imports = cross-tab references: this module reads loans.py,
securities.py, funding.py the way an Excel P&L tab would reference other tabs.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import pct_of
from models.loans import run as run_loans
from models.securities import run as run_securities
from models.funding import run as run_funding

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class IncomeStatementResult:
    interest_income: pd.Series          # "Interest Income"
    interest_expense: pd.Series         # "Interest Expense"
    net_interest_income: pd.Series      # "Net Interest Income"
    provision_for_credit_losses: pd.Series  # "Provision for Credit Losses"
    net_interest_income_after_provision: pd.Series
    fee_income: pd.Series               # "Fee Income"
    total_revenue: pd.Series            # "Total Revenue"
    operating_expense: pd.Series        # "Operating Expense"
    pretax_income: pd.Series            # "Pre-Tax Income"
    tax_expense: pd.Series              # "Tax Expense"
    net_income: pd.Series               # "Net Income"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Interest Income": self.interest_income,
            "Interest Expense": self.interest_expense,
            "Net Interest Income": self.net_interest_income,
            "Provision for Credit Losses": self.provision_for_credit_losses,
            "NII After Provision": self.net_interest_income_after_provision,
            "Fee Income": self.fee_income,
            "Total Revenue": self.total_revenue,
            "Operating Expense": self.operating_expense,
            "Pre-Tax Income": self.pretax_income,
            "Tax Expense": self.tax_expense,
            "Net Income": self.net_income,
        })


def run(assumptions: dict | None = None) -> IncomeStatementResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    cfg = assumptions["income_statement"]

    loans = run_loans(assumptions)
    securities = run_securities(assumptions)
    funding = run_funding(assumptions)

    # === CALCULATIONS ===
    interest_income = loans.interest_income + securities.interest_income
    interest_expense = funding.total_interest_expense
    net_interest_income = interest_income - interest_expense

    # Provision = current-period net charge-offs (simplification: no reserve build/release)
    provision_for_credit_losses = loans.net_charge_offs
    nii_after_provision = net_interest_income - provision_for_credit_losses

    fee_income = pct_of(net_interest_income, cfg["fee_income_pct_of_nii"])
    total_revenue = nii_after_provision + fee_income

    operating_expense = pct_of(total_revenue, cfg["efficiency_ratio"])
    pretax_income = total_revenue - operating_expense

    tax_expense = pct_of(pretax_income, cfg["tax_rate"])
    net_income = pretax_income - tax_expense

    result = IncomeStatementResult(
        interest_income=interest_income,
        interest_expense=interest_expense,
        net_interest_income=net_interest_income,
        provision_for_credit_losses=provision_for_credit_losses,
        net_interest_income_after_provision=nii_after_provision,
        fee_income=fee_income,
        total_revenue=total_revenue,
        operating_expense=operating_expense,
        pretax_income=pretax_income,
        tax_expense=tax_expense,
        net_income=net_income,
    )

    # === CHECKS ===
    assert (result.net_income == result.pretax_income - result.tax_expense).all()

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Income Statement")
    parser.parse_args()

    result = run()
    print("\nINCOME STATEMENT")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.0f}".format, "display.width", 160):
        print(result.summary().T)
    print()
