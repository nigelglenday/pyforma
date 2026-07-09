"""Loans tab: corkscrew rollforward of the loan book.

Formula check against source "Standard Operating Model v2.xlsx" > model tab, yr 1:
  BOP 1350, +Orig 400, Amort -270 (=1350*.20), NCO -13.5 (=1350*.01) -> EOP 1466.5
  Confirmed: amort and NCO are both computed off BOP, not BOP+originations.
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import average_balance, corkscrew, flat, pct_of, year_end_index

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class LoansResult:
    bop_balance: pd.Series           # "BOP Balance"
    originations: pd.Series          # "Originations"
    amortization_prepayment: pd.Series  # "Amortization/Prepayment"
    net_charge_offs: pd.Series       # "Net Charge-Offs"
    eop_balance: pd.Series           # "EOP Balance"
    average_balance: pd.Series       # "Average Balance"
    interest_income: pd.Series       # "Interest Income"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "BOP Balance": self.bop_balance,
            "Originations": self.originations,
            "Amort/Prepay": self.amortization_prepayment,
            "Net Charge-Offs": self.net_charge_offs,
            "EOP Balance": self.eop_balance,
            "Average Balance": self.average_balance,
            "Interest Income": self.interest_income,
        })


def run(assumptions: dict | None = None) -> LoansResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    horizon = assumptions["horizon"]
    loans_cfg = assumptions["loans"]
    index = year_end_index(horizon["start_year"], horizon["years"])

    # === INPUTS ===
    originations = flat(loans_cfg["new_volume"], index)

    # === CALCULATIONS ===
    # amort and NCO are % of BOP, which we only know once we roll forward,
    # so roll forward period by period (this is the corkscrew's own loop).
    bop, eop = [], []
    amort, nco = [], []
    balance = float(loans_cfg["bop_balance_yr0"])
    for t in index:
        bop.append(balance)
        period_amort = balance * loans_cfg["amort_prepay_rate"]
        period_nco = balance * loans_cfg["net_charge_off_rate"]
        amort.append(period_amort)
        nco.append(period_nco)
        balance = balance + loans_cfg["new_volume"] - period_amort - period_nco
        eop.append(balance)

    bop_balance = pd.Series(bop, index=index)
    eop_balance = pd.Series(eop, index=index)
    amortization_prepayment = pd.Series(amort, index=index)
    net_charge_offs = pd.Series(nco, index=index)
    avg_balance = average_balance(bop_balance, eop_balance)
    interest_income = pct_of(avg_balance, loans_cfg["yield"])

    result = LoansResult(
        bop_balance=bop_balance,
        originations=originations,
        amortization_prepayment=amortization_prepayment,
        net_charge_offs=net_charge_offs,
        eop_balance=eop_balance,
        average_balance=avg_balance,
        interest_income=interest_income,
    )

    # === CHECKS ===
    assert (eop_balance >= 0).all(), "Loan balance went negative: check amort/NCO rates"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Loans tab")
    parser.parse_args()

    result = run()
    print("\nLOANS")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.0f}".format, "display.width", 160):
        print(result.summary().T)
    print()
