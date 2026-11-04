## 2024-03-24 — Test
- **Learning:** Memory check
- **Action:** Memory check

## 2026-11-03 — Contract Argument Double Counting
- **Learning:** When validating missing parameters, simple additive totals (args + len(kwargs)) result in double counting if a caller erroneously passes the same parameter both positionally and as a keyword, causing missing argument invariants to fail silently.
- **Action:** Treat supplied parameter bindings strictly as sets to correctly measure the true count of unique arguments populated against the signature contract.

## 2026-11-03 — get_direct_callers filtering fix
- **Learning:** `get_direct_callers` previously appended call sites targeting different modules into the returned scoped calls because of an unneeded `else` statement. This resulted in O(N) filtering failures when multiple modules had identically named symbols.
- **Action:** Removed the `else` statement to ensure that only calls meant for the relevant symbol module are returned.
