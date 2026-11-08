## 2024-03-24 — Test
- **Learning:** Memory check
- **Action:** Memory check

## 2026-11-03 — Contract Argument Double Counting
- **Learning:** When validating missing parameters, simple additive totals (args + len(kwargs)) result in double counting if a caller erroneously passes the same parameter both positionally and as a keyword, causing missing argument invariants to fail silently.
- **Action:** Treat supplied parameter bindings strictly as sets to correctly measure the true count of unique arguments populated against the signature contract.

## 2026-11-03 — get_direct_callers filtering fix
- **Learning:** `get_direct_callers` previously appended call sites targeting different modules into the returned scoped calls because of an unneeded `else` statement. This resulted in O(N) filtering failures when multiple modules had identically named symbols.
- **Action:** Removed the `else` statement to ensure that only calls meant for the relevant symbol module are returned.

## 2026-11-03 — Transitive Blast Tree Scoping
- **Learning:** When calculating the transitive blast tree of a target symbol, traversing by string names without tracking the actual `Symbol` references caused identical names across different modules to merge their transitive callers, causing large filtering failures (O(N)).
- **Action:** Recursively pass `Symbol` objects inside `_traverse` (and use `get_direct_callers`) instead of generic string names to correctly scope recursive dependencies.

## 2026-11-06 — Command Injection & Spacing fix for Test Runner
- **Learning:** Using `.split()` to parse test execution commands dynamically constructed with Python's space-delimited string interpolation opens up shell execution vulnerabilities when dealing with filenames that contain spaces, leading to incorrect command tokenization or execution failures.
- **Action:** Test runner outputs like `recommended_command` must be strictly constructed and passed as a `List[str]` directly into `subprocess.run()`, completely avoiding intermediary `.split()` operations.

## 2026-11-06 — Config parsing robustness
- **Learning:** Unhandled ValueError when parsing specific config values in `from_dict` aborted all config loading.
- **Action:** Enclose each config cast in try-except to gracefully fall back to defaults for invalid types.
