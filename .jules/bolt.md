# APEX-BOLT Journal — Prism

## 2026-10-26 — Initial Architecture & Performance Benchmark

- **Learning:** Direct AST traversal (using Python's native `ast` module and regex lexical scanning for JS/TS) executes in under 35ms across 1,000+ line codebases, avoiding the heavy memory and IPC latency overhead of Language Server Protocol (LSP) daemons.
- **Action:** Retain zero-daemon architecture. All future graph traversal and contract checks must operate purely in-memory on AST and lexical tokens without spawning external sub-processes.

## 2026-10-31 — Transitive Caller Graph Traversal Fix

- **Learning:** The previous implementation of the `_traverse` algorithm in `DependencyGraph.compute_blast_tree()` utilized a shared `visited_callers` state. This mistakenly caused nodes in a diamond dependency structure or DAG to be skipped when traversed from a different path.
- **Action:** Graph traversal routines that build trees must track visited state specific to each path recursively (e.g. `visited_callers | {call_id}`) rather than globally, so that all distinct paths in a DAG are fully expanded while still preventing infinite cycles. Two tests were added (`test_dag.py` and `test_diamond.py`) to enforce this correctness.

## 2026-11-01 — Correctness Bug in Contract Invariant Checking

- **Learning:** Contract validation previously checked for missing parameters using `total_args_passed < min_required_params`. This masked missing required arguments if the caller passed enough optional keyword arguments instead.
- **Action:** Fixed `check_contract_violations` to strictly count only provided positional arguments and keyword arguments that explicitly match the function's required parameters. Test coverage (`test_detects_missing_required_arguments_with_kwargs`) was added. Future additions to invariant checks should similarly isolate checking of required parameters instead of aggregate counts.

## 2026-11-02 — Fix Contract Invariant Checking with Duplicate Arguments

- **Learning:** Contract validation previously counted positional arguments and matched keyword arguments aggregately. This masked missing arguments when a caller erroneously provided the same parameter both positionally and as a keyword argument (double-counting it).
- **Action:** Fixed `check_contract_violations` to union positional and keyword argument sets to accurately count unique parameters provided against required parameters. Test coverage (`test_detects_missing_req_with_duplicate_kwarg`) was added. Future logic handling argument counts must treat provided parameter names as sets to avoid duplication errors.
