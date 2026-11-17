# Compact rules — paste into the session

- Project root: «PROJECT_ROOT» (verify it exists first; stop if missing).
- `«LEGACY_FOLDER»/` is a read-only legacy bootstrap reference: gitignored,
  never imported, never deleted.
- Research first, plan, wait for the go-ahead. Resource caps: «CPU/RAM/GPU
  caps as stated by the user».
- Structure: `src/«pkg»/{data,processing,ui}` — data: no Dash; processing:
  pure NumPy/JAX, no UI; ui: `build_app(...)` factory, callbacks testable
  without a browser.
- Data paths are runtime variables, never hardcoded.
- Look: dbc DARKLY, navbar accent «#4196B4», fluid container, main view
  left (5 cols) / detail view right (7 cols).
- JAX CPU default, float64 reductions; GPU opt-in marked NOT TESTED until
  verified; report selected devices, never fall back silently.
- Every milestone: small pytest suite; UI tested via callback functions.
- Docs: operational_plan.md / to_do.md / timeline.md / scientific_notes.md;
  README marks verified vs UNVERIFIED.
- End of task: what changed, what was verified (real output), what's left;
  close with 1–2 lines: skipped / unchecked + risk.
