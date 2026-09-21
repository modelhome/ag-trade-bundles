# Plan: Corn trade policy

Source brief: docs/features/0001-corn-trade-policy.md
Status: implemented
Planned against commit: f3c75d0 ("chore: scaffold ag-trade-bundles")
Base commit: f3c75d0 (branch feat/0001-corn-trade-policy created from it)

Upstream at planning time: `ag-commodity-bundles` `main` = `896f6ca`, "Merge pull
request #2: corn-price export exposure (brief 0002)". `metadata.export_exposure`
is present in `corn-price/runner.py` and `corn-price/price_history.meta.json`.
Every node 3 field named below was read from that merged checkout, not from the
brief and not from memory.

## Outcome

`corn-trade-policy/` is a Model Home bundle that takes node 3's
`corn_price_impact` document and a stated export-demand scenario -- million
bushels of US corn not sold -- and emits one national JSON document reporting the
trade-driven price impact beside node 3's weather-driven one, each with its own
interval, plus a combined figure composed inside the transmission's exponential
rather than by adding percentages. It fits nothing, fetches nothing at run time,
and re-derives nothing node 3 already produces.

## Scope

### In scope

- The `corn-trade-policy/` bundle: `Modelfile.toml`, `Dockerfile`, `runner.py`,
  `build_destinations.py`, `destinations.csv`, `destinations.meta.json`,
  `check_trade_policy.py`, `sample_input.json`, `sample_scenario.json`,
  `README.md`.
- Two declared inputs: node 3's document, and the scenario as an inline literal.
- The bushels-to-shock conversion, the sign convention, the reused coefficient
  with its symmetry assumption, the log-space composition, and intervals on
  every headline figure.
- A committed destination-context table from ERS Table 22, context only, plus
  the loud failure it enables.
- Repo-level documentation: `README.md`'s bundle table and `CLAUDE.md`'s task
  list, bundle section and illustrative arithmetic (D-2).

### Out of scope

As stated in the brief: nodes 1-3, the flow definition, any refit, any tariff
rate or schedule, any political forecast, the soybean channel (documented only),
per-region allocation, FAS GATS / FAS Export Sales / Census USA Trade Online, a
live reference price, and a within-season futures transmission.

## Assumptions and decisions

The brief's four design questions were answered by John on 2026-09-20 and are
restated here because the reader of this plan may not have seen that exchange:
**corn only with a destination context table**, the soybean channel documented
in the README and not built; **reuse node 3's coefficient** with the symmetry
assumption declared; **bushels not sold, national**, with the tariff-to-bushels
step left to whoever states the scenario; **national-only output**, no region
join. Two further questions were answered on 2026-09-20 while planning:

- **D-1 (the brief's open decision) -- the denominator is total use, recovered
  from node 3's metadata.** `total_use_mil_bu = metadata.export_exposure.current
  .exports_mil_bu / metadata.export_exposure.current.export_share_of_use`, which
  is 3275.0 / 0.20241 = 16,180 mil bu on the committed row. Nothing new is
  sourced and the work stays in one PR. The cost is a documented basis gap: node
  3's coefficient is fitted on the national yield's deviation from an ERS trend,
  whose commensurate base is area harvested times trend yield -- 16,344 mil bu
  for marketing year 2026, so total use is 1.0% below it this year, and the gap
  has run -3.4% to +6.7% over 2015-2026. The gap is stated in the output
  document and the README, not buried. **Node 3's `us_trend_production_bu`
  (14,894 mil bu) is explicitly not used**: it is built from 2022 Census acreage
  and sits 8.9% below the ERS basis, which would inflate a 300 mil bu scenario
  from -1.440% to -1.564%. Asking node 3 to carry the exact figure is logged as a
  follow-up.
- **D-2 -- the same PR updates `README.md` and `CLAUDE.md`.** Brief 0002 set the
  precedent that every published figure the work moves is corrected in the same
  commit. Both documents currently say the bundle is not built, and CLAUDE.md's
  illustrative arithmetic uses the denominator D-1 just settled.

Decisions taken while planning, under the brief's authority:

- **D-3 -- the scenario is in million bushels**, field
  `bushels_not_sold_mil_bu`. Every quantity it is compared against -- total use,
  exports, the destination table -- is in mil bu, so this is the unit that needs
  the fewest conversions. Node 3's `us_production_shock_bu` is in bushels and is
  not read.
- **D-4 -- sign convention.** Bushels *not sold* are demand removed, which for
  price is equivalent to a surplus of the same size, so a positive
  `bushels_not_sold_mil_bu` produces a positive equivalent supply shock and
  therefore a negative price impact. A negative scenario (extra sales) runs and
  gives a positive impact.
- **D-5 -- one coefficient, so one interval on the combined shock.** The weather
  and trade components share `b0`; their intervals are perfectly correlated and
  must not be added. The combined interval applies `b0_low` and `b0_high` to the
  summed shock inside the exponential, mirroring node 3's
  `impacts = sorted([impact_pct(b0_low), impact_pct(b0_high)])`.
- **D-6 -- marketing-year anchoring.** The denominator and the reference price
  come from the **current** marketing year, which is node 3's own default basis
  and is a WASDE projection, flagged `is_projection` in the output. The
  loud-failure threshold and the destination context come from the **latest
  complete** marketing year, because a threshold must be an actual and never a
  projection. The output labels both years, and AC-17's shares are reported
  against the latest complete year exactly as the brief states.
- **D-7 -- no `transmission.json` in this bundle.** `shock_coefficient`,
  `shock_coefficient_ci95`, `terms`, `coefficients`, `fit` and `sources` are read
  from the input document's `metadata.transmission` and echoed into node 4's
  output. A document with no `metadata.transmission` fails loudly. This is what
  makes "node 4 never refits node 3's transmission" structurally true and means
  a node 3 refit propagates automatically.
- **D-8 -- the destination table.** All destinations ERS Table 22 carries for
  `commodity = Corn`, marketing years **1991 onward**. 1989 and 1990 are excluded
  by an explicit, commented rule: their reported world totals are 637 and 392
  thousand metric tons against roughly 50,000 in later years, so the series is
  incomplete, and the build script names the exclusion rather than silently
  slicing. Converted to mil bu at build time at 39.3683 bu per metric ton, with
  both units and the factor in a comment.
- **D-9 -- the output nests `national` into `weather`, `trade` and `combined`
  sub-objects.** Flow binding compares only the top-level required-key set, so
  nesting is free, and three parallel sub-objects make "reported separately" the
  shape of the document rather than a claim about it.
- **D-10 -- verification runs under `uv run --python 3.12`.** System `python3` on
  this host is 3.9.6 and has no `tomllib`, which `check_trade_policy.py` needs to
  read `Modelfile.toml`; the image is `python:3.12-slim`, so 3.12 is also the
  parity choice for the runner.
- **D-11 -- no pip layer**, matching node 3. The model is a division, an
  exponential, a table lookup and JSON I/O.

## Acceptance-criteria traceability

| ID | Acceptance criterion | Implementation | Verification | Status |
|---|---|---|---|---|
| AC-1 | Bundle contains the full file set, mirroring `corn-price/` | all 10 files under `corn-trade-policy/` | `check_files` -- 10/10 present | pass |
| AC-2 | Input 1 binds `corn_price_impact`, refused by `corn_price_regions` and node 2's snapshot | `Modelfile.toml` `[[inputs]]` required set | binding script: BINDS `corn_price_impact`; REFUSED `corn_price_regions`, `corn_yield_snapshot`, `corn_yield_trajectory` | pass |
| AC-3 | Scenario `required = []`; absent/empty/null/zero gives a zero trade component | `runner.py::read_scenario` | `check_zero_scenario` -- 4 forms, each gives trade 0.0 and combined = -0.1801 = node 3's figure | pass |
| AC-4 | Sample input is a real `corn_price_impact`; runner runs end to end | `sample_input.json` from merged node 3, `sample_scenario.json` | verification row 1, exit 0 | pass |
| AC-5 | `docker build` succeeds; `--network none` reproduces the local run apart from `generated_at` | `Dockerfile` | verification rows 4-5: identical apart from `generated_at` | pass |
| AC-6 | The denominator is D-1's basis, named in the output; `us_trend_production_bu` not used | `runner.py` `total_use_mil_bu` | `check_denominator` -- 16,180.031 mil bu; asserts the `us_trend_production_bu` result (+2.0143%) is NOT what was produced (+1.8541%) | pass |
| AC-7 | Optional node 3 fields presence-checked and fail loudly | `runner.py::require` / `require_number` | `check_loud_failures` -- missing transmission, missing exposure, zero share each exit 1 naming the path, no traceback | pass |
| AC-8 | Both signs behave correctly | `runner.py` sign convention (D-4) | `check_signs` -- +300 gives -1.4405%, -300 gives +1.4615%, asymmetric as a log form requires | pass |
| AC-9 | Exports never added to total use; output says exports sit inside use | `runner.py`; `assumptions.denominator` | `check_denominator` -- a double-counted basis would give +1.5420%, which is not what was produced | pass |
| AC-10 | Combined composed in log space, not by adding percentages | `runner.py::band` | `check_composition` -- combined -1.6179% against a naive sum of -1.6206%; matches the multiplicative compounding to 1e-4 | pass |
| AC-11 | No hard-coded transmission constant; read from input; fails loudly if absent; a refit changes the result | `runner.py` (D-7) | `check_transmission_is_upstream` -- no coefficient literal in source; a doubled upstream coefficient moves the trade impact | pass |
| AC-12 | Every headline has `_low`/`_high`, ordered, for all three components | `runner.py::band`, `sorted([...])` | `check_intervals` -- 12 figures checked; combined interval is not the sum of the two intervals | pass |
| AC-13 | Symmetry assumption in output, README and `not_for` | `runner.py` `assumptions.symmetry`; `README.md`; `Modelfile.toml` | `check_three_places` | pass |
| AC-14 | Destination table built only by its script, with meta, failing loudly, excluding bad years, entering no arithmetic | `build_destinations.py`, `destinations.meta.json` | `check_destinations` -- 2,312 rows, 1992-2024, 1989/1990/1991 excluded at 98.9%/99.1%/34.3% | pass |
| AC-15 | The check proves the enumerated modelling claims | `check_trade_policy.py` | **171/171 checks pass** | pass |
| AC-16 | Table 22 world total ties out to the balance sheet for the same year | `build_destinations.py` tie-out assertion | recorded in `destinations.meta.json`: max relative error 2.1e-06 over 33 committed years (see DEV-2 for why this is a build-time rather than check-time comparison) | pass |
| AC-17 | Scenario reported as a share of latest-complete exports and of total use, beside recent purchases | `runner.py` `scenario` block | `check_scenario_context` -- 1.85% of use, 8.76% of MY2025 exports, 9 destination entries | pass |
| AC-18 | not-a-forecast, not-advice, not-a-political-forecast, scenario-is-an-input, reallocation -- all three places | `Modelfile.toml`, `README.md`, `runner.py` | `check_three_places` -- 6 statements x 3 places = 18 checks | pass |
| AC-19 | Modelfile validates; caps respected; required keys typed; output required set includes `scenario` | `Modelfile.toml` | validator returns `OK`; validity_domain 525/600, provenance 356/400, not_for 548/600; every required key typed | pass |
| AC-20 | README documents all listed topics including the soybean channel | `corn-trade-policy/README.md` | `check_readme` -- 12 topics | pass |
## Verification

Run from the repository root unless a row says otherwise. `SP` is any scratch
directory. Baselines were taken on the feature branch at `f3c75d0`, before any
bundle file existed.

| Command | Purpose | Baseline result | Final result |
|---|---|---|---|
| `uv run --python 3.12 python corn-trade-policy/runner.py corn-trade-policy/sample_input.json corn-trade-policy/sample_scenario.json > $SP/impact.json` | the model runs end to end (AC-4) | no baseline: the runner did not exist | exit 0; weather -0.18%, trade -1.44%, combined -1.62% = -$0.0777/bu |
| `uv run --python 3.12 python corn-trade-policy/check_trade_policy.py $SP/impact.json` | the modelling claims (AC-3, 6-18, 20) | no baseline: the check did not exist | **171/171 checks pass**, exit 0 |
| `cd /Users/john/repos/modelhome && uv run python -m orchestration.modelfile validate <abs path>/corn-trade-policy/Modelfile.toml` | Modelfile structure and annotations (AC-19) | tool confirmed usable: returns `OK` on node 3's Modelfile | `OK`, exit 0, no annotation warnings |
| `cd corn-trade-policy && docker build -t ag-trade-corn-trade-policy:local .` | the image builds from the bundle folder as its own context (AC-5) | no baseline: no Dockerfile | exit 0 |
| `docker run --rm --network none -v "$PWD/run:/run" ag-trade-corn-trade-policy:local /run/corn_price_impact.json /run/scenario.json`, diffed against the local run ignoring `generated_at` | offline determinism (AC-5) | no baseline: no image | **identical** apart from `generated_at`; a bare `docker run` also works from the bundled samples |
| `cd /Users/john/repos/modelhome && uv run python <binding script>` | AC-2 | tool confirmed usable; the required set already bound `corn_price_impact` and was refused by `corn_price_regions` | BINDS `corn_price_impact`; REFUSED `corn_price_regions`, `corn_yield_snapshot`, `corn_yield_trajectory` |

No pre-existing failures: the repository had no checks before this branch, so
every result above is attributable to this work. The binding script is a
verification tool run from the modelhome checkout, not a committed bundle file;
this bundle takes no dependency on the platform repo.

## Implementation steps

1. **Read the merged node 3 bundle first** --
   `ag-commodity-bundles/corn-price/Modelfile.toml`, `runner.py`,
   `price_history.meta.json`, `check_price.py`, `Dockerfile` and `README.md` at
   `896f6ca`. Take every field name from there. The fields this bundle reads are
   `generated_at`; `metadata.date`; `metadata.transmission.{shock_coefficient,
   shock_coefficient_ci95, terms, coefficients, fit, sources}`;
   `metadata.export_exposure.{current, latest_complete, role}` each carrying
   `{marketing_year, exports_mil_bu, export_share_of_use, is_projection}`;
   `metadata.reference_price.{usd_bu, source}`;
   `metadata.tables.price_history.{vintage, source, period,
   latest_complete_marketing_year}`; `metadata.upstream`;
   `national.{date, us_yield_shock_pct, price_impact_pct, price_impact_pct_low,
   price_impact_pct_high, reference_price_usd_bu, price_impact_usd_bu,
   price_impact_usd_bu_low, price_impact_usd_bu_high}`; and
   `assumptions.not_captured`.
2. **Generate `sample_input.json`** by running merged node 3 on its own committed
   sample: `cd ag-commodity-bundles/corn-price && python runner.py
   sample_input.json $SP/regions.json > $SP/impact.json`. The result must contain
   `metadata.export_exposure`; if it does not, the checkout is stale and
   everything downstream is wrong. Commit it as `corn-trade-policy/sample_input.json`.
3. **Write `build_destinations.py`.** Reuse node 3's `build_price_history.py`
   shape: same `ERS_URL`, same `.ers-cache/` convention, same `last-modified`
   capture, same loud `SystemExit` on a missing series. Filter
   `table_name` starting `Table 22--U.S. corn and sorghum exports by selected
   destinations` with `commodity == "Corn"`, `frequency == "Annual"`,
   `timeperiod == "Marketing year Sep-Aug"`, `unit == "1,000 metric tons"`.
   Emit `destinations.csv` with `marketing_year, destination, exports_mil_bu,
   share_of_total_exports`, years 1991+ (D-8), and `destinations.meta.json` with
   the source URL, server `last-modified`, period, build date, the latest
   complete marketing year, a `definitions` block saying the table is context
   only, and the tie-out figure. **Fail loudly** on a missing `World total` row,
   a year whose destination shares do not sum to within tolerance of the world
   total, or a tie-out mismatch against node 3's `exports_mil_bu`.
4. **Run the build once** and commit the table and its meta. Do not hand-edit
   either.
5. **Write `runner.py`.** Mirror node 3's structure: module docstring stating
   what the model does and what it is not, `RunError`, `read_json`,
   `require_field`, stdout-only result, logs to stderr, `main(argv)` taking
   `argv[1]` as node 3's document and `argv[2]` as the scenario. Arithmetic, in
   order: recover `total_use_mil_bu` per D-1 and fail loudly if either
   `export_exposure` field is missing; read `b0` and its interval per D-7;
   `d_weather = national.us_yield_shock_pct / 100.0`;
   `d_trade = bushels_not_sold_mil_bu / total_use_mil_bu` per D-3 and D-4;
   `impact_pct(c, d) = (math.exp(c * d) - 1.0) * 100.0`; apply it at `d_trade`
   and at `d_weather + d_trade`, each with `sorted([impact_pct(b0_low, d),
   impact_pct(b0_high, d)])` per D-5; carry node 3's weather figures through
   unchanged rather than recomputing them; dollars at
   `reference_price * pct / 100.0` exactly as node 3 does. Every conversion gets
   a comment naming both units and the factor.
6. **Assert, in the runner, that the copied weather impact reproduces**
   `impact_pct(b0, d_weather)` to node 3's rounding, and fail loudly if not: that
   is the single cheapest detector of a stale or hand-edited upstream document.
7. **Build the output document** per D-9: top-level `generated_at`, `metadata`,
   `scenario`, `national`, `assumptions`, with `national` holding `weather`,
   `trade` and `combined`. `scenario` carries the bushels, the optional label,
   the equivalent supply shock, the share of latest-complete exports and of total
   use, the denominator with its value, source and marketing year, the
   `is_projection` flag, and a `stated_by` string saying the scenario is the
   user's assumption. `assumptions` carries `not_a_forecast`,
   `not_a_political_forecast`, `scenario_is_an_input`, `symmetry`, `denominator`
   (including the measured basis gap), `composition`, `reallocation`,
   `interval_definition`, `destinations_context` and `not_captured`, the last
   seeded from node 3's own list plus the soybean and acreage channel.
8. **Write `Modelfile.toml`.** Two `[[inputs]]`: node 3's document on the
   required-key set, with no `default` (the same reasoning node 3 gives -- a
   runnable example is too large to paste), and the scenario with `required = []`
   and a small runnable `default` that is the "Example to paste". One
   `[[outputs]]`, `corn_trade_policy_impact`, required set
   `["generated_at","metadata","scenario","national","assumptions"]`. `run`
   redirects stdout; `args = ["{input:corn_price_impact}", "{input:scenario}"]`.
   Annotations: `determinism = "deterministic"`, `expected_runtime = "seconds"`,
   `validity_domain` within 600 characters, `provenance` within 400, `not_for`
   under 600 by node 3's caution and naming all of AC-18's statements.
9. **Write the `Dockerfile`** on node 3's template: `python:3.12-slim`,
   `WORKDIR /app`, no pip layer (D-11), `COPY` of `runner.py`,
   `destinations.csv`, `destinations.meta.json` and both samples, header comment
   giving the local build and `--network none` run lines,
   `ENTRYPOINT ["python", "runner.py"]`, `CMD ["sample_input.json",
   "sample_scenario.json"]`. The build script and the check stay out.
10. **Write `check_trade_policy.py`** on `check_price.py`'s shape: `check(label,
    condition, detail)`, `close()`, a `run_model()` helper shelling out to the
    runner, `PASSES`/`FAILURES`, printing every result and exiting non-zero on
    any failure, with the 3.11+ `tomllib` guard node 3 prints. Functions per the
    traceability table. Loud-failure cases to cover: a missing
    `metadata.transmission`; a missing `metadata.export_exposure`; a scenario
    exceeding the latest complete marketing year's total exports; a non-finite or
    non-numeric `bushels_not_sold_mil_bu`. Each must exit non-zero, name the
    offending field or figure, and print no traceback.
11. **Run the verification table top to bottom** and record the results in it.
12. **Write `README.md`** covering every topic in AC-20, mirroring node 3's
    heading structure, with a dedicated soybean-channel section written to the
    brief's specification, and the measured reallocation evidence.
13. **Update `README.md` and `CLAUDE.md` at the repo root** per D-2: the bundle
    table's "Not yet built", CLAUDE.md's task list item 2, its
    "The `corn-trade-policy/` bundle" section, and its illustrative arithmetic
    paragraph, which uses the total-use denominator and should now point at D-1's
    decision and the measured basis gap rather than stand as a loose
    illustration. Add a "Verified results" block in node 3's style.

## Files likely to change

New: `corn-trade-policy/{Modelfile.toml, Dockerfile, runner.py,
build_destinations.py, destinations.csv, destinations.meta.json,
check_trade_policy.py, sample_input.json, sample_scenario.json, README.md}`.

Modified: `README.md`, `CLAUDE.md`.

Committed by `run` alongside the implementation:
`docs/features/0001-corn-trade-policy.md` and this plan, so the brief, the plan
and the code land in one pull request.

## Deviations from the plan

Four, all recorded while implementing and none changing the agreed design.

- **DEV-1 -- D-8's hard-coded window was wrong and is now derived.** The plan
  said to commit Table 22 from 1991 onward. Measured against Table 4 in the same
  file, **1991 is itself 34.3% short** (1989 by 98.9%, 1990 by 99.1%), so the
  planned rule would have committed a bad year. `build_destinations.py` now
  derives the window from the tie-out itself: a marketing year is committed only
  when its world total matches the balance sheet within 1e-4, the failures are
  recorded in the meta with their errors, and the script refuses to proceed if
  the excluded years are not an unbroken run at the start of the series. The
  committed years, 1992-2024, tie out to 2.1e-06.
- **DEV-2 -- AC-16 is verified at build time, not check time.** The plan implied
  the check would tie the destination table to node 3's `exports_mil_bu`
  directly. It cannot: node 3's `export_exposure` carries marketing years 2025
  and 2026, while Table 22 ends at 2024, so **no overlapping year exists**. The
  tie-out is therefore performed in the build script against Table 4 in the same
  download, recorded in `destinations.meta.json`, and the check asserts the
  recorded result and the exclusions rather than re-downloading 18 MB.
- **DEV-3 -- the committed table carries six decimals, not three.** ERS lists
  destinations as small as 3.9e-06 mil bu, which round to a false `0.000` at
  three decimals. The suite caught this as 88 non-positive rows. Six decimals
  preserves every value as positive, and nothing in the source is below 5e-7.
- **DEV-4 -- the check normalises whitespace before matching prose.** The
  labelling checks originally did a plain substring match against a hard-wrapped
  README, so `not a price forecast` failed purely because the phrase spanned a
  line break. That was a defect in the check, not the document: a documentation
  assertion must not depend on where a paragraph wraps.

## Risks and follow-ups

- **The denominator gap is a known, accepted approximation** (D-1). If a reviewer
  reads the output's stated basis note and disagrees, the fix is the follow-up
  below, not a quiet change here.
- **Follow-up in `ag-commodity-bundles`:** carry the national trend production
  (area harvested times trend yield) in node 3's output metadata, the same way
  `export_exposure` was added for this model, and switch node 4's denominator to
  it. That closes a gap that has run -3.4% to +6.7% since 2015.
- **Follow-up, this repo:** the soybean and acreage channel as its own brief.
  The README section written in step 12 is its specification.
- **The destination table lags the balance sheet by one marketing year.** ERS
  Table 22 ends at the latest complete year while Table 4 carries a WASDE
  projection. The output must never present the two as the same year (D-6).
- **The ERS URL moved once already**, in January 2026, and node 3's build script
  says so. If `build_destinations.py` cannot fetch, that is a build-time failure
  to report, never a run-time one.
- **No historical episode validates this model**, for the reason that is its own
  headline caveat. Do not let a reviewer's reasonable request for one turn into a
  fitted number; the answer is the measured reallocation evidence in the README.
- **Repository state at planning time:** working tree clean apart from untracked
  `docs/`. `run` will branch `feat/0001-corn-trade-policy`. This planning session
  is itself in the worktree `corn-trade-policy-brief-92c6ef` on branch
  `claude/corn-trade-policy-brief-92c6ef`; `run` must resolve that before
  branching rather than committing the brief twice.
