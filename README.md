# Unclaimed Property Tracker

A starter tool for tracking when customer balances, including crypto, become unclaimed property, which state they go to, and when owner notices have to go out.

## Why I built this

At a fintech or crypto company that holds customer balances, unclaimed property (escheatment) is easy to lose track of. Every state has its own dormancy period, notice window, and report deadline, and states are still deciding how to handle virtual currency. Some want the crypto itself and some want it sold first.

My background is BSA/AML at banks, fintech, and a crypto money transmitter. I haven't run an escheatment program myself, so I built this to work through the moving pieces the same way I'd set up licensing or CTR tracking: one table of rules by state, and a check that tells you what's due and when.

## What it does

For each account, the checker works out:

- **Which state gets it.** It follows the priority rules from *Texas v. New Jersey*: the state of the owner's last known address first, and if there's no address, the company's state of incorporation.
- **When it's presumed abandoned**, based on the last time the owner did something with the account and that state's dormancy period.
- **Which report it lands on** and the due date.
- **When the owner notice has to go out**, whether it's required at all (dollar thresholds vary), and whether certified mail is needed.
- **How the state wants crypto delivered:** in kind, or sold first.

Statuses: `SEND NOTICE NOW`, `APPROACHING` (within a year), `ACTIVE`, `OVERDUE`, and `OUT OF SCOPE` for states not in the table yet.

## Starter states

Five states to start: Delaware (a common state of incorporation, so it matters for the priority rule), New York, California, Texas, and Florida.

| State | Cash dormancy | Crypto dormancy | Report due | Crypto delivered |
| --- | --- | --- | --- | --- |
| Delaware | 5 years | 5 years | March 1 | Sold within 90 days before filing |
| New York | 3 years | 5 years (clock started Nov 22, 2022) | March 10 (cash), Nov 10 (crypto) | Per state instructions |
| California | 3 years | 3 years (law effective Jan 1, 2026) | Notice Report before Nov 1 | In kind |
| Texas | 3 years | 3 years | July 1 | In kind if the holder controls the keys |
| Florida | 5 years | 7 years | Before May 1 | Sold within 30 days before filing |

Every rule, with notes and the source it came from, is in [`data/state_rules.csv`](data/state_rules.csv). Dormancy periods vary by property type, so the cash column uses the general or most relevant period for customer balances.

## How to run it

Python 3, no extra packages.

```
python tracker/check.py --holder-state DE --as-of 2026-11-23
python -m unittest discover -s tests
```

Results go to `reports/results.csv` and `reports/sample_run.md`. See the [sample run](reports/sample_run.md).

## Limits

- This is a starter set of five states, not legal advice. Rules change, and some property types have their own periods.
- Sample accounts are made up.
- Edge cases like securities, foreign addresses, and aggregate reporting aren't covered yet.
- Anything close to a call (does this balance count, which state has priority) goes to legal.

## Next steps

- Add the rest of the states, starting with where customers are concentrated.
- Track rule changes over time, the way my [state licensing tracker](https://github.com/angelalara1219/state-mt-licensing-tracker) does.
- Flag accounts that need a returned-mail check, since undeliverable mail can start the dormancy clock in some states.
