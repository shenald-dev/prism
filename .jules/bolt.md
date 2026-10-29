# APEX-BOLT Journal — Prism

## 2026-10-26 — Initial Architecture & Performance Benchmark

- **Learning:** Direct AST traversal (using Python's native `ast` module and regex lexical scanning for JS/TS) executes in under 35ms across 1,000+ line codebases, avoiding the heavy memory and IPC latency overhead of Language Server Protocol (LSP) daemons.
- **Action:** Retain zero-daemon architecture. All future graph traversal and contract checks must operate purely in-memory on AST and lexical tokens without spawning external sub-processes.

## 2026-10-31 — Transitive Caller Graph Traversal Fix

- **Learning:** The previous implementation of the `_traverse` algorithm in `DependencyGraph.compute_blast_tree()` utilized a shared `visited_callers` state. This mistakenly caused nodes in a diamond dependency structure or DAG to be skipped when traversed from a different path.
- **Action:** Graph traversal routines that build trees must track visited state specific to each path recursively (e.g. `visited_callers | {call_id}`) rather than globally, so that all distinct paths in a DAG are fully expanded while still preventing infinite cycles. Two tests were added (`test_dag.py` and `test_diamond.py`) to enforce this correctness.
