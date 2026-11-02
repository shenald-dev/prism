## 2024-03-24 — Test
- **Learning:** Memory check
- **Action:** Memory check

## 2026-11-03 — Contract Argument Double Counting
- **Learning:** When validating missing parameters, simple additive totals (args + len(kwargs)) result in double counting if a caller erroneously passes the same parameter both positionally and as a keyword, causing missing argument invariants to fail silently.
- **Action:** Treat supplied parameter bindings strictly as sets to correctly measure the true count of unique arguments populated against the signature contract.
