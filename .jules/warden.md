## 2026-11-03 — Lifecycle & Assurance Ledger
- **QA & Veto Actions:** Verified tests passing and typechecker clean.
- **Entropy Pruned:** Removed dead fallback check logic in `src/prism/core/contracts.py` since `supplied_params` is correctly handled. Checked that `ignore_paths` and `parent_class` attributes were cleanly removed from the codebase.
- **Deferred / Blocked:** None.
- **Entropy Pruned:** Removed unused `max_impact_score` config property and parsing logic, and removed unused `get_centrality` method from `DependencyGraph` (-10 lines).
- **Entropy Pruned:** Removed unused `class_hierarchy` property and population logic from `DependencyGraph`.
