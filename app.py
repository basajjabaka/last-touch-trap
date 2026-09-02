"""Meridian attribution dashboard — Paid Social under four attribution models.

The whole argument is one interaction: change the model selector and watch Paid
Social move from 7th place to 1st on the same quarter of data.

Run locally:  shiny run app.py
"""

import pandas as pd
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

import attribution as attr

# --- palette -----------------------------------------------------------------
# Emphasis form: one accent hue for Paid Social, muted gray for context.
# Validated against surface #fcfcfb — CVD separation dE 15.9, normal-vision 17.8,
# both marks clear 3:1 contrast.
SURFACE = "#fcfcfb"
PLANE = "#f9f9f7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
ACCENT = "#2a78d6"
CONTEXT = "#898781"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

FOCUS = "paid_social"

# --- data: loaded once at module scope, not per session ----------------------
TOUCHES, FIRST_CONVS, WINDOWED = attr.build()
LIFT = attr.exposure_lift(TOUCHES, FIRST_CONVS)
PATHS = attr.journey_paths(WINDOWED)

N_CONV = len(FIRST_CONVS)
SHARES = {m: attr.share(WINDOWED, m) for m in attr.MODELS}
RANKS = {m: list(s.index).index(FOCUS) + 1 for m, s in SHARES.items()}

IS_OPENER = WINDOWED["position"] == 0
IS_CLOSER = WINDOWED["position"] == WINDOWED["journey_len"] - 1
PS_TOUCHED = WINDOWED.loc[WINDOWED.channel == FOCUS, "customer_id"].nunique()
PS_OPENED = int((WINDOWED.loc[IS_OPENER, "channel"] == FOCUS).sum())
PS_CLOSED = int((WINDOWED.loc[IS_CLOSER, "channel"] == FOCUS).sum())

TIMING = WINDOWED.groupby("channel")["days_before"].mean().sort_values()
TOP_PATHS = PATHS[PATHS.str.contains(FOCUS)].value_counts().head(8)


CHANNEL_LABELS = {"youtube": "YouTube"}


def nice(ch):
    return CHANNEL_LABELS.get(ch, ch.replace("_", " ").title())


def base_layout(fig, height, xtitle=""):
    fig.update_layout(
        height=height,
        # generous right margin: value labels sit outside the bar end
        margin=dict(l=8, r=78, t=8, b=36),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_2),
        showlegend=False,
        dragmode=False,
        bargap=0.34,
        xaxis=dict(
            title=dict(text=xtitle, font=dict(size=12, color=MUTED)),
            gridcolor=GRID,
            zerolinecolor=BASELINE,
            linecolor=BASELINE,
            tickfont=dict(color=MUTED, size=12),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            linecolor=BASELINE,
            tickfont=dict(color=INK, size=13),
        ),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=BASELINE,
            font=dict(family=FONT, size=13, color=INK),
        ),
    )
    return fig


def emphasis_bar(series, height, xtitle, fmt="{:.2f}%", hover="{:.2f}%"):
    """Horizontal ranked bars: the focus channel accented, the rest as context."""
    s = series.sort_values()
    colors = [ACCENT if ch == FOCUS else CONTEXT for ch in s.index]
    fig = go.Figure(
        go.Bar(
            x=s.values,
            y=[nice(c) for c in s.index],
            orientation="h",
            marker=dict(color=colors, cornerradius=4),
            text=[fmt.format(v) for v in s.values],
            textposition="outside",
            textfont=dict(family=FONT, size=12, color=INK_2),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>" + hover.replace("{:.2f}", "%{x:.2f}") + "<extra></extra>",
        )
    )
    return base_layout(fig, height, xtitle)


def as_widget(fig):
    """Hand Shiny a FigureWidget with the Plotly modebar switched off.

    shinywidgets merges `_config` into the widget's plotly config, so this is the
    supported hook. Must run inside an active session, i.e. from @render_widget.
    The charts are static bars whose only interaction is the hover tooltip, so the
    zoom/pan/save toolbar is clutter -- and `dragmode=False` in base_layout stops
    an accidental drag-zoom the (now hidden) reset button would have undone.
    """
    w = go.FigureWidget(fig)
    w._config = {"displayModeBar": False, "displaylogo": False, **w._config}
    return w


def stat_tile(value, label, sub=""):
    return ui.div(
        ui.div(value, style=f"font-size:30px;font-weight:640;color:{INK};line-height:1.15;"),
        ui.div(label, style=f"font-size:12px;color:{INK_2};margin-top:5px;font-weight:560;"),
        ui.div(sub, style=f"font-size:11px;color:{MUTED};margin-top:2px;"),
        style=(
            f"background:{SURFACE};border:1px solid rgba(11,11,11,0.10);"
            "border-radius:10px;padding:15px 17px;flex:1 1 190px;min-width:170px;"
        ),
    )


CSS = f"""
body {{ background:{PLANE}; font-family:{FONT}; color:{INK}; margin:0; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:26px 20px 56px; }}
.card {{ background:{SURFACE}; border:1px solid rgba(11,11,11,0.10);
         border-radius:10px; padding:17px 19px; margin-bottom:16px; }}
.card h2 {{ font-size:14px; margin:0 0 3px; color:{INK}; font-weight:640; }}
.card p.sub {{ font-size:12px; color:{MUTED}; margin:0 0 12px; }}
.row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }}
table.paths {{ width:100%; border-collapse:collapse; font-size:13px;
               font-variant-numeric:tabular-nums; }}
table.paths th {{ text-align:left; color:{MUTED}; font-weight:560; font-size:11px;
                  text-transform:uppercase; letter-spacing:.045em;
                  padding:0 0 7px; border-bottom:1px solid {GRID}; }}
table.paths td {{ padding:8px 0; border-bottom:1px solid {GRID}; color:{INK_2}; }}
table.paths td.n {{ text-align:right; color:{INK}; font-weight:600; width:70px; }}
table.paths tr:last-child td {{ border-bottom:none; }}
.chip {{ background:{ACCENT}; color:#fff; border-radius:4px; padding:1px 6px;
         font-size:11px; font-weight:600; }}
.shiny-input-radiogroup label {{ font-size:13px; margin-right:18px; color:{INK}; }}
.shiny-input-radiogroup .shiny-options-group {{ display:flex; flex-wrap:wrap; gap:2px; }}
"""


app_ui = ui.page_fluid(
    ui.tags.style(CSS),
    ui.tags.title("Meridian — attribution review"),
    ui.div(
        {"class": "wrap"},
        ui.div(
            ui.h1(
                "Is Paid Social really underperforming?",
                style=f"font-size:25px;margin:0 0 6px;color:{INK};font-weight:660;",
            ),
            ui.p(
                f"Meridian, Q2 2026 — {N_CONV:,} first conversions, {len(WINDOWED):,} touches "
                "inside the 30-day window. Change the attribution model below: nothing about "
                "the data changes, only the rule for who gets the credit.",
                style=f"font-size:13.5px;color:{INK_2};margin:0 0 20px;max-width:78ch;line-height:1.55;",
            ),
        ),
        ui.output_ui("tiles"),
        ui.div(
            {"class": "card"},
            ui.h2("Share of signups by channel"),
            ui.p({"class": "sub"}, "Paid Social in blue, every other channel as context."),
            ui.input_radio_buttons(
                "model",
                None,
                {m: attr.MODELS[m] for m in attr.MODELS},
                selected="last",
                inline=True,
            ),
            output_widget("share_chart"),
            ui.output_ui("share_note"),
        ),
        ui.div(
            {"class": "row"},
            ui.div(
                {"class": "card", "style": "flex:1 1 460px;margin-bottom:0;"},
                ui.h2("Paid Social under all four models"),
                ui.p({"class": "sub"}, "Same quarter, same touches — only the credit rule differs."),
                output_widget("model_chart"),
            ),
            ui.div(
                {"class": "card", "style": "flex:1 1 460px;margin-bottom:0;"},
                ui.h2("How early each channel lands"),
                ui.p({"class": "sub"}, "Mean days before the conversion. Last touch pays whoever is closest to zero."),
                output_widget("timing_chart"),
            ),
        ),
        ui.div(
            {"class": "card", "style": "margin-top:16px;"},
            ui.h2("Where Paid Social sits in the journey"),
            ui.p({"class": "sub"}, "The most common converting paths that include Paid Social."),
            ui.output_ui("paths_table"),
        ),
        ui.p(
            "Caveat carried from the analysis: this export contains no spend data, so no CAC "
            "or ROAS can be computed here. Paid Social's raw exposure lift is 1.08x, the lowest "
            "of the nine channels — it is a broad-reach channel. The case against the 60% cut is "
            "that last touch cannot answer the question, not that Paid Social is proven efficient.",
            style=f"font-size:12px;color:{MUTED};margin:18px 0 0;max-width:82ch;line-height:1.6;",
        ),
    ),
)


def server(input, output, session):
    @reactive.calc
    def model():
        return input.model()

    @render.ui
    def tiles():
        m = model()
        share = SHARES[m][FOCUS]
        return ui.div(
            {"class": "row"},
            stat_tile(f"{share:.2f}%", "Paid Social share of signups", attr.MODELS[m]),
            stat_tile(f"{RANKS[m]} of 9", "Rank among channels", attr.MODELS[m]),
            stat_tile(f"{PS_TOUCHED:,}", "Converters it touched", f"{PS_TOUCHED / N_CONV * 100:.1f}% of all converters"),
            stat_tile(f"{PS_OPENED:,} : {PS_CLOSED:,}", "Journeys opened : closed", f"{PS_OPENED / PS_CLOSED:.1f} opens per close"),
        )

    @render_widget
    def share_chart():
        return as_widget(emphasis_bar(SHARES[model()], 340, "share of signups (%)"))

    @render.ui
    def share_note():
        m = model()
        if m == "last":
            msg = (
                f"This is the current dashboard. Paid Social earns {SHARES['last'][FOCUS]:.2f}% — "
                f"rank {RANKS['last']} of 9. The arithmetic is right; it credits only the final touch, "
                "and every converting journey here has at least two."
            )
        else:
            msg = (
                f"Paid Social earns {SHARES[m][FOCUS]:.2f}% — rank {RANKS[m]} of 9, up from "
                f"rank {RANKS['last']} on last touch. Same conversions, same touches."
            )
        return ui.p(msg, style=f"font-size:12.5px;color:{INK_2};margin:10px 0 0;line-height:1.55;")

    @render_widget
    def model_chart():
        vals = pd.Series({attr.MODELS[m]: SHARES[m][FOCUS] for m in attr.MODELS})
        fig = go.Figure(
            go.Bar(
                x=vals.values,
                y=vals.index,
                orientation="h",
                marker=dict(color=ACCENT, cornerradius=4),
                text=[f"{v:.2f}%" for v in vals.values],
                textposition="outside",
                textfont=dict(family=FONT, size=12, color=INK_2),
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Paid Social %{x:.2f}%<extra></extra>",
            )
        )
        fig = base_layout(fig, 250, "Paid Social share of signups (%)")
        fig.update_yaxes(autorange="reversed")
        return as_widget(fig)

    @render_widget
    def timing_chart():
        return as_widget(
            emphasis_bar(TIMING, 250, "mean days before conversion",
                         fmt="{:.1f}d", hover="{:.2f} days")
        )

    @render.ui
    def paths_table():
        rows = "".join(
            "<tr><td>{}</td><td class='n'>{:,}</td></tr>".format(
                " &rsaquo; ".join(
                    f"<span class='chip'>{nice(c)}</span>" if c == FOCUS else nice(c)
                    for c in path.split(" > ")
                ),
                n,
            )
            for path, n in TOP_PATHS.items()
        )
        return ui.HTML(
            "<table class='paths'><thead><tr><th>Journey</th>"
            "<th class='n' style='text-align:right'>Customers</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )


app = App(app_ui, server)
