# Repository plan

How experimentation work is organized across GitHub repos.

## Target structure

| Repo | Scope | Status |
|---|---|---|
| **experimentation_ab_testing** (this repo) | Randomized controlled experiments (A/B tests): design, analysis, sequential monitoring, apps | Active |
| **causal_inference_observational** | Uncontrolled / quasi-experiments: diff-in-diff, synthetic control, propensity scores, market matching, regression discontinuity, Bayesian structural time series | To be created |
| **Experimentation_guide** | Docs and reading list covering both areas; links to the two code repos | Existing, to refresh |

### This repo's layout

```
src/abtest/                   core library, single source of truth for the math
apps/sequential_monitor/      Dash app (copied from sequential_testing_tool)
apps/sample_size_calculator/  Dash app (copied from sample-size-calculator-ab-test)
tests/                        library tests
docs/                         plans and notes
```

## Migration steps

1. [x] Copy `sequential_testing_tool` and `sample-size-calculator-ab-test` into `apps/` unchanged.
2. [ ] Rewire both apps to import `abtest` instead of their own copies of the math
       (`apps/sequential_monitor/core/`, `apps/sample_size_calculator/calculator.py`);
       move any method the library lacks (e.g. continuous-metric mSPRT, Bayesian t-posterior) into `src/abtest/`.
3. [ ] Bring the apps under ruff and pytest.
4. [ ] Create `causal_inference_observational` with the same layout (`src/causal/`, `tests/`, CI, CLAUDE.md).
5. [ ] Refresh `Experimentation_guide` README to point to both code repos.
6. [ ] Later: archive the old repos with a "moved to ..." note
       (`sequential_testing_tool`, `sample-size-calculator-ab-test`, `All_in_R`).
       Check `All_in_R/r_in_a_nutshell.pdf` before keeping it public (likely copyrighted book).

Untouched: `sc-agent-skills-files` (course material, unrelated).
