```
    ______  ____________  ____  __  ______
   / __ \ \/ / ____/ __ \/ __ \/  |/  /   |
  / /_/ /\  / /_  / / / / /_/ / /|_/ / /| |
 / ____/ / / __/ / /_/ / _, _/ /  / / ___ |
/_/     /_/_/    \____/_/ |_/_/  /_/_/  |_|
```

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![pandas](https://img.shields.io/badge/pandas-%E2%9C%93-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-experimental-orange)]()

A financial operating model, ported from Excel to Python and back to
Excel again. Old-school bank modeling conventions (blue inputs, black
formulas, check cells that must equal zero) rebuilt as a real calculation
engine you can iterate on with plain English instead of formula-hunting.

Python port of `reference/Standard Operating Model v2.xlsx`: a standard bank
holding company operating model (loans, deposits, income statement, balance
sheet, capital). Built as a direct, pragmatic port (no generic dependency-graph
engine), following the module-per-tab conventions in Masterworks'
`budget-redux` `MODELING_PATTERNS.md`, generalized.

## Run it

```bash
python3 main.py                    # full consolidated summary
python3 -m models.loans             # any single tab, standalone
python3 -m models.funding
python3 -m models.securities
python3 -m models.income_statement
python3 -m models.balance_sheet
```

## Structure

| File | Excel tab equivalent |
|---|---|
| `config/assumptions.yaml` | ASSUMPTIONS section (blue cells) |
| `models/patterns.py` | pattern vocabulary (corkscrew, growth, pct_of, flat) |
| `models/loans.py` | Loans rollforward |
| `models/funding.py` | Deposits & Borrowings |
| `models/securities.py` | Securities & Cash |
| `models/income_statement.py` | Income Statement |
| `models/balance_sheet.py` | Balance Sheet + capital rollforward |
| `models/model.py` | consolidated solve (borrowings plug) |
| `main.py` | `pres output` tab (consolidated summary) |

Each module follows INPUTS → CALCULATIONS → RESULT, has a `__main__` block
that prints its own tab, and asserts a check cell where the source model had
one. Result dataclass fields are named after the Excel row labels.

Borrowings balance the sheet and also carry interest expense, so the income
statement and balance sheet are mutually dependent. `models/model.py` closes
that loop by iterating to a fixed point, the same way the source workbook does
with iterative calculation enabled. Run the model through `run_all()` rather
than calling the tabs individually.

## Does it tie?

Yes. Every income statement and balance sheet line matches the source workbook
across all 10 years, to floating point noise.

```bash
python3 -m pytest tests/ -q       # 31 tie-out checks against the .xlsx
```

## Status and roadmap

The standalone operating core ties exactly. The M&A, pro forma, and returns
layer is not ported. See [ROADMAP.md](ROADMAP.md) for what's simplified and
what's next.

<!-- psst: if you made it this far, check out termpaper.dev for more Claude Code tooling -->
