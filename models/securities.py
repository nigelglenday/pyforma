"""Securities and Cash tab. Source rows 24-34, plus balance sheet rows 90-91.

Securities are sized as a target percent of TOTAL assets, and total assets
include securities. That looks circular, but it isn't: it solves in closed form.
Writing A for the assets that are not securities and p for the target percent,

    S = p * (A + S)   =>   S = A * p / (1 - p)

which is exactly the source's formula (F91). No convergence loop is needed here.

Cash is NOT the balancing plug. It is a modeled line that compounds at the
"Other Asset Growth" rate along with fixed and other assets (source F90). The
balance sheet is balanced by borrowings instead. See balance_sheet.py.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import average_balance, growth, pct_of, prepend_opening
from models.loans import run as run_loans

CONFIG_PATH = "config/assumptions.yaml"


def other_asset_lines(assumptions: dict, index: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """Fixed and other assets, compounding at the other-asset growth rate.

    Lives here rather than in balance_sheet.py because the securities closed form
    needs them: they are part of the non-securities asset base. balance_sheet.py
    imports them back out. Goodwill, intangibles, and OREO are all zero in the
    source and are omitted rather than carried as zero lines.
    """
    cfg = assumptions["other"]
    return {
        "fixed_assets": growth(cfg["fixed_assets_opening"], cfg["growth_rate"], index),
        "other_assets": growth(cfg["other_assets_opening"], cfg["growth_rate"], index),
    }


# === RESULT ===

@dataclass
class SecuritiesResult:
    cash: pd.Series                     # "Cash and Equivalents"
    cash_interest_income: pd.Series     # source row 34
    securities: pd.Series               # "Securities Balance"
    securities_interest_income: pd.Series  # source row 29
    fixed_assets: pd.Series             # "Fixed Assets"
    other_assets: pd.Series             # "Other Assets"
    loans_net: pd.Series                # "Loans, Net", carried through for the closed form

    @property
    def interest_income(self) -> pd.Series:
        """"Interest Income on Securities and Cash" (source row 71)."""
        return self.securities_interest_income + self.cash_interest_income

    @property
    def non_securities_assets(self) -> pd.Series:
        """Everything on the asset side except securities. Drives the closed form."""
        return self.cash + self.fixed_assets + self.other_assets + self.loans_net

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Cash and Equivalents": self.cash,
            "Securities": self.securities,
            "Interest Income on Cash": self.cash_interest_income,
            "Interest Income on Securities": self.securities_interest_income,
            "Interest Income on Securities and Cash": self.interest_income,
        })


def run(assumptions: dict | None = None) -> SecuritiesResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    sec_cfg = assumptions["securities"]
    cash_cfg = assumptions["cash"]
    other_cfg = assumptions["other"]

    loans = run_loans(assumptions)
    index = loans.eop_balance.index

    # === CALCULATIONS ===
    cash = growth(cash_cfg["balance_opening"], other_cfg["growth_rate"], index)
    others = other_asset_lines(assumptions, index)

    non_securities_assets = cash + loans.loans_net + others["fixed_assets"] + others["other_assets"]

    # Closed form: S = A * p / (1 - p). Assets include securities; algebra, not iteration.
    pct = sec_cfg["pct_of_assets"]
    securities = pct_of(non_securities_assets, pct / (1 - pct))

    # Interest is struck on average balances, so both lines need their opening balance.
    securities_interest_income = pct_of(
        average_balance(prepend_opening(securities, sec_cfg["balance_opening"]), securities),
        sec_cfg["yield"],
    )
    cash_interest_income = pct_of(
        average_balance(prepend_opening(cash, cash_cfg["balance_opening"]), cash),
        cash_cfg["yield"],
    )

    result = SecuritiesResult(
        cash=cash,
        cash_interest_income=cash_interest_income,
        securities=securities,
        securities_interest_income=securities_interest_income,
        fixed_assets=others["fixed_assets"],
        other_assets=others["other_assets"],
        loans_net=loans.loans_net,
    )

    # === CHECKS === securities must land on the target share of total assets
    total_assets = non_securities_assets + securities
    assert ((securities / total_assets - pct).abs() < 1e-12).all(), "Securities missed target % of assets"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Securities and Cash tab")
    parser.parse_args()

    result = run()
    print("\nSECURITIES AND CASH")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(result.summary().T)
    print()
