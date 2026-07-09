# Classes, objects, `self`, and `__init__`

A plain-language walkthrough, using `SecuritiesResult` from `models/securities.py`
as the running example. No prior programming background assumed.

## The problem classes solve

Say you want to represent "the securities balance and its interest income" as
one thing you can pass around. Without classes, you might just use a
dictionary:

```python
result = {"balance": my_balance_series, "interest_income": my_income_series}
result["balance"]  # access it
```

That works for one of these. But this project has five (loans, securities,
funding, income statement, balance sheet), and each has 5-10 fields.
Dictionaries let you typo a key name (`result["balence"]`) and Python won't
catch it until something crashes downstream, possibly far from where the typo
happened. A **class** is Python's way of saying "this exact shape of data has
a name, and here are its exact fields." It's closer to defining a named range
or a structured table in Excel than to a loose grab-bag of cells.

## What a class actually is

A class is a blueprint. It doesn't hold any data itself. It describes what a
"thing built from this blueprint" will look like.

```python
class SecuritiesResult:
    def __init__(self, balance, interest_income):
        self.balance = balance
        self.interest_income = interest_income
```

This says: "A `SecuritiesResult` is a thing that has a `balance` and an
`interest_income`." That's it. It's a shape, not a value.

## What an object (or "instance") is

Once you have the blueprint, you can stamp out actual things from it:

```python
result = SecuritiesResult(balance=my_balance_series, interest_income=my_income_series)
```

`result` is now a real, concrete thing built from the `SecuritiesResult`
blueprint, holding your actual data. If you did this five times with five
different sets of numbers, you'd have five separate `SecuritiesResult`
objects, each with its own `balance` and `interest_income`, not sharing data
with each other. Same relationship as "a pivot table template" vs. "the
actual pivot table you built from it with this quarter's numbers."

## What `self` is

This is the part that trips almost everyone up at first, so slow down here.

When Python builds `result` from the line above, it needs to know *which*
object it's currently filling in. `self` is just a placeholder name for "the
specific object being built or used right now." It is not a keyword with
magic powers. It's a plain parameter name, by convention always called
`self`.

So when `__init__` runs, Python effectively does this under the hood:

```python
result.balance = my_balance_series          # self.balance = balance, where self is "result"
result.interest_income = my_income_series   # self.interest_income = interest_income
```

`self` inside the class definition is just "whatever object we end up calling
this on." You never pass it yourself. Python fills it in automatically.
That's why `__init__(self, balance, interest_income)` has three parameters in
the definition but you only supply two when you call it
(`SecuritiesResult(balance=..., interest_income=...)`). Python quietly hands
over `self` for you.

## Why `__init__` specifically

`__init__` is just the name Python reserves for "run this automatically the
instant an object gets created." You could technically build an object and
set its fields one at a time afterward, but `__init__` lets you guarantee
every `SecuritiesResult` is created with both fields filled in from the
start. No half-built objects floating around.

## Tying it back to the actual code

```python
def run(...) -> SecuritiesResult:
    ...
    return SecuritiesResult(balance=balance, interest_income=interest_income)
```

`run()` computes the numbers, then packages them into one `SecuritiesResult`
object and hands that back. Anywhere else in the codebase that calls
`run_securities(...)` gets back one clean object with `.balance` and
`.interest_income` on it, instead of having to remember "the third thing
this function returns is the interest income series." That's the entire
payoff: a class is a way to give a bundle of related data a name and a fixed
shape, so the rest of the code can rely on it instead of guessing.

## `@dataclass`: the same thing, without writing `__init__` by hand

Look at the real code in `models/securities.py`:

```python
@dataclass
class SecuritiesResult:
    balance: pd.Series          # "Securities and Cash"
    interest_income: pd.Series  # "Interest Income"
```

This is doing exactly the same job as the manual version above.
`@dataclass` is a decorator: an instruction to Python that says "before you
finish building this class, auto-generate the boilerplate `__init__` (and a
few other methods) from the field list below." You list the field names and
their types, and Python writes the "store this on the object" code for you.
It is not a different concept, just a shortcut for the common case where all
`__init__` does is copy its arguments onto `self`.

The comments (`# "Securities and Cash"`, `# "Interest Income"`) aren't code.
They're notes tying each field back to the row label it corresponds to on the
original Excel tab this was ported from.

## And `summary()`

```python
def summary(self) -> pd.DataFrame:
    return pd.DataFrame({
        "Securities & Cash Balance": self.balance,
        "Interest Income": self.interest_income,
    })
```

This is a method: a function that lives inside the class and automatically
receives `self` (the object it's called on) as its first argument. When you
call `result.summary()`, Python fills in `self` with `result` for you, the
same way it does for `__init__`. Inside the method, `self.balance` and
`self.interest_income` are the two Series you stored when the object was
created. `pd.DataFrame({...})` takes a dict where each key becomes a column
name and each value (a Series) becomes that column's data, aligned by their
shared date index. The result is a printable table, used when a module runs
standalone (`python3 -m models.securities`) and needs to show its tab.
