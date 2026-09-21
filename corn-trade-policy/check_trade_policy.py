#!/usr/bin/env python3
"""
Validation check for corn-trade-policy. Not part of the model image.

    python check_trade_policy.py [run/corn_trade_policy_impact.output.json]

Proves the modelling claims, not the plumbing.

Note what is NOT here: a historical episode reproducing a known price move. The
upstream model validates against the 2012 drought because a drought leaves a
measurable hole in the crop. The two candidate trade episodes do not. Measured,
from the committed destination table and the upstream balance sheet: US corn
sales to China fell from 118 mil bu in marketing year 2023 to 1 mil bu in 2024
while TOTAL US corn exports rose from 2,255 to 2,873 mil bu, and across the 1980
Soviet embargo US corn exports were 2,401 mil bu in 1979 against 2,391 in 1980.
Both episodes reallocated instead of disappearing, so neither offers an
aggregate bushel loss to price. That is the model's own headline caveat, and the
honest consequence is that this suite proves the arithmetic, the labelling and
the loud failures rather than a reproduced number.

The things that could be wrong here and still produce a plausible-looking
document are: the scenario divided by the wrong denominator, the sign inverted,
the two components added instead of composed, a coefficient quietly hard-coded
so an upstream refit stops propagating, an interval dropped, and an incoherent
scenario priced instead of refused. Each of those has a check.

Exits non-zero on the first failure, after printing every result.
"""
import csv
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only on Python < 3.11
    print(
        "check_trade_policy.py needs Python 3.11 or newer to read Modelfile.toml "
        f"(running {sys.version.split()[0]}). The model image is python:3.12-slim; "
        "run the check on a matching interpreter, for example:\n"
        "    uv run --python 3.12 python corn-trade-policy/check_trade_policy.py",
        file=sys.stderr,
    )
    raise SystemExit(2)

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE.parent / "run" / "corn_trade_policy_impact.output.json"
SAMPLE = HERE / "sample_corn_price_impact.json"
PAYLOAD = HERE / "sample_payload.json"
SCENARIO = HERE / "sample_scenario.json"
RUNNER = HERE / "runner.py"
MODELFILE = HERE / "Modelfile.toml"
DESTINATIONS = HERE / "destinations.csv"
DESTINATIONS_META = HERE / "destinations.meta.json"
README = HERE / "README.md"

PASSES = []
FAILURES = []


def check(label, condition, detail=""):
    (PASSES if condition else FAILURES).append(label)
    mark = "pass" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
    return condition


def close(a, b, tolerance):
    return abs(a - b) <= tolerance


def prose(text):
    """Lowercased with runs of whitespace collapsed.

    These checks look for statements in prose that lives in a hard-wrapped
    Markdown file, so a plain substring match would depend on where a paragraph
    happens to wrap and would break the next time someone reflows it. The
    statement is what matters, not the line breaks.
    """
    return " ".join((text or "").split()).lower()


def run_model(upstream_path, scenario_path):
    """Run the runner out of process. Returns (exit code, document or None, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(RUNNER), str(upstream_path), str(scenario_path)],
        capture_output=True, text=True,
    )
    document = None
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            document = json.loads(proc.stdout)
        except json.JSONDecodeError:
            document = None
    return proc.returncode, document, proc.stderr


def run_case(upstream, scenario):
    """Run one modified case from in-memory documents."""
    with tempfile.TemporaryDirectory() as tmp:
        up = Path(tmp) / "upstream.json"
        sc = Path(tmp) / "scenario.json"
        up.write_text(json.dumps(upstream))
        sc.write_text(json.dumps(scenario))
        return run_model(up, sc)


def load_upstream():
    return json.loads(SAMPLE.read_text())


# ------------------------------------------------------------ files (AC-1)

def check_files():
    print("\nAC-1  the bundle carries what a Model Home bundle needs")
    for name in (
        "Modelfile.toml", "Dockerfile", "runner.py", "build_destinations.py",
        "destinations.csv", "destinations.meta.json", "check_trade_policy.py",
        "sample_corn_price_impact.json", "sample_scenario.json",
        "sample_payload.json", "README.md",
    ):
        check(f"{name} exists", (HERE / name).exists())


def check_sample_payload():
    """The keyed envelope the platform's run form takes.

    This model declares TWO inputs, so the run form asks for one slot per input
    name rather than a single document -- which is exactly what makes a file
    called "the sample input" misleading here. The envelope is committed so
    there is something to paste, and it is a DERIVED artifact, so the checks
    below are about drift: its keys must be the declared input names, and its
    values must be the two committed sample files byte for byte.
    """
    print("\nthe run form's keyed envelope")
    if not check("sample_payload.json exists", PAYLOAD.exists()):
        return
    try:
        payload = json.loads(PAYLOAD.read_text())
    except json.JSONDecodeError as exc:
        check("sample_payload.json is valid JSON", False, str(exc))
        return
    check("sample_payload.json is valid JSON", True)

    declared = [i["name"] for i in tomllib.loads(MODELFILE.read_text())["inputs"]]
    check("its keys are exactly the model's declared input names",
          set(payload) == set(declared),
          f"payload {sorted(payload)} against declared {sorted(declared)}")
    check("it carries the committed upstream sample unchanged",
          payload.get("corn_price_impact") == json.loads(SAMPLE.read_text()))
    check("it carries the committed scenario unchanged",
          payload.get("scenario") == json.loads(SCENARIO.read_text()))
    # The envelope is a paste target, not a runner input: runner.py takes the two
    # documents as separate paths and never reads this file.
    check("the runner does not read the envelope",
          "sample_payload" not in RUNNER.read_text())


# --------------------------------------------- the committed table (AC-14/16)

def check_destinations(document):
    print("\nAC-14/16  the destination table, its provenance and its tie-out")
    with open(DESTINATIONS, newline="") as fh:
        rows = list(csv.DictReader(fh))
    meta = json.loads(DESTINATIONS_META.read_text())

    check("destinations.csv has rows", bool(rows), f"{len(rows)} rows")
    check("the columns are the declared ones",
          set(rows[0]) == {"marketing_year", "destination", "exports_mil_bu",
                           "share_of_total_exports"})
    check("every exports figure is positive",
          all(float(r["exports_mil_bu"]) > 0 for r in rows))

    years = sorted({int(r["marketing_year"]) for r in rows})
    check("the committed window matches the meta",
          meta["period"] == f"{years[0]}-{years[-1]}",
          f"{meta['period']}")
    check("the window is contiguous", years == list(range(years[0], years[-1] + 1)))

    # The exclusion is derived from the tie-out, not hard-coded, so what matters
    # is that the excluded years are recorded, justified by a real error, and
    # genuinely absent from the table.
    excluded = meta["tie_out"]["excluded_years"]
    check("the meta records which years were excluded and why",
          bool(excluded), f"excluded {sorted(excluded)}")
    check("no excluded year is in the table",
          not (set(int(y) for y in excluded) & set(years)))
    check("every excluded year failed by a wide margin, not a hair",
          all(float(e) > 0.1 for e in excluded.values()),
          f"min error {min(float(e) for e in excluded.values()):.1%}")
    check("the committed years tie out to the balance sheet",
          meta["tie_out"]["max_relative_error_committed"]
          <= meta["tie_out"]["tolerance_relative"],
          f"max {meta['tie_out']['max_relative_error_committed']:.2e} "
          f"<= {meta['tie_out']['tolerance_relative']}")

    # Shares must be internally consistent with the totals the meta records.
    totals = meta["annual_total_exports_mil_bu"]
    bad = []
    for year in years:
        year_rows = [r for r in rows if int(r["marketing_year"]) == year]
        summed = sum(float(r["exports_mil_bu"]) for r in year_rows)
        if not close(summed, float(totals[str(year)]), 0.01):
            bad.append(year)
        for r in year_rows:
            implied = float(r["exports_mil_bu"]) / float(totals[str(year)])
            if not close(implied, float(r["share_of_total_exports"]), 1e-5):
                bad.append(year)
                break
    check("destinations sum to the recorded total and the shares agree",
          not bad, f"off: {sorted(set(bad))}" if bad else f"{len(years)} years")

    for field in ("vintage", "source", "period", "built_at", "conversion"):
        check(f"the meta records {field}", bool(meta.get(field)))
    check("the meta names the source_last_modified key even when ERS sends none",
          "source_last_modified" in meta)
    check("the meta says the table is context only",
          "context only" in meta["definitions"]["role"])
    check("the meta warns that the table lags the balance sheet",
          "never be presented as" in meta["definitions"]["lag"])

    carried = document["metadata"]["destinations"]
    check("the output carries the table's vintage and period",
          carried["vintage"] == meta["vintage"] and carried["period"] == meta["period"])
    check("the output says the destination table is context only",
          "context only" in carried["role"])
    check("the output's destination year is the table's latest",
          carried["marketing_year"] == meta["latest_marketing_year"],
          f"{carried['marketing_year']}")
    # The destination table ends one marketing year before the balance sheet.
    exposure = document["metadata"]["export_exposure"]
    check("the destination year is labelled apart from the balance-sheet year",
          carried["marketing_year"] != exposure["latest_complete"]["marketing_year"],
          f"destinations {carried['marketing_year']} vs balance sheet "
          f"{exposure['latest_complete']['marketing_year']}")


# ------------------------------------------------- the denominator (AC-6/9)

def check_denominator(document):
    print("\nAC-6/9  the scenario is divided by the declared basis, and only once")
    upstream = load_upstream()
    exposure = upstream["metadata"]["export_exposure"]["current"]
    expected_use = exposure["exports_mil_bu"] / exposure["export_share_of_use"]

    measured = document["scenario"]["measured_against"]
    check("the output names the basis it used",
          close(measured["total_use_mil_bu"], expected_use, 0.01),
          f"{measured['total_use_mil_bu']:,.1f} mil bu")
    check("the basis is labelled with its marketing year",
          measured["marketing_year"] == exposure["marketing_year"],
          f"marketing year {measured['marketing_year']}")
    check("the basis says whether it is a USDA projection",
          isinstance(measured["is_projection"], bool)
          and measured["is_projection"] == exposure["is_projection"])
    check("the output explains how the basis was derived",
          "export_share_of_use" in measured["derivation"])

    bushels = document["scenario"]["bushels_not_sold_mil_bu"]
    shock = document["national"]["trade"]["equivalent_supply_shock_pct"]
    check("the shock is the scenario over that basis",
          close(shock, bushels / expected_use * 100.0, 1e-3),
          f"{shock:+.4f}%")

    # Exports are a COMPONENT of use. Adding them would inflate the denominator
    # and shrink the shock; this asserts the model did not.
    inflated = expected_use + exposure["exports_mil_bu"]
    check("exports were not added to total use",
          not close(shock, bushels / inflated * 100.0, 1e-3),
          f"a double-counted basis would give {bushels / inflated * 100.0:+.4f}%")
    check("the output states that exports sit inside total use",
          "component of total use" in document["assumptions"]["denominator"])

    # The upstream us_trend_production_bu is on a 2022 Census acreage basis and
    # is 8.9% below the basis the coefficient was fitted on. Using it would be a
    # plausible-looking mistake, so its result is asserted to be absent.
    trend_basis_mil_bu = upstream["national"]["us_trend_production_bu"] / 1e6
    check("the upstream trend-production basis was NOT used",
          not close(shock, bushels / trend_basis_mil_bu * 100.0, 1e-3),
          f"it would have given {bushels / trend_basis_mil_bu * 100.0:+.4f}% "
          f"against {shock:+.4f}%")
    check("the output says which basis it rejected and why",
          "us_trend_production_bu" in document["assumptions"]["denominator"])


# ------------------------------------------------ the zero scenario (AC-3)

def check_zero_scenario(document):
    print("\nAC-3  an absent, empty or zero scenario leaves the upstream result alone")
    upstream = load_upstream()
    weather_pct = upstream["national"]["price_impact_pct"]

    for label, scenario in (
        ("an empty scenario object", {}),
        ("an explicit zero", {"bushels_not_sold_mil_bu": 0}),
        ("a null value", {"bushels_not_sold_mil_bu": None}),
        ("an empty string", {"bushels_not_sold_mil_bu": ""}),
    ):
        code, doc, stderr = run_case(upstream, scenario)
        if not check(f"{label} runs", code == 0, stderr.strip()[-90:] if code else ""):
            continue
        trade = doc["national"]["trade"]
        combined = doc["national"]["combined"]
        check(f"{label} gives a trade impact of exactly zero",
              trade["price_impact_pct"] == 0.0
              and trade["price_impact_pct_low"] == 0.0
              and trade["price_impact_pct_high"] == 0.0)
        check(f"{label} leaves the combined figure at the weather figure",
              close(combined["price_impact_pct"], weather_pct, 1e-3),
              f"{combined['price_impact_pct']} vs {weather_pct}")


# ------------------------------------------------------ the signs (AC-8)

def check_signs(document):
    print("\nAC-8  the sign convention runs the right way in both directions")
    upstream = load_upstream()

    code, lost, _ = run_case(upstream, {"bushels_not_sold_mil_bu": 300})
    check("a lost-sales scenario runs", code == 0)
    check("demand removed pushes the price DOWN",
          lost["national"]["trade"]["price_impact_pct"] < 0,
          f"{lost['national']['trade']['price_impact_pct']:+.4f}%")
    check("demand removed is a positive equivalent supply shock",
          lost["national"]["trade"]["equivalent_supply_shock_pct"] > 0)

    code, gained, _ = run_case(upstream, {"bushels_not_sold_mil_bu": -300})
    check("an extra-sales scenario runs", code == 0)
    check("an extra-sales scenario reports signed, negative shares",
          gained["scenario"]["share_of_total_use"] < 0
          and gained["scenario"]["share_of_latest_complete_exports"] < 0,
          f"{gained['scenario']['share_of_total_use']:.4%} of use")
    check("demand added pushes the price UP",
          gained["national"]["trade"]["price_impact_pct"] > 0,
          f"{gained['national']['trade']['price_impact_pct']:+.4f}%")

    # Log-linear, so equal and opposite shocks are not equal and opposite
    # impacts. Asserting that keeps anyone from "fixing" the asymmetry later.
    check("equal and opposite shocks give unequal impacts, as a log form must",
          not close(abs(lost["national"]["trade"]["price_impact_pct"]),
                    abs(gained["national"]["trade"]["price_impact_pct"]), 1e-6),
          f"{lost['national']['trade']['price_impact_pct']:+.4f}% vs "
          f"{gained['national']['trade']['price_impact_pct']:+.4f}%")


# ------------------------------------------------- the composition (AC-10)

def check_composition(document):
    print("\nAC-10  the two shocks compose inside the transmission, not after it")
    upstream = load_upstream()
    b0 = upstream["metadata"]["transmission"]["shock_coefficient"]
    exposure = upstream["metadata"]["export_exposure"]["current"]
    total_use = exposure["exports_mil_bu"] / exposure["export_share_of_use"]

    bushels = document["scenario"]["bushels_not_sold_mil_bu"]
    d_trade = bushels / total_use
    d_weather = upstream["national"]["us_yield_shock_pct"] / 100.0

    def impact(d):
        return (math.exp(b0 * d) - 1.0) * 100.0

    # The hand-worked case, to full precision.
    check("the trade impact reproduces by hand",
          close(document["national"]["trade"]["price_impact_pct"],
                round(impact(d_trade), 4), 1e-9),
          f"{document['national']['trade']['price_impact_pct']:+.4f}%")
    check("the combined impact reproduces by hand",
          close(document["national"]["combined"]["price_impact_pct"],
                round(impact(d_weather + d_trade), 4), 1e-9),
          f"{document['national']['combined']['price_impact_pct']:+.4f}%")

    naive_sum = (document["national"]["weather"]["price_impact_pct"]
                 + document["national"]["trade"]["price_impact_pct"])
    combined = document["national"]["combined"]["price_impact_pct"]
    check("the combined figure is NOT the sum of the two components",
          not close(combined, naive_sum, 1e-4),
          f"combined {combined:+.4f}% against a sum of {naive_sum:+.4f}%")

    # The log form means the components compound multiplicatively.
    compounded = ((1 + impact(d_weather) / 100.0) * (1 + impact(d_trade) / 100.0)
                  - 1.0) * 100.0
    check("the components compound multiplicatively, as exp(b*d) requires",
          close(combined, round(compounded, 4), 1e-4),
          f"{compounded:+.4f}%")
    check("the total shock is the sum of the two shocks",
          close(document["national"]["combined"]["total_shock_pct"],
                round((d_weather + d_trade) * 100.0, 4), 1e-9))
    check("the output explains the composition in words",
          "not the sum" in document["assumptions"]["composition"].lower())


# -------------------------------------- the coefficient is upstream (AC-11)

def check_transmission_is_upstream(document):
    print("\nAC-11  no coefficient is hard-coded; an upstream refit propagates")
    source = RUNNER.read_text()
    for literal in ("0.7825", "0.78255", "-1.2692", "-0.3932"):
        check(f"runner.py does not contain the literal {literal}",
              literal not in source)

    upstream = load_upstream()
    check("the output echoes the upstream coefficient",
          close(document["metadata"]["transmission"]["shock_coefficient"],
                upstream["metadata"]["transmission"]["shock_coefficient"], 0.0))
    check("the output echoes the upstream fit statistics",
          document["metadata"]["transmission"]["fit"]
          == upstream["metadata"]["transmission"]["fit"])

    # Double the coefficient upstream: the result must move. If it does not, the
    # runner is applying something of its own.
    refitted = json.loads(json.dumps(upstream))
    refitted["metadata"]["transmission"]["shock_coefficient"] *= 2
    refitted["metadata"]["transmission"]["shock_coefficient_ci95"] = [
        c * 2 for c in refitted["metadata"]["transmission"]["shock_coefficient_ci95"]
    ]
    # The weather figure must move with it, or the reproduction guard stops the
    # run -- which is itself the behaviour being relied on here.
    d_weather = refitted["national"]["us_yield_shock_pct"] / 100.0
    b0 = refitted["metadata"]["transmission"]["shock_coefficient"]
    refitted["national"]["price_impact_pct"] = round(
        (math.exp(b0 * d_weather) - 1.0) * 100.0, 4
    )
    code, doc, stderr = run_case(refitted, {"bushels_not_sold_mil_bu": 300})
    if check("a refitted upstream document still runs", code == 0,
             stderr.strip()[-90:] if code else ""):
        check("a doubled upstream coefficient changes the trade impact",
              not close(doc["national"]["trade"]["price_impact_pct"],
                        document["national"]["trade"]["price_impact_pct"], 1e-6),
              f"{doc['national']['trade']['price_impact_pct']:+.4f}% against "
              f"{document['national']['trade']['price_impact_pct']:+.4f}%")


# -------------------------------------------------- the intervals (AC-12)

def check_intervals(document):
    print("\nAC-12  no figure ships without its range, and the ranges are ordered")
    national = document["national"]
    for component in ("weather", "trade", "combined"):
        block = national[component]
        for stem in ("price_impact_pct", "price_impact_usd_bu"):
            low, central, high = (
                block[f"{stem}_low"], block[stem], block[f"{stem}_high"]
            )
            check(f"{component}.{stem} carries both ends",
                  all(isinstance(v, (int, float)) for v in (low, central, high)))
            check(f"{component}.{stem} is ordered low <= central <= high",
                  low <= central <= high,
                  f"[{low}, {central}, {high}]")

    upstream = load_upstream()
    ci95 = upstream["metadata"]["transmission"]["shock_coefficient_ci95"]
    check("the interval comes from the upstream bootstrap, reused",
          document["metadata"]["transmission"]["shock_coefficient_ci95"] == ci95)
    check("the output says the interval is about the transmission, not the price",
          "not what the corn price will do"
          in document["assumptions"]["interval_definition"])
    check("the output says the two intervals are never added",
          "never added" in document["assumptions"]["interval_definition"])

    # Both components use one coefficient, so the combined interval must come
    # from the combined shock rather than from summing two intervals.
    summed_low = (national["weather"]["price_impact_pct_low"]
                  + national["trade"]["price_impact_pct_low"])
    check("the combined interval is not the sum of the two intervals",
          not close(national["combined"]["price_impact_pct_low"], summed_low, 1e-4),
          f"{national['combined']['price_impact_pct_low']:+.4f}% against a summed "
          f"{summed_low:+.4f}%")


# ------------------------------------------- the scenario in context (AC-17)

def check_scenario_context(document):
    print("\nAC-17  the scenario is reported against the market it removes demand from")
    scenario = document["scenario"]
    upstream = load_upstream()
    exposure = upstream["metadata"]["export_exposure"]
    bushels = scenario["bushels_not_sold_mil_bu"]

    check("the scenario is reported as a share of total use",
          close(scenario["share_of_total_use"],
                bushels / scenario["measured_against"]["total_use_mil_bu"], 1e-5),
          f"{scenario['share_of_total_use']:.2%}")
    check("the scenario is reported as a share of a COMPLETE year's exports",
          close(scenario["share_of_latest_complete_exports"],
                bushels / exposure["latest_complete"]["exports_mil_bu"], 1e-5),
          f"{scenario['share_of_latest_complete_exports']:.2%} of marketing year "
          f"{exposure['latest_complete']['marketing_year']}")
    check("the export ceiling is an actual, never a projection",
          exposure["latest_complete"]["is_projection"] is False)
    check("the output says the scenario was stated by the user",
          "input" in scenario["stated_by"] and "not an output" in scenario["stated_by"])
    check("the scenario's label is carried through",
          scenario["label"] == json.loads(SCENARIO.read_text())["scenario_label"])

    destinations = document["metadata"]["destinations"]["destinations"]
    check("the output names who actually buys US corn",
          len(destinations) >= 5, f"{len(destinations)} entries")
    check("the destination shares are a fraction of one",
          all(0.0 <= d["share_of_total_exports"] <= 1.0 for d in destinations))
    check("the destinations are ordered largest first",
          all(destinations[i]["exports_mil_bu"] >= destinations[i + 1]["exports_mil_bu"]
              for i in range(len(destinations) - 2)))


# ------------------------------------------------ loud failures (AC-7/15)

def check_loud_failures():
    print("\nAC-7/15  a malformed or incoherent run stops and says why")
    upstream = load_upstream()
    good = {"bushels_not_sold_mil_bu": 300}

    def expect_failure(label, doc, scenario, *needles):
        code, _, stderr = run_case(doc, scenario)
        ok = check(f"{label} exits non-zero", code == 1, f"exit {code}")
        if ok:
            check(f"{label}: the message names the problem",
                  all(n in stderr for n in needles),
                  stderr.strip().splitlines()[-1][:110] if stderr.strip() else "")
        check(f"{label}: no traceback is printed", "Traceback" not in stderr)

    stripped = json.loads(json.dumps(upstream))
    del stripped["metadata"]["transmission"]
    expect_failure("a missing upstream transmission", stripped, good,
                   "metadata.transmission")

    stripped = json.loads(json.dumps(upstream))
    del stripped["metadata"]["export_exposure"]
    expect_failure("a missing upstream export exposure", stripped, good,
                   "metadata.export_exposure")

    zeroed = json.loads(json.dumps(upstream))
    zeroed["metadata"]["export_exposure"]["current"]["export_share_of_use"] = 0
    expect_failure("a zero export share", zeroed, good, "export_share_of_use")

    tampered = json.loads(json.dumps(upstream))
    tampered["national"]["price_impact_pct"] = 5.0
    expect_failure("an upstream result that does not reproduce", tampered, good,
                   "does not reproduce")

    ceiling = upstream["metadata"]["export_exposure"]["latest_complete"]["exports_mil_bu"]
    expect_failure("a scenario larger than the whole export programme", upstream,
                   {"bushels_not_sold_mil_bu": ceiling + 1},
                   "exceeds total US corn exports")
    expect_failure("the same scenario in the other direction", upstream,
                   {"bushels_not_sold_mil_bu": -(ceiling + 1)},
                   "exceeds total US corn exports")

    expect_failure("a scenario given as a string", upstream,
                   {"bushels_not_sold_mil_bu": "300"},
                   "bushels_not_sold_mil_bu")
    expect_failure("a non-finite scenario", upstream,
                   {"bushels_not_sold_mil_bu": float("inf")},
                   "bushels_not_sold_mil_bu")
    expect_failure("a scenario that is not an object", upstream, [300],
                   "not an object")

    # A falsey non-string label violates the declared string schema just as
    # surely as 123 does, and must not be quietly coerced to an empty label.
    for bad_label in (0, False, [], {}):
        expect_failure(f"a scenario_label of {bad_label!r}", upstream,
                       {"bushels_not_sold_mil_bu": 300, "scenario_label": bad_label},
                       "scenario_label")

    # Every published range comes from the upstream interval, so a malformed or
    # non-finite bound must stop the run rather than reach sorted() or the
    # output. float("bad") would otherwise exit with a traceback.
    for bad_ci in (["bad", 1], [None, -0.4], [float("nan"), -0.4],
                   [-1.27, float("inf")]):
        broken = json.loads(json.dumps(upstream))
        broken["metadata"]["transmission"]["shock_coefficient_ci95"] = bad_ci
        expect_failure(f"an upstream interval of {bad_ci!r}", broken, good,
                       "shock_coefficient_ci95")

    # A scenario exactly at the ceiling is coherent and must still run.
    code, doc, _ = run_case(upstream, {"bushels_not_sold_mil_bu": ceiling})
    check("a scenario exactly at the ceiling still runs", code == 0, f"exit {code}")


# ------------------------------------------- honesty, in all three places

def check_three_places(document):
    print("\nAC-13/18  the labelling is in the output, the README and the Modelfile")
    not_for = prose(tomllib.loads(MODELFILE.read_text())["not_for"])
    readme = prose(README.read_text()) if README.exists() else ""
    assumptions = document["assumptions"]
    blob = prose(json.dumps(assumptions))

    statements = {
        "not a price forecast": (
            "not a price forecast" in blob or "not a forecast" in blob,
            "not a price forecast" in not_for,
            "not a price forecast" in readme,
        ),
        "not investment advice": (
            "not investment advice" in blob,
            "not investment advice" in not_for,
            "not investment advice" in readme,
        ),
        "not a political forecast": (
            "not a political forecast" in blob,
            "not a political forecast" in not_for,
            "not a political forecast" in readme,
        ),
        "the scenario is an input": (
            "input" in assumptions["scenario_is_an_input"],
            "input you state" in not_for or "is an input" in not_for,
            "an input" in readme,
        ),
        "trade reallocates": (
            "reallocat" in blob,
            "reallocat" in not_for,
            "reallocat" in readme,
        ),
        "the symmetry assumption": (
            "symmetry" in blob,
            "symmetry" in not_for,
            "symmetry" in readme,
        ),
    }
    for statement, (in_output, in_modelfile, in_readme) in statements.items():
        check(f"the output states {statement!r}", in_output)
        check(f"the Modelfile not_for states {statement!r}", in_modelfile)
        check(f"the README states {statement!r}", in_readme)

    check("the output's not_captured names the soybean channel",
          any("soybean" in item for item in assumptions["not_captured"]))
    check("the output's not_captured carries the upstream model's own list",
          any(item.startswith("inherited from the upstream")
              for item in assumptions["not_captured"]))
    check("the output carries the measured reallocation evidence",
          "2,401" in assumptions["reallocation"]
          and "China" in assumptions["reallocation"])


# ------------------------------------------------- schema and caps (AC-19)

def check_annotations(document):
    print("\nAC-19  the Modelfile is inside the platform's limits and fully typed")
    model = tomllib.loads(MODELFILE.read_text())

    check("validity_domain is within 600 characters",
          len(model["validity_domain"]) <= 600, f"{len(model['validity_domain'])}")
    check("provenance is within 400 characters",
          len(model["provenance"]) <= 400, f"{len(model['provenance'])}")
    check("not_for is kept under 600 characters, as the upstream bundle does",
          len(model["not_for"]) < 600, f"{len(model['not_for'])}")
    check("determinism is declared", model["determinism"] == "deterministic")

    def walk(schema, path):
        """Every key in a `required` array needs a declared properties.<key>.type."""
        problems = []
        if not isinstance(schema, dict):
            return problems
        properties = schema.get("properties") or {}
        for key in schema.get("required") or []:
            declared = properties.get(key) or {}
            if "type" not in declared:
                problems.append(f"{path}.{key}")
        for key, child in properties.items():
            problems.extend(walk(child, f"{path}.{key}"))
        if "items" in schema:
            problems.extend(walk(schema["items"], f"{path}[]"))
        return problems

    problems = []
    for block in ("inputs", "outputs"):
        for entry in model[block]:
            problems.extend(walk(entry["schema"], f"{block}.{entry['name']}"))
    check("every required key has a declared type", not problems,
          f"untyped: {problems}" if problems else "")

    outputs = {o["name"]: o for o in model["outputs"]}
    check("there is exactly one output", len(outputs) == 1, f"{sorted(outputs)}")
    required = set(outputs["corn_trade_policy_impact"]["schema"]["required"])
    check("the output's required set includes 'scenario'", "scenario" in required)
    # The upstream document's required set. Sharing it would make a downstream
    # step unable to tell the two apart.
    check("the output's required set differs from the upstream document's",
          required != {"generated_at", "metadata", "national", "regions", "assumptions"},
          f"{sorted(required)}")

    inputs = {i["name"]: i for i in model["inputs"]}
    check("the upstream input binds on the right required set",
          set(inputs["corn_price_impact"]["schema"]["required"])
          == {"generated_at", "metadata", "national", "regions", "assumptions"})
    check("the scenario input requires nothing, so the model runs standalone",
          inputs["scenario"]["schema"]["required"] == [])
    check("the scenario input ships a runnable example to paste",
          "bushels_not_sold_mil_bu" in (inputs["scenario"]["schema"].get("default") or {}))

    check("the declared output name matches what the run line redirects to",
          "corn_trade_policy_impact.output.json" in model["run"])

    # A consumer validating against the declared schema alone must be able to
    # rely on the market context AC-17 promises, so anything the runner always
    # emits inside `scenario` belongs in that object's required list.
    scenario_schema = (outputs["corn_trade_policy_impact"]["schema"]
                       ["properties"]["scenario"])
    scenario_required = set(scenario_schema["required"])
    always_emitted = {
        "bushels_not_sold_mil_bu", "equivalent_supply_shock_pct",
        "share_of_total_use", "share_of_latest_complete_exports",
        "measured_against", "stated_by",
    }
    check("every scenario field the runner always emits is declared required",
          always_emitted <= scenario_required,
          f"missing: {sorted(always_emitted - scenario_required)}"
          if always_emitted - scenario_required else "")
    check("the scenario document carries every key the schema requires",
          scenario_required <= set(document["scenario"]),
          f"absent: {sorted(scenario_required - set(document['scenario']))}"
          if scenario_required - set(document["scenario"]) else "")

    # The shares are signed, because a negative scenario (extra sales) is
    # supported. The schema text must not promise a 0..1 range it does not keep.
    for field in ("share_of_total_use", "share_of_latest_complete_exports"):
        text = scenario_schema["properties"][field]["description"].lower()
        check(f"{field} is documented as signed, not as 0 to 1",
              "signed" in text and "from 0 to 1" not in text)


# ----------------------------------------------------- documentation (AC-20)

def check_readme():
    print("\nAC-20  the README documents what a reader needs")
    if not check("README.md exists", README.exists()):
        return
    text = prose(README.read_text())
    for topic, needle in (
        ("the two inputs", "scenario"),
        ("wiring the scenario as an inline literal", "inline"),
        ("the denominator", "total use"),
        ("the sign convention", "sign"),
        ("the reused coefficient", "upstream"),
        ("the symmetry assumption", "symmetry"),
        ("the log-space composition", "compose"),
        ("the destination table", "destination"),
        ("determinism", "determinis"),
        ("the reallocation evidence", "reallocat"),
        ("the soybean channel", "soybean"),
        ("what the model is not", "not a forecast"),
    ):
        check(f"the README covers {topic}", needle in text, f"looked for {needle!r}")


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUTPUT
    if not path.exists():
        code, document, stderr = run_model(SAMPLE, SCENARIO)
        if code != 0 or document is None:
            print(f"could not run the model to produce a document:\n{stderr}",
                  file=sys.stderr)
            return 2
    else:
        document = json.loads(path.read_text())

    check_files()
    check_sample_payload()
    check_destinations(document)
    check_denominator(document)
    check_zero_scenario(document)
    check_signs(document)
    check_composition(document)
    check_transmission_is_upstream(document)
    check_intervals(document)
    check_scenario_context(document)
    check_loud_failures()
    check_three_places(document)
    check_annotations(document)
    check_readme()

    total = len(PASSES) + len(FAILURES)
    print(f"\n{len(PASSES)}/{total} checks pass")
    if FAILURES:
        print("\nfailed:")
        for label in FAILURES:
            print(f"  - {label}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
