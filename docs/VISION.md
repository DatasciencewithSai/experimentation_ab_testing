# Vision: build, learn, showcase, share

Owner's goals, captured 2026-11-26. This is the north star for all three repos;
`docs/REPO_PLAN.md` covers the repo structure and migration.

## The two ideas

1. **A set of fast, focused experimentation tools**, in the spirit of Evan Miller's
   "Awesome A/B Tools": one page per question, instant answers, plain-English interpretation,
   and the math shown for anyone who wants it. Original design and code, not a copy.
2. **The go-to place to understand experimentation**: every concept and method, organized so it
   makes sense, from randomized A/B tests to quasi-experiments, linked to working tools and code.

Both should be **agentic**: usable by AI agents (and built with them), the way Statsig is moving,
with the rigor Ron Kohavi teaches (trustworthiness checks first, then results).

## How the pieces fit

```
   Experimentation_guide repo  ->  Hub site (GitHub Pages)
                                   - Tools: one page per calculator
                                   - Concepts: explained, linked, with sources
                                          |
                                          | same math as
                                          v
   abtest  (experimentation_ab_testing)       causal  (causal_inference_observational)
   single source of truth for the statistics, tested in CI
                                          |
                                          | exposed to agents via
                                          v
   Agent layer: MCP server + Claude skills (design / analyze / review experiments)
```

## Track 1: Tools (the calculators)

Each tool page: inputs -> answer -> plain-English verdict -> "how this is computed" -> concept page link.

| # | Tool | Library source |
|---|---|---|
| 1 | Sample size and test duration (proportions, means; absolute or relative MDE) | `abtest.sample_size` (+ existing calculator app) |
| 2 | Conversion rate comparison (z-test / chi-squared, CI on the lift) | `abtest.frequentist` |
| 3 | Continuous metric comparison (Welch t-test) | `abtest.frequentist` |
| 4 | Sequential monitor: is it safe to stop today? (mSPRT + Bayesian) | `abtest.sequential` (+ existing app) |
| 5 | Bayesian A/B: P(B > A), expected loss | `abtest.bayesian` |
| 6 | Sample ratio mismatch (SRM) checker | to build |
| 7 | Count / rate data (Poisson) and time-to-event comparisons | to build |
| 8 | Variance reduction (CUPED) impact estimator | to build |
| 9 | Quasi-experiment tools: diff-in-diff, synthetic control | `causal` |

## Track 2: Knowledge hub (concepts that make sense)

Turn `Experimentation_guide` from notes into a browsable site. Sections:

- **Design**: hypotheses, randomization unit, power and MDE, OEC and guardrail metrics, duration
- **Trustworthiness** (Kohavi-first): SRM, A/A tests, Twyman's law, novelty/primacy, interference
- **Analysis**: frequentist, Bayesian, sequential, variance reduction, multiple comparisons,
  heterogeneous effects
- **When you can't randomize**: DiD, synthetic control, propensity scores, RDD, market matching,
  CausalImpact
- **Running a program**: platforms (Statsig, Optimizely, Eppo, GrowthBook), culture, decisions
- **Library**: books (Kohavi, Tang & Xu, *Trustworthy Online Controlled Experiments*), papers, people

Every concept page: what it is -> when to use it -> common mistakes -> try it (tool) -> code -> sources.

## Track 3: Agentic layer

- **MCP server** exposing `abtest` and `causal` so any agent (Claude, Cursor, ...) can size,
  analyze and monitor experiments with tested math instead of guessing.
- **Claude skills**:
  - `design-experiment`: hypothesis -> metrics -> sample size -> duration -> pre-registration doc
  - `analyze-experiment`: trust checks first (SRM, data quality), then effects, then a readout
  - `review-experiment`: Kohavi-style checklist on someone's results; flags peeking, SRM,
    multiple testing, underpowered tests
- **Agents that grow the project**: scheduled agents pick the next roadmap item
  (a tool, a concept page, a method) and open a PR for review.

## Track 4: Showcase and share

- Hub site on GitHub Pages; pinned repos with screenshots and clear READMEs.
- One short write-up per tool or concept (LinkedIn / blog), linking back to the site.
- Example notebooks with realistic datasets for each method.

## Phases

1. **Foundation** (done): repos, libraries, CI, cloud environment, apps imported.
2. **Tools MVP**: hub site skeleton + tools 1-6, math from the libraries.
3. **Knowledge hub**: migrate guide notes, write core concept pages, cross-link with tools.
4. **Agentic**: MCP server + the three skills; scheduled content agents.
5. **Expand**: tools 7-9, more causal methods, notebooks, write-ups.

## Open decisions

- **Tool runtime**:
  (a) JavaScript in the browser, math cross-checked against the Python library with shared test
  fixtures: instant, free static hosting (recommended);
  (b) Pyodide running the Python library in the browser: one codebase, slower first load;
  (c) Python apps on a server (Dash, like today): needs hosting.
- **Name / brand** for the hub site.
- **Where the site lives**: recommended `Experimentation_guide`, which becomes the hub and uses
  the two libraries.
