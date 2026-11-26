# A/B Test Sample Size Calculator

A professional Dash + Plotly web application for planning statistically valid A/B tests for conversion-rate experiments. The calculator uses a fixed-horizon two-sample z-test for proportions through the industry-standard `statsmodels` library.

## What the app does

- Calculates required sample size per group and total sample size
- Computes absolute effect and relative lift
- Estimates experiment duration from daily eligible traffic
- Renders an interactive power curve
- Compares required sample size across effect sizes
- Validates user inputs in real time

## Methodology

This app uses:

- Two-sample z-test planning for binary outcomes
- `statsmodels.stats.power.NormalIndPower.solve_power`
- `statsmodels.stats.proportion.proportion_effectsize`
- A fixed-horizon design with 50/50 traffic allocation
- A two-sided test assumption

This makes it a practical planning tool for classic conversion-rate A/B tests where you want to choose a target minimum detectable effect before launch.

## Project structure

```text
sample_size_calculator_ab_test/
├── app.py
├── calculator.py
├── requirements.txt
├── README.md
└── assets/
    └── styles.css
```

## Install from scratch

If you are setting up a machine for Python work, install these in this order:

1. Python 3.11 or newer
2. `pip` (usually included with Python)
3. JupyterLab or Notebook if you also want an analysis environment
4. A code editor such as VS Code
5. The Python packages in `requirements.txt`

### 1. Check Python

```bash
python3 --version
```

If Python is missing, install it first from [python.org](https://www.python.org/downloads/).

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Upgrade packaging tools

```bash
python3 -m pip install --upgrade pip setuptools wheel
```

### 4. Install the app dependencies

```bash
pip install -r requirements.txt
```

### 5. Optional: install Jupyter

Jupyter is not required to run the Dash app, but it is useful if you want to explore sample size math or prototype ideas.

```bash
pip install jupyterlab notebook ipykernel
python3 -m ipykernel install --user --name ab-test-calculator
```

## Run the app

From the project directory:

```bash
python3 app.py
```

Then open the local URL shown in the terminal, usually:

- [http://127.0.0.1:8050](http://127.0.0.1:8050)

## Inputs

- Baseline conversion rate: current control conversion rate as a decimal
- Expected conversion rate: target treatment conversion rate as a decimal
- Alpha: significance threshold, often `0.05`
- Power: desired sensitivity, often `0.80` or `0.90`
- Daily eligible visitors: total daily traffic available to the experiment

## Output metrics

- Sample size per group
- Total sample size
- Absolute effect in percentage points
- Relative effect in percent
- Estimated runtime in days and weeks
- Standardized effect size (`Cohen's h`)

## Recommended defaults

- Alpha: `0.05`
- Power: `0.80`
- Minimum runtime sanity check: at least 1 to 2 full business cycles when possible

## Notes and assumptions

- The app assumes equal allocation between control and treatment.
- The app is designed for binary conversion metrics, not continuous revenue-style metrics.
- Duration estimates are traffic-based and do not replace experiment quality checks such as sample ratio mismatch, instrumentation validation, or guardrail review.

## Industry references

The product direction and experimentation framing were informed by widely used experimentation guidance:

- Optimizely Stats Engine overview and experiment duration guidance:
  - [Stats Engine](https://support.optimizely.com/hc/en-us/articles/4410284008461-Calculate-the-statistical-likelihoods-of-variations-using-Stats-Engine)
  - [How long to run an experiment](https://support.optimizely.com/hc/en-us/articles/4410283969165-How-long-to-run-an-experiment)
- Google/Firebase experimentation concepts:
  - [About Firebase A/B tests](https://firebase.google.com/docs/ab-testing/ab-concepts)
- Spotify experimentation platform context:
  - [Spotify's New Experimentation Platform (Part 1)](https://engineering.atspotify.com/2020/10/spotifys-new-experimentation-platform-part-1/)

## Next improvements you could add

- Support one-sided vs. two-sided tests
- Support unequal allocation ratios
- Add confidence interval simulation views
- Add sample ratio mismatch checks
- Export experiment plans as CSV or PDF
