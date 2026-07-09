# Roadmap

## Verified against the source

**The operating core ties exactly.** Every line of the income statement and
balance sheet matches the source `model` tab across all 10 years, to floating
point noise (worst absolute difference 4.5e-13). Year 1 net income $20.5961,
borrowings $234.3657, common equity $168.3875, all identical to the workbook.

Reproduce with the tie-out check in `tests/`, or against
`reference/Standard Operating Model v2.xlsx` directly.

Three things the earlier port got structurally wrong, now fixed:

- **Borrowings are the plug, not cash.** Cash is a modeled line growing at the
  other-asset rate. The port had inverted this, making cash the residual, which
  produced a cash balance ballooning to a quarter of assets and an entirely
  artificial earnings rollover.
- **Securities are not circular.** They are a target percent of total assets,
  solved in closed form: `S = A * p / (1 - p)`. No convergence loop needed.
- **Fee income is grossed up** to a share of total revenue, not multiplied
  against net interest income.

## Deliberate simplifications (read before extending)

1. **Loans**: aggregate rollforward only. The source model's vintage-level
   cohort matrix (`loan` tab, each origination year amortizing on its own
   schedule) was **not** ported. If you want vintage-level detail back, that's
   the next real piece of work.
2. **Borrowings go negative from 2021.** Deposits compound at 5% while assets
   grow more slowly, so the plug flips to excess funding (-$279 by 2022). This
   is faithful to the source, which does the same thing. It is still not a
   balance sheet any real bank runs. Fixing it means giving the model a
   deployment policy (cap the excess, then buy securities or return capital)
   rather than letting a single plug absorb the mismatch.
3. **No M&A / target acquisition / pro forma / IRR-MOIC layer.** The source
   model's second half (rows ~200-408: transaction assumptions, acquired P&L,
   pro forma combination, investor returns, sensitivity table, Gordon Growth
   valuation) was not touched. This port covers only the standalone operating
   core.
6. **Inputs are YAML, not an Excel input workbook.** This diverges from the
   `MODELING_PATTERNS.md` standard, which specifies Excel-as-input (so a
   human owns the number and the rationale next to it). YAML was faster to
   ship in the time available. Revisit if you want the commentary-alongside-
   number property, or if you want this project's inputs to be directly
   editable by a non-technical user without touching a text file.
7. **No Excel writer.** Output is a terminal table only. "Export back to the
   same format" (the fourth thing from the original ask) is not built.

## What's genuinely done

- Full loans -> securities -> funding -> income statement -> balance sheet
  chain, 10-year horizon, runs end to end.
- Balance sheet balances exactly (assets = liabilities + equity) every year,
  checked via `assert` in `balance_sheet.py`.
- Every module runs standalone and prints its own tab.
- Named pattern vocabulary (`corkscrew`, `growth`, `pct_of`, `flat`) used
  consistently, same four patterns cover the entire model.

## Next steps, roughly in order of value

1. Vintage-level loan schedule (the real `loan` tab).
2. Proper securities-as-%-of-assets with a convergence loop (or explicitly
   decide the flat-%-of-loans simplification is fine and stop flagging it).
3. Capital ratios tab (Tier 1, leverage, TCE): straightforward `pct_of`
   patterns once RWA buckets are defined.
4. Excel writer, matching `pres output` tab layout. When building this, follow
   the `financial-modeling` skill (`/Users/moonpie/.claude-mw/skills/financial-modeling`):
   blue/black/green/orange/red color contract, single input column with time
   series flowing right, elevator-shaft empty left column, dark-blue section
   headers spanning full width, parentheses for negatives, dashes for zero,
   no merged cells. That skill's closing "stranger test" is word-for-word the
   same four questions as Appendix B of `MODELING_PATTERNS.md`, so the two
   standards are already aligned, this one just covers the Excel-side detail
   the other doesn't. It's also the natural argument for revisiting
   simplification #6 (YAML vs. Excel inputs): a proper single input column
   with the value and its rationale side by side is exactly the property an
   Excel input workbook gets you that YAML comments don't.
5. M&A layer, if that's ever actually needed for this exercise's purpose.
