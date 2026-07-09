"""Securities & Cash tab: sized off the loan book (simplification, see README).

Source model sizes securities as a target % of TOTAL ASSETS, which creates a
circular reference (assets include securities). We size off loans instead
(linked_growth-style) to keep this a one-pass model. Swap for a proper
assets-based target + convergence loop later if the distinction matters.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import pct_of, year_end_index
from models.loans import run as run_loans

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class SecuritiesResult:
    balance: pd.Series          # "Securities and Cash"
    interest_income: pd.Series  # "Interest Income"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Securities & Cash Balance": self.balance,
            "Interest Income": self.interest_income,
        })


def run(assumptions: dict | None = None) -> SecuritiesResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    cfg = assumptions["securities"]
    loans = run_loans(assumptions)

    # === CALCULATIONS ===
    balance = pct_of(loans.eop_balance, cfg["pct_of_loans"])
    interest_income = pct_of(balance, cfg["yield"])

    return SecuritiesResult(balance=balance, interest_income=interest_income)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Securities & Cash tab")
    parser.parse_args()

    result = run()
    print("\nSECURITIES & CASH")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.0f}".format, "display.width", 160):
        print(result.summary().T)
    print()
