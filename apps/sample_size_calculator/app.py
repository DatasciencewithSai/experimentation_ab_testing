from __future__ import annotations

from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

from calculator import (
    CalculatorInputs,
    build_effect_comparison,
    build_power_curve,
    calculate_sample_size,
    validate_inputs,
)


app = Dash(__name__)
server = app.server
app.title = "A/B Test Sample Size Calculator"


def metric_card(label: str, metric_id: str, help_text: str) -> html.Div:
    return html.Div(
        className="metric-card",
        children=[
            html.Div(label, className="metric-label"),
            html.Div(id=metric_id, className="metric-value"),
            html.Div(help_text, className="metric-help"),
        ],
    )


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "#52606d"},
            }
        ],
        margin={"l": 24, "r": 24, "t": 40, "b": 24},
    )
    return fig


app.layout = html.Div(
    className="page-shell",
    children=[
        html.Div(
            className="hero-panel",
            children=[
                html.Div(
                    className="hero-copy",
                    children=[
                        html.Div("Experiment Planning", className="eyebrow"),
                        html.H1("A/B Test Sample Size Calculator"),
                        html.P(
                            "Plan statistically valid experiments for conversion-rate "
                            "changes using a two-sample z-test for proportions, "
                            "powered by statsmodels."
                        ),
                    ],
                ),
                html.Div(
                    className="hero-note",
                    children=[
                        html.Div("Methodology", className="note-title"),
                        html.P(
                            "Fixed-horizon sample size planning with alpha and power "
                            "controls. Charts update live as you change assumptions."
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            className="content-grid",
            children=[
                html.Div(
                    className="panel form-panel",
                    children=[
                        html.H2("Inputs"),
                        html.Div(
                            className="field-grid",
                            children=[
                                html.Div(
                                    className="field",
                                    children=[
                                        html.Label("Baseline conversion rate"),
                                        dcc.Input(
                                            id="baseline-rate",
                                            type="number",
                                            min=0.001,
                                            max=0.999,
                                            step=0.001,
                                            value=0.10,
                                            debounce=True,
                                        ),
                                        html.Span(
                                            "Example: 0.10 means 10%.",
                                            className="field-help",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="field",
                                    children=[
                                        html.Label("Expected conversion rate"),
                                        dcc.Input(
                                            id="expected-rate",
                                            type="number",
                                            min=0.001,
                                            max=0.999,
                                            step=0.001,
                                            value=0.12,
                                            debounce=True,
                                        ),
                                        html.Span(
                                            "Target rate for the treatment group.",
                                            className="field-help",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="field",
                                    children=[
                                        html.Label("Alpha"),
                                        dcc.Input(
                                            id="alpha",
                                            type="number",
                                            min=0.001,
                                            max=0.2,
                                            step=0.001,
                                            value=0.05,
                                            debounce=True,
                                        ),
                                        html.Span(
                                            "Type I error threshold, commonly 0.05.",
                                            className="field-help",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="field",
                                    children=[
                                        html.Label("Power"),
                                        dcc.Input(
                                            id="power",
                                            type="number",
                                            min=0.5,
                                            max=0.999,
                                            step=0.01,
                                            value=0.80,
                                            debounce=True,
                                        ),
                                        html.Span(
                                            "Probability of detecting the target effect.",
                                            className="field-help",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="field field-wide",
                                    children=[
                                        html.Label("Daily eligible visitors"),
                                        dcc.Input(
                                            id="daily-visitors",
                                            type="number",
                                            min=1,
                                            step=1,
                                            value=5000,
                                            debounce=True,
                                        ),
                                        html.Span(
                                            "Used for duration estimates across both variants.",
                                            className="field-help",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(id="validation-message", className="validation-message"),
                    ],
                ),
                html.Div(
                    className="panel results-panel",
                    children=[
                        html.H2("Key Metrics"),
                        html.Div(
                            className="metrics-grid",
                            children=[
                                metric_card(
                                    "Sample size / group",
                                    "sample-per-group",
                                    "Visitors required in each variant.",
                                ),
                                metric_card(
                                    "Total sample size",
                                    "total-sample-size",
                                    "Combined control and treatment traffic.",
                                ),
                                metric_card(
                                    "Absolute effect",
                                    "absolute-effect",
                                    "Expected rate - baseline rate.",
                                ),
                                metric_card(
                                    "Relative effect",
                                    "relative-effect",
                                    "Lift relative to baseline.",
                                ),
                                metric_card(
                                    "Estimated duration",
                                    "estimated-duration",
                                    "Approximate runtime at your traffic level.",
                                ),
                                metric_card(
                                    "Standardized effect",
                                    "effect-size",
                                    "Cohen's h for proportions.",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            className="charts-grid",
            children=[
                html.Div(
                    className="panel chart-panel",
                    children=[
                        html.H2("Interactive Power Curve"),
                        dcc.Graph(
                            id="power-curve",
                            config={"displayModeBar": False},
                            figure=empty_figure("Enter valid inputs to render the power curve."),
                        ),
                    ],
                ),
                html.Div(
                    className="panel chart-panel",
                    children=[
                        html.H2("Effect Size Comparison"),
                        dcc.Graph(
                            id="effect-comparison",
                            config={"displayModeBar": False},
                            figure=empty_figure("Enter valid inputs to compare sample sizes across lifts."),
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            className="footer-note",
            children=[
                html.P(
                    "This calculator assumes a 50/50 traffic split and a two-sided "
                    "two-sample z-test for binary conversion outcomes."
                )
            ],
        ),
    ],
)


@app.callback(
    Output("validation-message", "children"),
    Output("sample-per-group", "children"),
    Output("total-sample-size", "children"),
    Output("absolute-effect", "children"),
    Output("relative-effect", "children"),
    Output("estimated-duration", "children"),
    Output("effect-size", "children"),
    Output("power-curve", "figure"),
    Output("effect-comparison", "figure"),
    Input("baseline-rate", "value"),
    Input("expected-rate", "value"),
    Input("alpha", "value"),
    Input("power", "value"),
    Input("daily-visitors", "value"),
)
def update_dashboard(
    baseline_rate: float | None,
    expected_rate: float | None,
    alpha: float | None,
    power: float | None,
    daily_visitors: int | None,
):
    if None in (baseline_rate, expected_rate, alpha, power, daily_visitors):
        message = html.Div("Fill in all inputs to calculate the required sample size.")
        placeholder = "N/A"
        return (
            message,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            empty_figure("Fill in all inputs to render the power curve."),
            empty_figure("Fill in all inputs to compare sample sizes."),
        )

    inputs = CalculatorInputs(
        baseline_rate=float(baseline_rate),
        expected_rate=float(expected_rate),
        alpha=float(alpha),
        power=float(power),
        daily_visitors=int(daily_visitors),
    )

    errors = validate_inputs(inputs)
    if errors:
        error_message = html.Ul([html.Li(error) for error in errors])
        placeholder = "N/A"
        return (
            error_message,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            placeholder,
            empty_figure("Resolve input validation issues to render the power curve."),
            empty_figure("Resolve input validation issues to compare effect sizes."),
        )

    results = calculate_sample_size(inputs)
    sample_sizes, powers = build_power_curve(inputs, results.sample_per_group)
    expected_rates, comparison_samples, relative_lifts = build_effect_comparison(
        inputs.baseline_rate,
        inputs.alpha,
        inputs.power,
    )

    power_curve = go.Figure()
    power_curve.add_trace(
        go.Scatter(
            x=sample_sizes,
            y=powers,
            mode="lines+markers",
            name="Power",
            line={"color": "#0f766e", "width": 4},
            marker={"size": 7, "color": "#14b8a6"},
        )
    )
    power_curve.add_hline(
        y=inputs.power,
        line_dash="dot",
        line_color="#b45309",
        annotation_text=f"Target power = {inputs.power:.0%}",
    )
    power_curve.add_vline(
        x=results.sample_per_group,
        line_dash="dot",
        line_color="#1d4ed8",
        annotation_text=f"Required n = {results.sample_per_group:,}",
    )
    power_curve.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 32, "r": 24, "t": 24, "b": 32},
        xaxis_title="Sample size per group",
        yaxis_title="Statistical power",
        yaxis={"tickformat": ".0%", "range": [0, 1]},
        hovermode="x unified",
    )

    comparison_figure = go.Figure()
    comparison_figure.add_trace(
        go.Scatter(
            x=relative_lifts,
            y=comparison_samples,
            mode="lines+markers",
            name="Required sample / group",
            line={"color": "#7c3aed", "width": 4},
            marker={"size": 7, "color": "#a78bfa"},
            customdata=expected_rates,
            hovertemplate=(
                "Relative effect: %{x:.2f}%<br>"
                "Expected rate: %{customdata:.3f}<br>"
                "Required n/group: %{y:,.0f}<extra></extra>"
            ),
        )
    )
    comparison_figure.add_vline(
        x=((inputs.expected_rate - inputs.baseline_rate) / inputs.baseline_rate) * 100,
        line_dash="dot",
        line_color="#1d4ed8",
        annotation_text="Current assumption",
    )
    comparison_figure.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 32, "r": 24, "t": 24, "b": 32},
        xaxis_title="Relative effect vs. baseline (%)",
        yaxis_title="Sample size per group",
        hovermode="closest",
    )

    relative_effect_text = (
        f"{results.relative_effect * 100:.2f}%"
        if results.relative_effect is not None
        else "N/A"
    )

    duration_text = (
        f"{results.estimated_days:,} days ({results.estimated_weeks:.1f} weeks)"
        if results.estimated_days is not None
        else "N/A"
    )

    validation_message = html.Div(
        "Inputs look valid. Metrics and charts reflect a fixed-horizon two-sample z-test.",
        className="validation-success",
    )

    return (
        validation_message,
        f"{results.sample_per_group:,}",
        f"{results.total_sample_size:,}",
        f"{results.absolute_effect * 100:.2f} pp",
        relative_effect_text,
        duration_text,
        f"{results.effect_size:.4f}",
        power_curve,
        comparison_figure,
    )


if __name__ == "__main__":
    app.run(debug=False)
