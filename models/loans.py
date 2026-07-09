"""Loans tab: corkscrew rollforward of the loan book, plus the loan loss reserve.

Ported from "Standard Operating Model v2.xlsx" > model tab, rows 10-42.

Two corkscrews. The loan book rolls BOP + originations - amortization - net
charge-offs. The reserve is pinned to a percent of closing gross loans, and the
provision is whatever expense makes that reserve balance roll forward:

    provision = reserve_eop - reserve_bop + net_charge_offs      (source F40)

so the provision covers the charge-offs taken plus whatever build or release the
target reserve implies. Provision is therefore larger than bare charge-offs in a
growing book.

Amortization and net charge-offs are both struck off the OPENING balance, not
off opening plus originations (source F18, F19).
"""

import argparse
from dataclasses import dataclass

import pandas as pd
import yaml

from models.patterns import average_balance, pct_of, year_end_index

CONFIG_PATH = "config/assumptions.yaml"


# === RESULT ===

@dataclass
class LoansResult:
    bop_balance: pd.Series              # "BOP Balance"
    originations: pd.Series             # "Originations"
    amortization_prepayment: pd.Series  # "Amortization/Prepayment"
    net_charge_offs: pd.Series          # "Net-Charge Offs"
    eop_balance: pd.Series              # "EOP Balance" / "Loans, Gross"
    average_balance: pd.Series          # "Average Balance"
    interest_income: pd.Series          # "Interest Income on Loans"

    loan_loss_reserve: pd.Series        # "Loan Loss Reserve"
    loan_loss_provision: pd.Series      # "Loan Loss Provision"
    loans_net: pd.Series                # "Loans, Net"

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "BOP Balance": self.bop_balance,
            "Originations": self.originations,
            "Amort/Prepay": self.amortization_prepayment,
            "Net Charge-Offs": self.net_charge_offs,
            "EOP Balance": self.eop_balance,
            "Average Balance": self.average_balance,
            "Interest Income": self.interest_income,
            "Loan Loss Reserve": self.loan_loss_reserve,
            "Loan Loss Provision": self.loan_loss_provision,
            "Loans, Net": self.loans_net,
        })


def run(assumptions: dict | None = None) -> LoansResult:
    if assumptions is None:
        with open(CONFIG_PATH) as f:
            assumptions = yaml.safe_load(f)

    horizon = assumptions["horizon"]
    cfg = assumptions["loans"]
    index = year_end_index(horizon["start_year"], horizon["years"])

    # === CALCULATIONS ===
    # Amortization and charge-offs are percentages of the opening balance, which
    # is only known once the book has rolled forward, so roll it period by period.
    bop, eop, amort, nco = [], [], [], []
    reserve_bop, reserve_eop, provision = [], [], []

    balance = float(cfg["gross_balance_opening"])
    reserve = float(cfg["reserve_opening"])
    for _ in index:
        bop.append(balance)
        reserve_bop.append(reserve)

        period_amort = balance * cfg["amort_prepay_rate"]
        period_nco = balance * cfg["net_charge_off_rate"]
        balance = balance + cfg["new_volume"] - period_amort - period_nco

        prior_reserve = reserve
        reserve = cfg["reserve_pct_of_loans"] * balance

        amort.append(period_amort)
        nco.append(period_nco)
        eop.append(balance)
        reserve_eop.append(reserve)
        provision.append(reserve - prior_reserve + period_nco)

    bop_balance = pd.Series(bop, index=index)
    eop_balance = pd.Series(eop, index=index)
    amortization_prepayment = pd.Series(amort, index=index)
    net_charge_offs = pd.Series(nco, index=index)
    loan_loss_reserve = pd.Series(reserve_eop, index=index)
    loan_loss_provision = pd.Series(provision, index=index)

    avg_balance = average_balance(bop_balance, eop_balance)
    interest_income = pct_of(avg_balance, cfg["yield"])
    loans_net = eop_balance - loan_loss_reserve

    result = LoansResult(
        bop_balance=bop_balance,
        originations=pd.Series(float(cfg["new_volume"]), index=index),
        amortization_prepayment=amortization_prepayment,
        net_charge_offs=net_charge_offs,
        eop_balance=eop_balance,
        average_balance=avg_balance,
        interest_income=interest_income,
        loan_loss_reserve=loan_loss_reserve,
        loan_loss_provision=loan_loss_provision,
        loans_net=loans_net,
    )

    # === CHECKS ===
    assert (eop_balance >= 0).all(), "Loan balance went negative: check amort/NCO rates"
    # The reserve corkscrew must close: BOP + provision - charge-offs = EOP.
    reserve_check = (
        pd.Series(reserve_bop, index=index) + loan_loss_provision - net_charge_offs - loan_loss_reserve
    )
    assert (reserve_check.abs() < 1e-9).all(), f"Reserve rollforward does not close: {reserve_check}"

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Loans tab")
    parser.parse_args()

    result = run()
    print("\nLOANS")
    print("=" * 100)
    with pd.option_context("display.float_format", "${:,.1f}".format, "display.width", 160):
        print(result.summary().T)
    print()
