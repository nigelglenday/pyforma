"""Income Statement. Source rows 69-86.

Cross-module imports = cross-tab references: this module reads loans.py,
securities.py, funding.py the way an Excel P&L tab would reference other tabs.

One formula deserves calling out. Fee income is defined as a share of TOTAL
revenue, not as a share of net interest income, so it has to be grossed up
(source F77):

    fee = nii_after_provision * r / (1 - r)

which makes fee income exactly r of (nii_after_provision + fee). Multiplying
net interest income by r directly, as an earlier version of this port did,
understates it and uses the wrong base (before provision rather than after).
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
    interest_income_on_loans: pd.Series          # "Interest Income on Loans"
    interest_income_on_securities_and_cash: pd.Series  # "Interest Income on Securities and Cash"
    interest_income: pd.Series                   # "Interest Income"
    interest_expense: pd.Series                  # "Interest Expense"
    net_interest_income_before_provisions: pd.Series  # "Net Interest Income Before Provisions"
    loan_loss_provision: pd.Series               # "Loan Loss Provision"
    net_interest_income_after_provisions: pd.Series   # "Net Interest Income After Provisions"
    non_interest_income: pd.Series               # "Non-Interest Income"
    total_revenue: pd.Series                     # "Total Revenue"
    operating_expense: pd.Series                 # "Operating Expense"
    pretax_income: pd.Series                     # "Pre-Tax Income"
    tax_provision: pd.Series                     # "Tax Provision"
    net_income: pd.Series                        # "Net Income"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Interest Income on Loans": self.interest_income_on_loans,
            "Interest Income on Securities and Cash": self.interest_income_on_securities_and_cash,
            "Interest Income": self.interest_income,
            "Interest Expense": self.interest_expense,
            "Net Interest Income Before Provisions": self.net_interest_income_before_provisions,
            "Loan Loss Provision": self.loan_loss_provision,
            "Net Interest Income After Provisions": self.net_interest_income_after_provisions,
            "Non-Interest Income": self.non_interest_income,
            "Total Revenue": self.total_revenue,
            "Operating Expense": self.operating_expense,
            "Pre-Tax Income": self.pretax_income,
            "Tax Provision": self.tax_provision,
            "Net Income": self.net_income,
        })


def run(
    assumptions: dict | None = None,
    funding: "FundingResult | None" = None,
) -> IncomeStatementResult:
    """Run the P&L.

    funding is injected by models/model.py so that borrowing interest expense
    reflects the solved plug rather than a placeholder. Use run_all().
    """
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    cfg = assumptions["income_statement"]

    loans = run_loans(assumptions)
    securities = run_securities(assumptions)
    if funding is None:
        funding = run_funding(assumptions)

    # === CALCULATIONS ===
    interest_income = loans.interest_income + securities.interest_income
    interest_expense = funding.interest_expense
    nii_before = interest_income - interest_expense

    nii_after = nii_before - loans.loan_loss_provision

    # Grossed up so that fee income is `ratio` of total revenue, not of NII.
    ratio = cfg["fee_income_ratio"]
    non_interest_income = pct_of(nii_after, ratio / (1 - ratio))
    total_revenue = nii_after + non_interest_income

    operating_expense = pct_of(total_revenue, cfg["efficiency_ratio"])
    pretax_income = total_revenue - operating_expense

    tax_provision = pct_of(pretax_income, cfg["tax_rate"])
    net_income = pretax_income - tax_provision

    result = IncomeStatementResult(
        interest_income_on_loans=loans.interest_income,
        interest_income_on_securities_and_cash=securities.interest_income,
        interest_income=interest_income,
        interest_expense=interest_expense,
        net_interest_income_before_provisions=nii_before,
        loan_loss_provision=loans.loan_loss_provision,
        net_interest_income_after_provisions=nii_after,
        non_interest_income=non_interest_income,
        total_revenue=total_revenue,
        operating_expense=operating_expense,
        pretax_income=pretax_income,
        tax_provision=tax_provision,
        net_income=net_income,
    )

    # === CHECKS === fee income must land on its target share of total revenue
    share = result.non_interest_income / result.total_revenue
    assert ((share - ratio).abs() < 1e-12).all(), "Fee income missed target % of revenue"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Income Statement")
    parser.parse_args()

    # run_all(), not run(): interest expense depends on the solved borrowings plug.
    from models.model import run_all

    result = run_all().income
    print("\nINCOME STATEMENT")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(result.summary().T)
    print()
