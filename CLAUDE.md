# CLAUDE.md

Python package `abtest` (src layout) for A/B test design and analysis.

## Commands
- Setup: `uv venv .venv && uv pip install -p .venv -e ".[dev]"` (or `pip install -e ".[dev]"`)
- Test: `.venv/bin/pytest -q`
- Lint/format: `.venv/bin/ruff check . && .venv/bin/ruff format --check .` (fix with `ruff format .`)

## Conventions
- Code lives in `src/abtest/`; one module per method family. Export public functions in `__init__.py`.
- Effects are always reported as treatment (B) minus control (A).
- Every public function validates inputs (raise `ValueError`) and has tests in `tests/`.
- Statistical methods must be checked against a known value or a reference implementation
  (e.g. scipy) in tests; simulations must use a fixed seed.
- Keep dependencies to numpy and scipy unless there's a strong reason.

## Apps
- `apps/<name>/` are self-contained Dash apps with their own `requirements.txt` and venv; run them from their folder.
- They are mid-migration onto `abtest`; see `docs/REPO_PLAN.md` before changing their math.
- `apps/sequential_monitor` tests: `python tests/test_sanity.py` from that folder.

## Workflow
- Run tests and ruff before every commit; CI (`.github/workflows/ci.yml`) must stay green.
- Work on a feature branch; don't push directly to `main` unless the owner asks.
