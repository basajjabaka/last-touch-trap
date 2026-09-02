"""Attribution logic for the Meridian Paid Social review.

Imported by both notebook.ipynb and app.py so the analysis and the dashboard
cannot drift apart. Every figure in the README traces back to a function here.

Rules, from the brief:
  - a touch earns credit only within 30 days before the conversion, at or before it
  - a customer who resubscribed is counted under their FIRST conversion only
  - customers who never paid stay in the touch log, but earn no conversion credit
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
WINDOW_DAYS = 30

# Channels Meridian pays for directly. Used only for the "paid signups" cut of
# the last-touch number; every other figure runs over all nine channels.
PAID_CHANNELS = ["paid_social", "brand_search", "retargeting", "display", "youtube"]

MODELS = {
    "last": "Last touch (current dashboard)",
    "first": "First touch",
    "linear": "Linear",
    "position": "Position-based 40/20/40",
}


def load(data_dir=DATA_DIR):
    """Read both exports and clean the one dirty column.

    `device` arrives with mixed casing (Web/web, Mobile/mobile) and `campaign`
    is null for ~17% of touches. Neither affects attribution, but both would
    split a group-by, so they get normalised here rather than in five places.
    """
    touches = pd.read_csv(data_dir / "touches.csv", parse_dates=["touch_ts"])
    conversions = pd.read_csv(data_dir / "conversions.csv", parse_dates=["converted_at"])

    touches["device"] = touches["device"].str.lower()
    touches["campaign"] = touches["campaign"].fillna("(none)")

    return touches, conversions


def first_conversions(conversions):
    """One row per customer, at their earliest subscription start.

    483 customers resubscribed inside Q2. The brief says to treat each customer
    under their first conversion, so the later rows are dropped entirely -- they
    would otherwise credit the same touch path twice.
    """
    return (
        conversions.sort_values(["customer_id", "converted_at"])
        .groupby("customer_id", as_index=False)
        .first()
    )


def windowed_touches(touches, first_convs):
    """Touches eligible to earn credit, sorted into journey order.

    Keeps `converted_at - 30d <= touch_ts <= converted_at`. Non-converting
    customers drop out at the inner join; their touches are real but earn
    nothing. Touches older than the window drop out too -- that bites Paid
    Social hardest, which is itself part of the finding.
    """
    merged = touches.merge(
        first_convs[["customer_id", "converted_at", "amount_usd", "plan"]],
        on="customer_id",
        how="inner",
    )
    eligible = merged[
        (merged["touch_ts"] <= merged["converted_at"])
        & (merged["touch_ts"] >= merged["converted_at"] - pd.Timedelta(days=WINDOW_DAYS))
    ].copy()

    eligible = eligible.sort_values(["customer_id", "touch_ts"]).reset_index(drop=True)
    eligible["position"] = eligible.groupby("customer_id").cumcount()
    eligible["journey_len"] = eligible.groupby("customer_id")["customer_id"].transform("size")
    eligible["days_before"] = (
        eligible["converted_at"] - eligible["touch_ts"]
    ).dt.total_seconds() / 86400

    return eligible


def _position_weight(pos, n):
    """40% to the opener, 40% to the closer, 20% split across the middle."""
    if n == 1:
        return 1.0
    if n == 2:
        return 0.5
    return 0.4 if pos in (0, n - 1) else 0.2 / (n - 2)


def credit(windowed, model, value_col=None):
    """Credit per channel under one model.

    Every model distributes exactly 1.0 per converting customer (or their
    revenue, if `value_col` is given), so the four models are directly
    comparable and each total equals the converter count.
    """
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}, expected one of {list(MODELS)}")

    w = windowed
    weight = pd.Series(1.0, index=w.index)

    if model == "last":
        weight = (w["position"] == w["journey_len"] - 1).astype(float)
    elif model == "first":
        weight = (w["position"] == 0).astype(float)
    elif model == "linear":
        weight = 1.0 / w["journey_len"]
    elif model == "position":
        weight = pd.Series(
            [_position_weight(p, n) for p, n in zip(w["position"], w["journey_len"])],
            index=w.index,
        )

    if value_col is not None:
        weight = weight * w[value_col]

    return w.assign(_credit=weight).groupby("channel")["_credit"].sum()


def share(windowed, model, value_col=None):
    """Same as `credit`, expressed as percent of total and ranked."""
    c = credit(windowed, model, value_col=value_col)
    return (c / c.sum() * 100).sort_values(ascending=False)


def model_comparison(windowed, value_col=None):
    """All four models side by side, one row per channel."""
    table = pd.DataFrame({m: share(windowed, m, value_col=value_col) for m in MODELS})
    return table.sort_values("first", ascending=False).round(2)


def journey_paths(windowed):
    """Each customer's journey as a ' > ' joined channel string."""
    return windowed.groupby("customer_id")["channel"].apply(" > ".join)


def exposure_lift(touches, first_convs):
    """Conversion rate when a customer saw a channel, vs when they did not.

    This is the only place non-converters do work. It is a correlation, not a
    causal estimate: closing channels score high here partly because people who
    already intend to buy go and search the brand.
    """
    converter_ids = set(first_convs["customer_id"])
    seen = touches.groupby(["customer_id", "channel"]).size().unstack(fill_value=0) > 0
    converted = pd.Series(seen.index.isin(converter_ids), index=seen.index)

    rows = []
    for ch in seen.columns:
        exposed = converted[seen[ch]].mean()
        not_exposed = converted[~seen[ch]].mean()
        rows.append(
            {
                "channel": ch,
                "customers_exposed": int(seen[ch].sum()),
                "cvr_exposed_pct": round(exposed * 100, 2),
                "cvr_not_exposed_pct": round(not_exposed * 100, 2),
                "lift_x": round(exposed / not_exposed, 2),
            }
        )

    return pd.DataFrame(rows).sort_values("lift_x", ascending=False).reset_index(drop=True)


def build(data_dir=DATA_DIR):
    """Load, clean and window in one call. Returns (touches, first_convs, windowed)."""
    touches, conversions = load(data_dir)
    first_convs = first_conversions(conversions)
    return touches, first_convs, windowed_touches(touches, first_convs)
