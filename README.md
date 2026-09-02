# Meridian — Paid Social attribution review

**Recommendation: do not make the 60% cut.** The 2.9% figure is arithmetically correct and
answers the wrong question — it comes from the one model that structurally cannot see what
Paid Social does. But this is not a case for spending more either: hold the budget flat for
one quarter and run a holdout test that can actually measure it.

Q2 2026 (1 Apr – 30 Jun), 30-day attribution window, 5,939 first conversions, 20,533 eligible
touches. Working: [`notebook.ipynb`](notebook.ipynb) · logic: [`attribution.py`](attribution.py)

## The dashboard is right, and it is misleading

Last touch gives Paid Social **2.91%** of signups — reproduced exactly. Change nothing but the
credit rule and the same quarter says this:

| Model | Paid Social | Rank | Brand Search |
|---|---:|:---:|---:|
| **Last touch** (current dashboard) | **2.91%** | 7 of 9 | 34.60% |
| Linear | 11.53% | 5 | 15.84% |
| Position-based 40/20/40 | 13.59% | 3 | 18.49% |
| **First touch** | **27.29%** | **1 of 9** | 6.28% |

A 9.4x swing from the model choice alone. Paid Social is either the worst paid channel or the
best one, depending on a setting nobody chose deliberately.

## Why last touch does this

- **It opens journeys it doesn't close.** Paid Social opened 1,621 converting journeys and
  closed 173 — 9.4 opens per close. It touched 2,063 of 5,939 converters (34.7%).
- **It acts earliest.** Mean 14.8 days before conversion, the furthest out of any channel.
  Brand Search lands at 5.9 days, Retargeting at 6.8. Last touch pays whoever is nearest zero.
- **There is no journey it could have won.** Every converting journey here has 2–5 touches;
  not one is single-touch. Last touch is *always* discarding a known assist.
- **The window compounds it.** 11.2% of Paid Social's touches to converters fall outside the
  30-day window, versus 0.16% for Brand Search.
- **The paths say it plainly.** The most common journeys containing it are
  `paid_social → brand_search` and `paid_social → retargeting`. Cutting Paid Social to fund
  Brand Search and Retargeting means defunding the channel that creates the demand they harvest.

## Where Paid Social is genuinely weak

Using the 34,061 customers who never paid: **Paid Social's exposure lift is 1.08x — the lowest
of all nine channels** (15.6% conversion when exposed vs 14.4% when not). It reaches 37% of all
known customers, so seeing it barely discriminates. It is broad reach, not precision.

Two limits on how far any of this goes:

1. **This export has no spend data.** No CAC, no ROAS, no efficiency claim in either direction.
2. **Exposure lift is correlation.** It flatters closers — Brand Search scores 4.03x partly
   because people who already intend to buy go and search the brand. It cannot settle causality
   for anyone, including Paid Social.

Findings hold in April, May and June separately, so this is structural, not a blip.

## What to do

1. **Hold Paid Social flat next quarter.** A 60% cut on a last-touch number would remove the
   single largest opener of converting journeys on the strength of the one model that can't
   see openers.
2. **Run a geo holdout or PSA test.** Suppress Paid Social in matched regions for 4–6 weeks.
   That produces the causal number this data cannot, and it is the only thing that should
   justify a cut of that size.
3. **Re-cut the dashboard to position-based**, with last touch kept as a secondary column.
   Position-based credits both the opener and the closer and doesn't collapse a 3.5-touch
   average journey into one row.
4. **Get Q2 spend by channel.** The same notebook then extends to cost-per-acquisition under
   each model, which is what actually settles a budget question.

## Repo

| File | |
|---|---|
| [`notebook.ipynb`](notebook.ipynb) | Full analysis; the five answers are in the final cell |
| [`attribution.py`](attribution.py) | Load, clean, window, and the four credit models |
| [`app.py`](app.py) | Shiny dashboard — `shiny run app.py` |
| `data/` | `touches.csv` (89,102 rows), `conversions.csv` (6,422 rows) |

**Dashboard:** _(Posit Connect Cloud link — pending deploy)_

Cleaning rules that bind: repeat subscribers counted under their **first** conversion only
(483 customers, 6,422 rows → 5,939); touches eligible only where
`converted_at - 30d ≤ touch_ts ≤ converted_at`; non-converters kept in the touch log but earn
no credit; `device` casing normalised. Every converter retains at least one eligible touch, so
there is no unattributed bucket hiding the answer.
