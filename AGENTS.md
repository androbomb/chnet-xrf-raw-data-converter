# AGENTS.md — agent rules

This file tells the coding agent how to work in this repository. Read it fully
before changing anything.

## 0. Verify paths first (bootstrap step)

- On the first touch, verify the project root and every path the user
  referenced actually exist on THIS machine (`ls` / `stat`). If a path is
  missing, stop and ask — do not continue silently on a different path.
- New or scope-changing work: research first, present a plan, wait for an
  explicit go-ahead before executing.
- Respect the user's resource caps (CPU/RAM/GPU) as stated in the session;
  keep compute within the stated caps and report what you measured. No caps
  were stated for this project yet; default to single-threaded runs and
  report wall time + RAM peak for anything over ~100 MB.

## 1. Lean code by default

- The best code is the code never written; take the first option that fully
  works: existing codebase pattern > stdlib > installed dependency > new code.
- Before writing, list every place the change must reach: callers, tests,
  fixtures, config, exports. Check what the change could break.
- No abstraction, wrapper, option, config, boilerplate or "for later" code
  nobody asked for. Keep values in the form the platform already gives you.
- Comment only the why the code cannot show, in one line.
- Shortcut with a known limit: code comment
  `shortcut: <the limit>, <when to upgrade>`.
- Lazy code without its check is unfinished: new non-trivial logic (a branch,
  a loop, a parser, money or security, a new script) ships with one small
  test or an assert-based self-check.
- Bug fix: before editing, grep every caller of the function you touch; fix
  the root cause once in the shared code.
- Never cut: validation at trust boundaries, error handling that prevents
  data loss, security, accessibility, anything the user asked for.

## 2. Bootstrap from legacy (read-only reference)

- `original_code/` is a legacy bootstrap reference: gitignored, examined
  read-only. Do NOT import from it in the new runtime. Do NOT delete it.
  It is a REFERENCE, not a scientifically correct implementation: replicate
  only what `legacy_audit.md` section 2 (differences) approves, and never
  its silent data loss.
- The repository is the code repo, not the data location: data paths are
  runtime variables (CLI args / env vars), never hardcoded absolute paths.
- On sample data files: examine only metadata and small samples in-session;
  mass loads (full pipeline runs) only inside an approved milestone (M4).

## 3. Project snapshot (M0 — original requirements verbatim)

User request (2026-11-17, Telegram):
> "Voglio aggiornare il progetto raw-xrf-to-h5-opener-python, usando il
> template generico corretto come base organizzativa. Il codice legacy
> fornito è un riferimento da preservare, non un'implementazione
> scientificamente corretta da replicare automaticamente. La working
> directory è SOLO /workspace/exchange/xrf-raw-converter. Il codice
> originale, da gitignorare dopo averlo analizzato, è in
> original_code/. In data_example/ trovi due files di esempio, uno XML con
> metadati e uno 'solo data'. Leggi i file del progetto e le regole
> applicabili. Inizia con un M0 in sola lettura e restituisci un piano
> concreto. Dopo l'approvazione, implementa autonomamente entro lo scope
> concordato, senza richiedere conferme per ogni modifica ordinaria.
> [Documenti richiesti: AGENTS.md, operational_plan.md, legacy_audit.md,
> data_format.md, output_schema.md, scientific_notes.md, README.md, to_do.md,
> timeline.md. M0 deve distinguere ciò che è dimostrato dal codice da ciò
> che richiede esempi o conferma dell'utente. Non pubblicare su PyPI, non
> fare push e non eliminare il legacy.]"

**Emendamento contratto (2026-11-17, utente)**: il push verso GitHub
(origin) è **consentito** — si pusha a ogni chiusura milestone; resta
**bloccato solo il push verso PyPI/TestPyPI**.

Goal: una libreria + CLI snella e testata che converte raw MA-XRF
(Fi MA-XRF, INFN-CHNet) in NPZ/HDF5 (cubo `(y, x, channel)` + assi + mask +
metadati), con calibrazione energia element-identical (`energy[i]=m·i+q`,
conteggi element-identical, niente resampling), NC esplicita (default
16384, sovrascrivibile) e rebin esplicito (sum/mean) OFF di default.
Niente auto-rebin/auto-crop. Data paths: argomenti CLI; esempi in
`data_example/` (gitignored). UI minimale (Dash, embeddabile in Jupyter)
nella milestone M5, dopo M4.

## 4. Scientific rigor (invariants — XRF-specific)

- **Conservazione dei conteggi**: nessun passo perde eventi silenziosamente.
  `populate`: `sum(cube) == n_events`. `calibrate`: somma conservata dentro
  E_range (binning per somma, mai overwrite — legacy_audit L4). `rebin` sum:
  somma conservata; `rebin` mean è dichiarata come media per gruppo.
- Legacy ≠ riferimento scientifico: ogni deviazione documentata in
  `legacy_audit.md` §2 e in `scientific_notes.md`.
- dtype: uint32 per il cubo (default, opzione utente; overflow uint16
  legacy, L10), float64 per griglie energia e aritmetica.
- NC (n° canali) è la profondità ESATTA del cubo: l'output è sempre
  (h, w, n_channels); default strumentale 16384, sovrascrivibile via
  opzione/metadati — mai `max(observed)+1`. Se il max canale osservato la
  supera, `XRFReadError` con la potenza di 2 successiva come suggerimento
  (profondità MCA = potenza di 2); per ridurre la profondità si usa il rebin
  esplicito (`rebin`, o `rebin_to` a profondità target) — niente snap,
  niente troncamento silenzioso (emendamento 2026-11-17, sostituisce lo
  snap `n_channels_snapped` dell'emendamento precedente).
- Rebin: solo se esplicitamente richiesto (sum/mean), off di default,
  dichiarato nei metadati di output; mai auto-applicato.
- Unità coordinate: µm (X/Y) e µm/s (velocity) — marcate "assumed"
  nei metadati finché non confermate strumentalmente (N4).
- Ogni quantità derivata dai dati (assi, unità, calibrazioni) ha una fonte
  documentata: `data_format.md` / `scientific_notes.md`; ciò che è
  ASSUNTO (es. unità µm) resta marcato finché l'utente non conferma.

## 5. Limited testing discipline

- Every milestone ships with a small pytest suite; the M5 minimal UI gets
  headless tests (no browser required, Jupyter-embeddable).
- Numerics: property tests for conservation (F2-F4) + hand-computed tiny
  cases; legacy-semantics parity (mean mode) tested on synthetic data.
- No browser, no live server needed: everything is callable headless.
- Record results (date, count, status) in `to_do.md` verification log.

## 6. Resource awareness

- Single-threaded by default (no process pool — legacy pool had bugs, L6/L12).
- Watch RAM on full-file runs (datacube uint32, NC=16384 ≈ 1.9 GB per the
  284 MB file + streaming overhead); report what you measured in the
  verification log.

## 7. Documentation ownership

- `operational_plan.md` = decisions, milestones, acceptance criteria, open
  questions.
- `legacy_audit.md` = verified legacy problems + intended differences.
- `data_format.md` = input grammar. `output_schema.md` = output contract.
- `to_do.md` = Now / Next / Later / Blocked + verification log.
- `timeline.md` = dated, append-only decisions and changes.
- `scientific_notes.md` = conventions with claim/source/date.
- Keep the README honest: mark UNVERIFIED vs verified.

## 8. Reference-project lessons (applicability)

The generic template ships Dash 4.x/JAX lessons (UI, jupyter_mode,
cross-selection). The minimal UI landed in M5 (2026-11-17, user decision
N2): `xrfraw.ui.build_app()` (Dash 4.5 + dbc 2.0.4, DARKLY, accent
#4196B4), embeddabile con `app.run(jupyter_mode="inline")` (nativo Dash
4.5, no pacchetto `_jupyter` separato); `dash-xrf-visualizer` resta il
riferimento. Verificato su Dash 4.5: niente `dbc.Code`/`dbc.H4` (usare
`dash.html`), `dev_tools_offline` è un arg del costruttore (non di
`run()`), il layout è fatto di oggetti componente (test headless: walk
via `to_plotly_json()`). No JAX here.

## 9. Safety and honesty

- No fabricated output. If a step cannot be verified here (no Docker
  daemon, no `gh` CLI), say so and mark it NOT VERIFIED / NOT TESTED.
- Git push verso origin: **consentito** (emendamento 2026-11-17) — push a
  ogni chiusura milestone.
- PyPI/TestPyPI releases are immutable: never reuse a published version.
  PyPI publishing remains **forbidden** in this phase — local builds only.
- Do not touch files the user modified that are out of scope.

## 10. End-of-task report

- Report what changed, what was verified (with real output), what is left.
- Close with one or two lines: what you skipped or did not check, and the
  risk the user must know.