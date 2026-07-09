# pyforma

A Python port of a bank holding company operating model, originally ported
from `reference/Standard Operating Model v2.xlsx`. Public repo:
https://github.com/nigelglenday/pyforma (MIT, main branch).

Read `README.md` (what it is, how to run it) and `ROADMAP.md` (what's
verified against the source, what's deliberately simplified and why, what's
next) before touching the model. Don't restate their contents here; they are
the canonical description and they drift.

## Running the model

```bash
python3 main.py                    # full consolidated summary
python3 -m models.loans             # any single tab, standalone
python3 -m pytest tests/ -q         # tie-out checks against the source .xlsx
```

## Conventions

Module-per-tab, generalized from Masterworks' `budget-redux`
`MODELING_PATTERNS.md` (docs plus a `budget-modeling-patterns` skill live on
the unmerged `modeling-patterns-foundation` branch of
`MasterworksIO/SPV-Finance`). Not copied verbatim; generalized.

- Named pattern vocabulary lives in `models/patterns.py`: `corkscrew`
  (BOP + adds - subs = EOP), `growth`, `pct_of`, `flat`. Those four cover the
  whole model. Reach for a new pattern only when none of them fits.
- Every module has INPUTS / CALCULATIONS / RESULT sections, a `__main__` block
  that prints its own tab standalone, and an assert check cell wherever the
  source workbook had one.
- `Result` dataclass fields are named after the source Excel row labels.

## Skills

Two skills live in `.claude/skills/`:

- **`financial-modeling`**: Excel formatting conventions (blue/black/green/
  orange/red color coding, single input column, elevator-shaft empty left
  column, dark-blue full-width section headers, parentheses for negatives,
  dashes for zero, no merged cells). Use this when building the Excel writer
  (roadmap item 4) or any other spreadsheet output.
- **`python-modeling-patterns`**: the Python-side conventions above,
  generalized into a standalone skill. Use this when adding a new line item
  or module.

## Ground rules

- No em dashes anywhere: code, comments, docs, terminal output, commit messages.
- Always work on a branch. Never commit directly to `main`.
- Smallest possible change. Ask before destructive git operations.
- The build was a ~60-minute timebox. Every dollar figure in the model is a
  generic template number, not real Masterworks financials, unless Nigel says
  otherwise. Don't present output as though it means something about the business.
