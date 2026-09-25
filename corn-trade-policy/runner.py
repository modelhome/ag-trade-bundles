#!/usr/bin/env python3
"""
US Corn Trade Policy Impact -- node 4 of the climate -> agriculture -> finance
flow.

Takes a `corn_price_impact` document from ag-commodity-bundles/corn-price
(node 3) and a stated export-demand scenario, and returns the corn price impact
that scenario implies, reported BESIDE node 3's weather-driven impact rather
than folded into it.

    python runner.py <corn_price_impact.json> <scenario.json>

The result document goes to stdout and nothing else does; logs go to stderr.

What the model does, in order:

1.  Reads node 3's document. Everything economic comes from it: the fitted
    transmission coefficient and its bootstrap interval, the weather-driven
    impact, the reference price, and the export exposure that gives the size of
    the market the scenario is measured against. This model FITS NOTHING and
    re-derives nothing node 3 produces.

2.  Converts the scenario's bushels into the quantity node 3's coefficient was
    fitted on -- a proportional deviation of the crop, as a fraction -- by
    dividing by total use for the current marketing year. See "The denominator"
    below; this is the one approximation in the model and it is reported in the
    output rather than buried here.

3.  Applies node 3's coefficient to that shock. Bushels NOT SOLD are demand
    removed, which for price is equivalent to a surplus of the same size, so a
    positive scenario gives a positive equivalent supply shock and therefore a
    NEGATIVE price impact.

4.  Reports weather and trade separately, each with its own interval, and a
    combined figure composed inside the transmission's exponential -- NOT by
    adding the two percentages, which is not what the functional form says.

5.  Carries node 3's `regions`, `national` and `assumptions` through unchanged
    under `upstream_price_impact`, so a reader of the flow's last output sees
    the per-region weather evidence. Nothing in that block is recomputed, and
    none of it enters the arithmetic above.

The denominator. Node 3's coefficient is fitted on the national yield's
deviation from an ERS trend, whose commensurate bushel base is area harvested
times trend yield: 16,344 mil bu for marketing year 2026. Node 3's output does
not carry that figure. It does carry the export exposure, from which total use
follows as exports / export_share_of_use, and total use is the closest
available basis: 1.0% below the trend-production basis for 2026, with the gap
running -3.4% to +6.7% over 2015-2026. Node 3's `us_trend_production_bu` is NOT
used -- it is built from 2022 Census acreage and sits 8.9% below the ERS basis,
which would inflate a 300 mil bu scenario from -1.44% to -1.56%. The basis, its
value and its year are all stated in the output document.

Exports are a COMPONENT of total use, never an addition to it, so a lost-export
scenario reduces the denominator as well as the numerator. Nothing here ever
adds exports to use.

What this is not. It is the price impact implied by a scenario THE USER STATES,
against a baseline in which that scenario does not happen. It is not a price
forecast, not a trading signal, not investment advice, and not a political
forecast: this model does not predict whether any tariff will be imposed,
extended or lifted. Trade also reallocates, so a headline tariff is not a bushel
loss -- the step from a policy to a number of bushels belongs to whoever states
the scenario, not to this model.

Deterministic and offline: a pure function of the two input documents and the
committed destination table. No network calls, no randomness, no wall-clock
dependence beyond the `generated_at` stamp.
"""
import copy
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

DESTINATIONS_PATH = HERE / "destinations.csv"
DESTINATIONS_META_PATH = HERE / "destinations.meta.json"

# How many destinations the output names individually before aggregating the
# rest. Context for a reader deciding whether a scenario is plausible, not data.
TOP_DESTINATIONS = 8

# The copied weather impact must reproduce from node 3's own shock and
# coefficient this closely, in percentage points. Node 3 rounds both
# us_yield_shock_pct and price_impact_pct to four decimals, which bounds the
# disagreement well below this.
REPRODUCTION_TOLERANCE_PCT = 1e-3

NOT_A_FORECAST = (
    "This is the corn price impact implied by an export-demand scenario the user "
    "states, under the transmission fitted by the upstream US Corn Price Impact "
    "model, holding everything else equal. It is NOT a price forecast, NOT a "
    "trading signal and NOT investment advice. It is also NOT a political "
    "forecast: this model does not predict whether any tariff or trade measure "
    "will be imposed, extended or lifted. The scenario is an input, not a finding."
)

SCENARIO_IS_AN_INPUT = (
    "The scenario is an input to this model, not a finding of it. The number of "
    "bushels not sold is supplied by whoever runs the model. This "
    "model does not derive it from a tariff rate, and deliberately cannot: trade "
    "reallocates. In 2018-19 soybean flows largely rerouted rather than "
    "disappeared, and in marketing year 2024 US corn sales to China fell to "
    "essentially nothing while total US corn exports rose to a record. A model "
    "that turned a tariff rate into lost bushels by itself would be claiming "
    "knowledge it does not have."
)

UPSTREAM_SOURCE = (
    "This block is the upstream US Corn Price Impact model's (node 3's) result, "
    "carried through unchanged for reference: its regions, national and "
    "assumptions exactly as received. None of it is recomputed here, and none of "
    "it is an input to any figure elsewhere in this document. The per-region "
    "rows describe the weather component only; the trade scenario is national "
    "and is attributed to no region. Node 3's national figures repeat those in "
    "national.weather, and the two agree by construction."
)


class RunError(Exception):
    """A condition the model refuses to guess its way past."""


def log(message):
    print(message, file=sys.stderr)


def read_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise RunError(f"input file not found: {path}")
    except json.JSONDecodeError as exc:
        raise RunError(f"{path} is not valid JSON: {exc}")


def require(document, path, why):
    """Fetch a dotted path from the upstream document or fail loudly.

    Several fields this model reads are declared but OPTIONAL in node 3's output
    schema, so their absence is a real possibility rather than an impossible
    one. Defaulting any of them would silently change the arithmetic, so each is
    required explicitly and named when missing.
    """
    node = document
    walked = []
    for key in path.split("."):
        walked.append(key)
        if not isinstance(node, dict) or key not in node:
            raise RunError(
                f"the upstream document has no {'.'.join(walked)}: {why}"
            )
        node = node[key]
    return node


def require_number(document, path, why):
    value = require(document, path, why)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RunError(f"{path} is {value!r}, which is not a number: {why}")
    if not math.isfinite(value):
        raise RunError(f"{path} is {value!r}, which is not finite: {why}")
    return float(value)


def read_scenario(raw):
    """The scenario, with the defaults that let this model run standalone.

    A present-but-empty value falls back exactly as a missing key does, so the
    bundle runs with no scenario at all, and a flow that wires an empty literal
    behaves the same as one that wires nothing.
    """
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise RunError(
            f"the scenario document is a {type(raw).__name__}, not an object"
        )

    value = raw.get("bushels_not_sold_mil_bu")
    if value is None or value == "":
        bushels = 0.0
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RunError(
                f"bushels_not_sold_mil_bu is {value!r}; it must be a number of "
                "million bushels, not a tariff rate, a percentage or a string"
            )
        if not math.isfinite(value):
            raise RunError(
                f"bushels_not_sold_mil_bu is {value!r}, which is not finite"
            )
        bushels = float(value)

    # `or ""` would coerce a falsey non-string -- 0, False, [] -- to an empty
    # label and accept a document that violates the declared string schema,
    # while 123 would be rejected. Absence is handled first, then the type.
    label = raw.get("scenario_label")
    if label is None or label == "":
        label = ""
    elif not isinstance(label, str):
        raise RunError(
            f"scenario_label is {label!r}, which is not a string. Leave it out "
            "or pass text; it is carried into the output as written."
        )

    return bushels, label.strip()


def load_destinations():
    """The committed destination context. Enters no arithmetic."""
    if not DESTINATIONS_PATH.exists():
        raise RunError(f"missing committed table: {DESTINATIONS_PATH.name}")
    if not DESTINATIONS_META_PATH.exists():
        raise RunError(f"missing committed table: {DESTINATIONS_META_PATH.name}")
    with open(DESTINATIONS_PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))
    meta = json.loads(DESTINATIONS_META_PATH.read_text())
    if not rows:
        raise RunError(f"{DESTINATIONS_PATH.name} has no rows")
    return rows, meta


def destination_context(rows, meta):
    """The latest marketing year's buyers, largest first, with the rest pooled."""
    latest = int(meta["latest_marketing_year"])
    year_rows = [r for r in rows if int(r["marketing_year"]) == latest]
    if not year_rows:
        raise RunError(
            f"{DESTINATIONS_PATH.name} has no rows for its own declared latest "
            f"marketing year {latest}"
        )
    year_rows.sort(key=lambda r: -float(r["exports_mil_bu"]))
    total = float(meta["annual_total_exports_mil_bu"][str(latest)])

    top = [
        {
            "destination": r["destination"],
            "exports_mil_bu": round(float(r["exports_mil_bu"]), 3),
            "share_of_total_exports": round(float(r["share_of_total_exports"]), 6),
        }
        for r in year_rows[:TOP_DESTINATIONS]
    ]
    rest = year_rows[TOP_DESTINATIONS:]
    if rest:
        rest_bu = sum(float(r["exports_mil_bu"]) for r in rest)
        top.append({
            "destination": f"all other destinations ({len(rest)})",
            "exports_mil_bu": round(rest_bu, 3),
            "share_of_total_exports": round(rest_bu / total, 6) if total else 0.0,
        })

    return {
        "marketing_year": latest,
        "total_exports_mil_bu": round(total, 3),
        "destinations": top,
        "vintage": meta["vintage"],
        "source": meta["source"],
        "source_last_modified": meta.get("source_last_modified"),
        "period": meta["period"],
        "built_at": meta["built_at"],
        "excluded_years": sorted(meta["tie_out"]["excluded_years"]),
        "role": meta["definitions"]["role"],
        "lag": meta["definitions"]["lag"],
    }


def carried_upstream(upstream):
    """Node 3's regions, national and assumptions, copied for publication.

    Deep copies, so nothing later in this run can alter what is published, and
    no rounding or formatting: the members are the parsed JSON as received. Node
    3's schema requires all three, so a missing or mistyped one is a malformed
    document and stops the run rather than publishing a partial block.
    """
    carried = {"source": UPSTREAM_SOURCE}
    for key, kind, why in (
        ("regions", list, "they are carried through as the per-region weather evidence"),
        ("national", dict, "it is carried through beside this model's own result"),
        ("assumptions", dict, "it is carried through, and its not_captured list is inherited"),
    ):
        value = require(upstream, key, why)
        if not isinstance(value, kind):
            raise RunError(
                f"the upstream {key} is a {type(value).__name__}, not "
                f"{'an array' if kind is list else 'an object'}: {why}"
            )
        carried[key] = copy.deepcopy(value)
    return carried


def process(upstream, bushels_not_sold_mil_bu, scenario_label, destinations, dest_meta):
    # --- everything economic comes from node 3 -------------------------------

    transmission = require(
        upstream, "metadata.transmission",
        "this model applies the upstream model's fitted transmission and never "
        "fits or hard-codes one of its own",
    )
    b0 = require_number(
        upstream, "metadata.transmission.shock_coefficient",
        "there is no coefficient to apply without it",
    )
    ci95 = require(
        upstream, "metadata.transmission.shock_coefficient_ci95",
        "every figure this model publishes carries the interval from that "
        "bootstrap, and none may ship without it",
    )
    if not isinstance(ci95, (list, tuple)) or len(ci95) != 2:
        raise RunError(
            f"metadata.transmission.shock_coefficient_ci95 is {ci95!r}; it must "
            "be a two-element interval"
        )
    # Every range this model publishes comes from these two numbers, so they are
    # validated rather than passed to float() and allowed to raise. A bare
    # float("bad") would exit with a traceback, and a non-finite bound would
    # propagate silently into the published low and high figures.
    bounds = []
    for index, value in enumerate(ci95):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RunError(
                f"metadata.transmission.shock_coefficient_ci95[{index}] is "
                f"{value!r}, which is not a number: every published range comes "
                "from that bootstrap interval"
            )
        if not math.isfinite(value):
            raise RunError(
                f"metadata.transmission.shock_coefficient_ci95[{index}] is "
                f"{value!r}, which is not finite: a range cannot be published "
                "from it"
            )
        bounds.append(float(value))
    b0_low, b0_high = bounds

    exposure_current = require(
        upstream, "metadata.export_exposure.current",
        "the scenario is measured against the size of the market, and this "
        "model never re-sources the balance sheet",
    )
    exposure_latest = require(
        upstream, "metadata.export_exposure.latest_complete",
        "the scenario is checked against a completed marketing year's exports, "
        "never against a projection",
    )
    current_exports_mil_bu = require_number(
        upstream, "metadata.export_exposure.current.exports_mil_bu",
        "total use is recovered from it",
    )
    current_export_share = require_number(
        upstream, "metadata.export_exposure.current.export_share_of_use",
        "total use is recovered from it",
    )
    if current_export_share <= 0:
        raise RunError(
            f"metadata.export_exposure.current.export_share_of_use is "
            f"{current_export_share}; total use cannot be recovered from a "
            "non-positive share"
        )
    latest_exports_mil_bu = require_number(
        upstream, "metadata.export_exposure.latest_complete.exports_mil_bu",
        "it is the ceiling a stated scenario is checked against",
    )

    # Exports are a COMPONENT of total use, so this division recovers the whole
    # of use and never adds exports to anything. Both quantities are mil bu.
    total_use_mil_bu = current_exports_mil_bu / current_export_share

    us_yield_shock_pct = require_number(
        upstream, "national.us_yield_shock_pct",
        "it is the weather shock the combined figure is composed with",
    )
    reference_price_usd_bu = require_number(
        upstream, "national.reference_price_usd_bu",
        "the dollar figures are worked out against it",
    )
    date = require(upstream, "national.date", "the result has to say what day it describes")

    # --- the scenario, as a shock -------------------------------------------

    # A scenario cannot remove more export demand than a completed marketing
    # year's entire export programme. The ceiling is an ACTUAL, never the
    # current year's WASDE projection.
    if abs(bushels_not_sold_mil_bu) > latest_exports_mil_bu:
        raise RunError(
            f"the scenario moves {bushels_not_sold_mil_bu:,.1f} mil bu, which "
            f"exceeds total US corn exports of {latest_exports_mil_bu:,.1f} mil "
            f"bu in marketing year "
            f"{exposure_latest.get('marketing_year')}, the latest complete year. "
            "There is not that much export demand to lose."
        )

    # Bushels not sold are demand removed. For price that is equivalent to a
    # surplus of the same size, so the shock enters with the sign of a surplus
    # and a positive scenario produces a NEGATIVE price impact.
    d_trade = bushels_not_sold_mil_bu / total_use_mil_bu
    d_weather = us_yield_shock_pct / 100.0

    def impact_pct(coefficient, shock_fraction):
        return (math.exp(coefficient * shock_fraction) - 1.0) * 100.0

    def band(shock_fraction):
        """Central estimate and the bootstrap interval, low first.

        The two components share one coefficient, so their intervals are
        perfectly correlated: the combined interval comes from applying the
        bounds to the combined shock, never from adding two intervals together.
        """
        central = impact_pct(b0, shock_fraction)
        low, high = sorted(
            [impact_pct(b0_low, shock_fraction), impact_pct(b0_high, shock_fraction)]
        )
        return central, low, high

    # Node 3's weather figures are carried through unchanged rather than
    # recomputed. Reproducing them from its own shock and coefficient is the
    # cheapest available detector of a stale or hand-edited upstream document.
    weather_pct = require_number(
        upstream, "national.price_impact_pct", "it is the weather component"
    )
    reproduced = impact_pct(b0, d_weather)
    if abs(reproduced - weather_pct) > REPRODUCTION_TOLERANCE_PCT:
        raise RunError(
            f"the upstream document's price_impact_pct ({weather_pct}) does not "
            f"reproduce from its own us_yield_shock_pct and transmission "
            f"({reproduced:.6f}). The document has been edited, or its "
            "coefficient and its result come from different runs."
        )

    trade_central, trade_low, trade_high = band(d_trade)
    combined_central, combined_low, combined_high = band(d_weather + d_trade)

    def usd(pct):
        return round(reference_price_usd_bu * pct / 100.0, 4)

    national = {
        "date": date,
        "reference_price_usd_bu": reference_price_usd_bu,
        # Carried through from node 3 unchanged. This model does not re-run the
        # weather calculation and must not appear to.
        "weather": {
            "us_yield_shock_pct": us_yield_shock_pct,
            "price_impact_pct": weather_pct,
            "price_impact_pct_low": require_number(
                upstream, "national.price_impact_pct_low", "no figure ships without its range"
            ),
            "price_impact_pct_high": require_number(
                upstream, "national.price_impact_pct_high", "no figure ships without its range"
            ),
            "price_impact_usd_bu": require_number(
                upstream, "national.price_impact_usd_bu", "the dollar figure is carried through too"
            ),
            "price_impact_usd_bu_low": require_number(
                upstream, "national.price_impact_usd_bu_low", "no figure ships without its range"
            ),
            "price_impact_usd_bu_high": require_number(
                upstream, "national.price_impact_usd_bu_high", "no figure ships without its range"
            ),
            "source": "carried through from the upstream model unchanged; not recomputed here",
        },
        "trade": {
            "equivalent_supply_shock_pct": round(d_trade * 100.0, 4),
            "price_impact_pct": round(trade_central, 4),
            "price_impact_pct_low": round(trade_low, 4),
            "price_impact_pct_high": round(trade_high, 4),
            "price_impact_usd_bu": usd(trade_central),
            "price_impact_usd_bu_low": usd(trade_low),
            "price_impact_usd_bu_high": usd(trade_high),
        },
        "combined": {
            "total_shock_pct": round((d_weather + d_trade) * 100.0, 4),
            "price_impact_pct": round(combined_central, 4),
            "price_impact_pct_low": round(combined_low, 4),
            "price_impact_pct_high": round(combined_high, 4),
            "price_impact_usd_bu": usd(combined_central),
            "price_impact_usd_bu_low": usd(combined_low),
            "price_impact_usd_bu_high": usd(combined_high),
            "composition": (
                "the two shocks are added INSIDE the transmission's exponential, "
                "not after it, so this figure is not the sum of the weather and "
                "trade percentages above"
            ),
        },
    }

    scenario = {
        "bushels_not_sold_mil_bu": bushels_not_sold_mil_bu,
        "label": scenario_label,
        "equivalent_supply_shock_pct": round(d_trade * 100.0, 4),
        "share_of_total_use": round(
            bushels_not_sold_mil_bu / total_use_mil_bu, 6
        ),
        "share_of_latest_complete_exports": round(
            bushels_not_sold_mil_bu / latest_exports_mil_bu, 6
        ),
        "measured_against": {
            "total_use_mil_bu": round(total_use_mil_bu, 3),
            "marketing_year": exposure_current.get("marketing_year"),
            "is_projection": exposure_current.get("is_projection"),
            "derivation": (
                "exports / export_share_of_use from the upstream model's "
                "metadata.export_exposure.current. Exports are a component of "
                "total use, never an addition to it"
            ),
            "latest_complete_exports_mil_bu": latest_exports_mil_bu,
            "latest_complete_marketing_year": exposure_latest.get("marketing_year"),
        },
        "stated_by": (
            "whoever ran this model. The scenario is an input to it, not an "
            "output of it"
        ),
    }

    carried = carried_upstream(upstream)

    not_captured = list(carried["assumptions"].get("not_captured") or [])
    not_captured = [
        f"inherited from the upstream transmission: {item}" for item in not_captured
    ]
    not_captured.extend([
        "the soybean channel: a tariff that hits soybeans hardest lowers the "
        "soybean price, shifts acreage to corn the following spring and pushes "
        "the corn price down a year later. China takes roughly half of US "
        "soybean exports and close to nothing of US corn in most years, so for "
        "a China tariff this indirect channel is probably the larger one. It is "
        "not modelled here; see the README",
        "reallocation: this model prices the bushels it is given and cannot know "
        "how many bushels a given policy would actually cost",
        "announcement and expectation: once a measure is known it is already in "
        "the price. This answers what the scenario implies against a baseline "
        "without it, which is not what happens next",
        "the timing of the move within the season; the transmission is an annual "
        "relationship fitted on a marketing-year average cash price",
    ])

    assumptions = {
        "not_a_forecast": NOT_A_FORECAST,
        "scenario_is_an_input": SCENARIO_IS_AN_INPUT,
        "symmetry": (
            "The transmission applied here was fitted by the upstream model on "
            "SUPPLY-side weather shocks, 1976-2025. Applying it to a demand "
            "shock assumes the price responds symmetrically to a bushel removed "
            "from demand and a bushel added to supply. Post-harvest the supply "
            "curve is close to vertical, which makes that defensible, but it is "
            "an assumption this model makes and does not demonstrate. The "
            "upstream model's own not_captured list states that export demand "
            "shocks and trade policy are outside its fit."
        ),
        "denominator": (
            "The scenario's bushels are turned into a proportional shock by "
            f"dividing by total use of {total_use_mil_bu:,.0f} mil bu for "
            f"marketing year {exposure_current.get('marketing_year')}, recovered "
            "from the upstream export exposure. The coefficient was fitted on "
            "the national yield's deviation from trend, whose exact base is area "
            "harvested times trend yield; the upstream document does not carry "
            "that figure, and total use is the closest available basis -- about "
            "1% below it for 2026, with the gap running -3.4% to +6.7% over "
            "2015-2026. The upstream us_trend_production_bu is deliberately NOT "
            "used: it is built on 2022 Census acreage and sits 8.9% below the "
            "fitted basis. Exports are a component of total use, so a lost-export "
            "scenario reduces the denominator as well as the numerator."
        ),
        "composition": (
            "The transmission is log-linear: the impact is exp(b * d) - 1. Two "
            "shocks therefore combine inside the exponential, so the combined "
            "impact is NOT the sum of the weather and trade percentages."
        ),
        "interval_definition": (
            "Every low and high figure comes from the upstream model's bootstrap "
            "interval on the transmission coefficient, reused unchanged. It says "
            "how well that relationship is known from fifty years of supply "
            "shocks -- not what the corn price will do, and not how likely the "
            "scenario is. Because both components use the same coefficient, "
            "their intervals are perfectly correlated and are never added."
        ),
        "reallocation": (
            "Trade reallocates rather than disappearing. Measured: US corn sales "
            "to China fell from 118 mil bu in marketing year 2023 to 1 mil bu in "
            "2024 while total US corn exports ROSE from 2,255 to 2,873 mil bu; "
            "and across the 1980 Soviet embargo US corn exports were 2,401 mil "
            "bu in 1979 against 2,391 in 1980. Neither episode produced an "
            "aggregate bushel loss, which is why this model takes bushels as its "
            "input and why no historical episode validates it."
        ),
        "destinations_context": (
            "The committed destination table is context only. It shows who buys "
            "US corn so a scenario can be stated against measured purchases; it "
            "is never used to convert a policy into bushels."
        ),
        "not_captured": not_captured,
    }

    metadata = {
        "date": date,
        "model": "US Corn Trade Policy Impact (ag-trade-bundles/corn-trade-policy)",
        "node": "4 of the climate -> agriculture -> finance flow",
        "determinism": (
            "Deterministic and offline: a pure function of the two input "
            "documents and the committed destination table. No network calls, no "
            "randomness, no wall-clock dependence."
        ),
        # Echoed, not restated: whatever the upstream model committed is what was
        # applied here, so a refit upstream propagates without a change here.
        "transmission": dict(transmission, **{
            "applied_by_this_model": (
                "read from the upstream document and applied unchanged. This "
                "model fits nothing and hard-codes no coefficient."
            ),
            "symmetry_assumption": assumptions["symmetry"],
        }),
        "export_exposure": require(
            upstream, "metadata.export_exposure",
            "the scenario is measured against it",
        ),
        "reference_price": (upstream.get("metadata") or {}).get("reference_price"),
        "destinations": destinations,
        "upstream": {
            "model": "ag-commodity-bundles/corn-price (node 3)",
            "generated_at": upstream.get("generated_at"),
            "date": date,
            "tables": (upstream.get("metadata") or {}).get("tables"),
            "upstream_of_that": (upstream.get("metadata") or {}).get("upstream"),
        },
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metadata": metadata,
        "scenario": scenario,
        "national": national,
        "assumptions": assumptions,
        "upstream_price_impact": carried,
    }


def main(argv):
    if len(argv) < 3:
        raise RunError(
            "usage: runner.py <corn_price_impact.json> <scenario.json>"
        )
    upstream = read_json(argv[1])
    scenario_raw = read_json(argv[2])
    bushels, label = read_scenario(scenario_raw)

    rows, dest_meta = load_destinations()
    destinations = destination_context(rows, dest_meta)

    document = process(upstream, bushels, label, destinations, dest_meta)

    national = document["national"]
    log(
        f"scenario {bushels:+,.1f} mil bu"
        + (f" ({label})" if label else "")
        + f" = {document['scenario']['equivalent_supply_shock_pct']:+.3f}% of "
        f"{document['scenario']['measured_against']['total_use_mil_bu']:,.0f} "
        "mil bu total use"
    )
    log(
        f"weather  {national['weather']['price_impact_pct']:+.2f}% "
        f"[{national['weather']['price_impact_pct_low']:+.2f}, "
        f"{national['weather']['price_impact_pct_high']:+.2f}] (from node 3)"
    )
    log(
        f"trade    {national['trade']['price_impact_pct']:+.2f}% "
        f"[{national['trade']['price_impact_pct_low']:+.2f}, "
        f"{national['trade']['price_impact_pct_high']:+.2f}]"
    )
    log(
        f"combined {national['combined']['price_impact_pct']:+.2f}% "
        f"[{national['combined']['price_impact_pct_low']:+.2f}, "
        f"{national['combined']['price_impact_pct_high']:+.2f}] "
        f"= {national['combined']['price_impact_usd_bu']:+.4f} $/bu on "
        f"{national['reference_price_usd_bu']}"
    )

    json.dump(document, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except RunError as exc:
        print(f"corn-trade-policy: {exc}", file=sys.stderr)
        raise SystemExit(1)
