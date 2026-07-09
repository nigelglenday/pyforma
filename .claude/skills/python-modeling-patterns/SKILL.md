---
name: python-modeling-patterns
description: Use when translating a spreadsheet-based financial or operational model into Python, or when adding a new line item, schedule, or calculation to a model already built this way. Covers module-per-tab structure, a real date index, the named pattern vocabulary for common line-item shapes (corkscrew, growth, pct_of, multiple_of, flat), and keeping human-owned inputs separate from computed results.
tags: [finance, python]
---

# Python Modeling Patterns

A spreadsheet is good at two things at once: it's where a human types a
number, and it's where that number gets used in a formula. That's also its
weakness. Once inputs and calculations live in the same cells, a single edit
can silently break something three tabs away, and there's no real record of
what changed or why.

This skill is for the alternative: keep Excel (or a config file) as the
input and display surface, and move every calculation into Python, where it's
readable, testable, and has a real audit trail (git). The goal is a Python
model that anyone who's built the equivalent spreadsheet can still navigate,
even if they've never written Python before.

## The core rule

**Every value is either an input or a calculation, never both.** An input is
a number a human typed and might change (a rate, a growth assumption, a
schedule). A calculation is code that derives a value from other values. If
you find yourself typing a percentage, rate, or dollar amount directly inside
a calculation, stop. Pull it out into a named input.

This is the same blue/black contract a well-built spreadsheet uses: blue
cells are typed, black cells are formulas. In Python, that maps to config
(YAML, or an input workbook) for the blue cells, and code for the black ones.

## Structuring modules like tabs

Give each distinct piece of the model, the thing that would get its own tab
in the spreadsheet, its own Python module. If a section of the model would
be a header within a tab rather than a whole tab of its own, it's a function
within a module, not a separate file.

Inside each module, read top to bottom the way a well-organized tab does:

```
# === INPUTS ===
# Load assumptions from config. These are the human-owned values.

# === CALCULATIONS ===
# Pure functions deriving results from inputs and other modules' results.

# === RESULT ===
# A typed container (e.g. a dataclass) that other modules import.
```

Name the fields of that result container after the row labels the source
model uses. If the spreadsheet calls something "Total Management Fee
Revenue," the field is `total_management_fee_revenue`, not `fee_total`. The
goal is that someone reading the spreadsheet and the Python side by side can
map between them without a lookup table.

Give every module a way to print itself standalone (a `__main__` block, or an
equivalent CLI entry point). Running that module alone should show you its
"tab" in isolation. This is the main way to inspect the model without
reading five files at once.

## Checks

A well-built spreadsheet has check cells: a value that should always equal
zero, flagged if it doesn't. The Python equivalent is an `assert` at the end
of a calculation, or a dedicated validation function. Put a check anywhere
the source model had one (a balance sheet that must balance, a rollforward
that shouldn't go negative), and add new ones anywhere a silent error would
be easy to miss.

## Use a real date index, not strings

Build the model's time axis from actual dates (a real date type, e.g.
pandas' `DatetimeIndex`), never from hand-built strings like `"2026-01"`.
String-keyed time series force you to reimplement basic date logic by hand:
detecting quarters by splitting a string, hardcoding "12 periods per year,"
manually shifting month labels. A real date index gets you rollups
(monthly to quarterly to annual), date arithmetic, and clean joins to
external data for free, and it doesn't quietly break the day you add a
partial year or change the horizon length.

Format dates to something readable ("Jan-26") only when displaying them to a
human. Never compute on the formatted string.

## The pattern vocabulary

Most line items in a financial or operational model are one of a small
number of recurring shapes. Naming them makes the model's logic scannable:
you can tell what a line does from its pattern name before reading the
formula.

| Pattern | Shape | Use for |
|---|---|---|
| **corkscrew** | `close(t) = open(t) + additions(t) - subtractions(t)`; `open(t) = close(t-1)` | Any balance that rolls forward: cash, AUM, a reserve, an equity balance |
| **growth** | `value(t) = value(t-1) * (1 + rate)` | A line that compounds at its own rate |
| **linked_growth** | grows at the same rate as another line | A line that should move proportionally with a driver |
| **pct_of** | `value(t) = pct * driver(t)` | A cost or fee defined as a percentage of something else |
| **multiple_of** | `value(t) = multiple * driver(t)` | Headcount times cost-per-head, units times price |
| **flat** | `value(t) = value(t-1)` | A line that doesn't change period to period |
| **trailing_average** | mean of a driver over a window | Smoothing a noisy run-rate |
| **input** | `value(t) = input(t)` | The blue cells: a human-owned number or schedule |

Reach for a general expression (any arithmetic over other lines, prior
values, and inputs) only when none of the named patterns fit. The named
patterns aren't a closed set. They're readable shorthand for common shapes.
When you find yourself writing the same custom expression a third time,
give it a name, add it to this table, and use the name everywhere after.

## Two kinds of dependency

A line can depend on another line's value in the *same* period, or on a
value from a *prior* period. These behave differently:

- **Same-period dependencies must not form a loop.** If line A depends on
  line B, which depends on line A, in the same period, that's an error, not
  a spreadsheet-style circular reference to resolve iteratively.
- **Prior-period dependencies are expected and are how balances roll
  forward.** A corkscrew's opening balance this period is its closing
  balance last period. That's not a cycle, it's the mechanism.

The one genuinely circular case that comes up in practice is something like
a revolving credit facility, where a period's cash position determines a
draw, which determines interest expense, which feeds back into cash. If you
hit a real version of this, either model the disputed line as a schedule
input (turning the decision into an assumption instead of a derived value,
which usually reflects reality better anyway) or resolve it with an explicit
convergence loop: iterate, check how much the value moved, stop once it's
within a defined tolerance, and fail loudly if it never settles.

## Before you write a line, answer three questions

- **Is this an input or a calculation?** If it's a number someone might
  reasonably want to change, it's an input, and belongs in config, not in
  code.
- **What does it reference?** Name the other lines it depends on explicitly.
  A hidden dependency is a spreadsheet with a broken formula waiting to
  happen, just in Python instead.
- **What are its parameters?** Every rate, percentage, and schedule should
  be a named, visible input, not a literal buried in a function.

## Red flags

- Building a list of period labels by hand (`["2026-01", "2026-02", ...]`)
  instead of a real date range.
- Asserting a fixed number of periods (`assert len(values) == 12`), which
  breaks the moment the horizon changes.
- Detecting quarter- or year-end by checking whether a string ends in a
  particular substring.
- A percentage, rate, or dollar figure typed directly into a calculation
  instead of pulled from a named input.
- A line that references another line in the same period that eventually
  references it back.

Any of these is worth stopping and fixing before it becomes load-bearing.
