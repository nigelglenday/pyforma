# Roadmap

## Verified against the source

The loans corkscrew was checked line-by-line against year 1 and year 2 of the
source `model` tab (BOP 1350 -> EOP 1466.5 -> EOP 1558.5, interest income
$77.45 -> $83.19). Matches exactly. Everything downstream of loans
(securities, funding, income statement, balance sheet) is a fresh build using
the same pattern vocabulary, not a line-by-line port.

## Deliberate simplifications (read before extending)

This was built in a ~60-minute timebox. What's real vs. approximated:

1. **Loans**: real port, verified against source formulas. Aggregate rollforward
   only. The source model's vintage-level cohort matrix (`loan` tab, each
   origination year amortizing on its own schedule) was **not** ported. If you
   want vintage-level detail back, that's the next real piece of work.
2. **Securities**: sized as a flat % of the loan book, not as a target % of
   total assets. The source model's version creates a circular reference
   (securities sizing depends on total assets, which includes securities).
   Sidestepped rather than solved. Revisit with a convergence loop if the
   distinction matters for your use.
3. **Cash is a balancing plug**, not modeled from a cash flow statement. This
   guarantees the balance sheet balances but means cash isn't really "modeled."
   It's solved for. Fine for illustrative purposes, not fine if you need to
   reason about actual liquidity.
4. **No loan loss reserve line**: net charge-offs flow straight through as
   the provision expense, with no separate reserve build/release rollforward.
5. **No M&A / target acquisition / pro forma / IRR-MOIC layer.** The source
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
   the `financial-modeling` skill (`.claude/skills/financial-modeling/SKILL.md`
   in this repo): blue/black/green/orange/red color contract, single input column with time
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
