# Corn trade policy

## Outcome

`corn-trade-policy/` is a self-contained Model Home model that takes node 3
(`ag-commodity-bundles/corn-price/`) `corn_price_impact` document and a **stated
export-demand scenario** -- bushels of US corn not sold -- and returns the corn
price impact that scenario implies, reported **beside** node 3's weather-driven
impact rather than folded into it. Each component carries its own interval, and
the combined figure is composed the way the transmission is specified rather
than by adding two percentages.

Pasting the subfolder's GitHub URL into `http://localhost:5173/models/new/repo`
creates a working model, and Model Home composes it after `corn-price` in a
flow, with the scenario wired as an `inline` literal the flow author supplies.

This is node 4 of a climate -> agriculture -> finance flow: forecast weather ->
corn crop model -> corn price impact -> trade-policy impact. Node 3's output is
node 4's input, unchanged: they are semantic peers. Node 4 consumes the weather
result; it never re-derives it, never refits node 3's transmission, never
re-sources the balance sheet and never redefines the region set.

Node 4 answers exactly one question: **what does this export-demand scenario
imply for the corn price, against a baseline in which it does not happen?** It
does not answer what happens next, it does not predict whether any tariff will
be imposed, extended or lifted, and the scenario is an input rather than an
output. Node 4's number looks even more tradeable than node 3's and is even less
of a trade: it is arithmetic on an assumption the user supplied.

## Scope

### In scope

**The `corn-trade-policy/` bundle:** `Modelfile.toml`, `Dockerfile`,
`runner.py`, two sample inputs (a **real node 3 `corn_price_impact`** and a
scenario literal), the committed destination-context table with its build script
and `*.meta.json`, and a validation check run outside the image.

**Input 1 -- node 3's document, unchanged.** The input schema *is* node 3's
`corn_price_impact` output schema, bound on its required-key set
`["generated_at", "metadata", "national", "regions", "assumptions"]`. Verify the
binding against the platform's `check_schema_compatibility` before building, and
verify that node 3's *other* output and node 2's snapshot, both
`["metadata", "columns", "rows"]`, are refused.

**Input 2 -- the scenario, a second declared input.** Bushels of export demand
removed, plus an optional free-text label naming the scenario for provenance.
`required = []` with the defaults in the runner, so an absent, empty or zero
scenario produces a trade component of exactly zero and the bundle still runs
standalone.

**The bushels-to-shock conversion.** The single most consequential step in the
model and the place a plausible-looking wrong number is easiest to produce. The
scenario arrives in bushels; the committed coefficient is fitted on a
*proportional* deviation of the national crop from trend, as a fraction. The
denominator that makes those two commensurate is a decision the plan must take
explicitly, from the candidates measured in **General guidance** below, and the
chosen basis must appear in the output document.

**The trade price impact.** Apply node 3's committed transmission coefficient,
read from node 3's own output metadata rather than copied, to the equivalent
shock, with the sign convention stated: bushels **not sold** are a reduction in
demand and enter with the sign of an equivalent surplus, so a positive scenario
produces a negative price impact. The interval comes from node 3's committed
bootstrap bounds on that coefficient, applied the same way node 3 applies them.

**The symmetry assumption, declared.** Node 3's coefficient is fitted on
supply-side weather shocks. Reusing it for a demand shock assumes a symmetry the
fit does not demonstrate, defensible because post-harvest supply is close to
vertical, and it is an assumption the output states in its own words rather than
one buried in a runner.

**The combined impact.** Weather and trade reported separately, each with its
interval, and a combined figure composed as the transmission's functional form
requires rather than by adding the two percentages.

**The weather component, reproduced and not recomputed.** Node 4 copies node 3's
`price_impact_pct` and its bounds through unchanged, and says so.

**A committed destination-context table.** US corn exports by destination and
marketing year, from `Table 22--U.S. corn and sorghum exports by selected
destinations` in the **same keyless ERS Feed Grains file, at the same vintage**,
that node 3 already builds `price_history.csv` from. It is **context only**: it
enters no arithmetic. Its job is to let a reader see who actually buys US corn
and how much, so a scenario can be stated against measured purchases rather than
against an impression, and to let the runner refuse an incoherent scenario.

**Output -- `corn_trade_policy_impact`.** One JSON document, **national only**,
with no region array and no `region_key` join. Its required-key set includes a
`scenario` key, which keeps it unambiguous against node 3's own output for any
future node 5.

**Labelling, in all three places.** The Modelfile `not_for`, the README and the
output document each state that this is not a price forecast, not a trading
signal, not investment advice **and not a political forecast**, that the
scenario is the user's assumption rather than the model's finding, and that
trade reallocates so a headline tariff is not a bushel loss.

**A README section on the soybean channel**: what it is, why the evidence says it
is probably the larger channel for a China tariff, and how it would be
approached if it were built. Documented, not built.

**A validation check** run outside the image, proving the modelling claims.
Note that the usual promise -- a known historical episode reproducing a known
price move -- is **not available here**, for the measured reason recorded under
Constraints. The check proves the other claims instead, enumerated in AC-15.

### Out of scope

- **Nodes 1 to 3 and the flow definition**, which lives in the platform: no
  Flowfile.
- **Re-deriving anything node 3 produces**: the yield shock, the production
  shock, the per-region contributions, the reference price, the balance sheet or
  the transmission fit. Node 4 fits nothing.
- **The soybean price and the acreage substitution that follows it.** Named in
  the README and in the output's not-captured list, and left for a later brief.
- **Any tariff schedule, tariff rate, or conversion from a tariff rate to
  bushels.** Nothing in this bundle knows what a tariff is. The scenario is
  bushels, and the step before it belongs to whoever states the scenario.
- **Any forecast of policy.** No bundle here predicts whether a measure will be
  imposed, extended or lifted.
- **Per-region allocation of the trade impact**, and any region join.
- **A demand-side transmission fit.** Decided against; see General guidance.
- **FAS GATS, FAS Export Sales Reporting and Census USA Trade Online.** Ruled
  out before anything was downloaded: the ERS file node 3 already uses carries
  the destination detail this bundle needs. No new source, no API key.
- A live or market reference price, and a within-season futures transmission.
  Both remain node 3's follow-ups.

## Acceptance criteria

- **AC-1** -- `corn-trade-policy/` contains `Modelfile.toml`, `Dockerfile`,
  `runner.py`, both sample inputs, the committed destination table with its build
  script and `*.meta.json`, a validation check and a `README.md`, matching the
  layout and conventions of `ag-commodity-bundles/corn-price/`.
- **AC-2** -- Input 1 declares
  `required = ["generated_at", "metadata", "national", "regions", "assumptions"]`
  and `check_schema_compatibility` confirms it binds node 3's `corn_price_impact`
  and is **refused** by both `corn_price_regions` and node 2's
  `corn_yield_snapshot`. Demonstrated by running the platform check, not asserted.
- **AC-3** -- Input 2 is a separately declared scenario input with
  `required = []`. An absent, empty, null or zero scenario produces a trade
  component of **exactly zero**, a combined impact equal to node 3's weather
  impact to node 3's own rounding, and a run that still succeeds.
- **AC-4** -- The sample node 3 document is a **real `corn_price_impact`**, and
  `python corn-trade-policy/runner.py <node3.json> <scenario.json>` runs end to
  end and writes the declared output.
- **AC-5** -- `docker build` from the bundle folder succeeds and
  `docker run --network none` reproduces the local run's output apart from
  `generated_at`. Build scripts and the check stay out of the image.
- **AC-6** -- The bushels-to-shock denominator is the basis chosen in the plan,
  it is **named in the output document** with its value and its source, and the
  check asserts the runner used it. Node 3's `us_trend_production_bu` is
  **not** used unless the plan's decision explicitly selects it on the evidence,
  because it is built on 2022 Census acreage and sits 8.9% below the basis the
  coefficient's regressor is normalised against, which is 9.7% above it.
- **AC-7** -- Node 3's `us_trend_production_bu` is a declared but **optional**
  property of `corn_price_impact`. Any node 3 field the runner reads that is not
  in node 3's required-key set is checked for presence and the run **fails
  loudly** naming the missing field, rather than defaulting.
- **AC-8** -- Sign convention: a positive `bushels_not_sold` produces a negative
  trade price impact, and a negative one (extra sales) a positive impact. Both
  directions are asserted in the check.
- **AC-9** -- Exports are never added to total use. The check asserts the
  denominator is not any quantity containing exports twice, and the output
  states in words that exports are a component of use, so a lost-export scenario
  reduces the denominator as well as the numerator.
- **AC-10** -- The combined impact is composed as the transmission's functional
  form requires, not by adding the two component percentages. The check asserts
  the combined figure differs from that sum and matches a hand-worked case to
  full precision.
- **AC-11** -- No transmission constant is hard-coded anywhere in the bundle.
  The coefficient, its bootstrap interval, the fit statistics and the sample
  period are all read from node 3's output metadata, echoed into node 4's output
  metadata, and the run **fails loudly** if node 3's document carries no
  transmission block. The check asserts a modified coefficient in the input
  changes the result.
- **AC-12** -- Every headline number ships with its `_low` and `_high` in the
  same object, ordered low <= central <= high, for the weather component, the
  trade component and the combined figure alike. No figure appears without its
  interval, and the output states that the interval expresses uncertainty about
  the **transmission**, reused from a supply-side fit, and not about what the
  corn price will do.
- **AC-13** -- The symmetry assumption -- that a coefficient fitted on
  supply-side weather shocks is being applied to a demand shock -- appears in the
  output document, the README and the Modelfile `not_for`. All three, not one of
  the three.
- **AC-14** -- The destination table is built **only** by its committed build
  script from the ERS Feed Grains file, ships a `*.meta.json` recording the
  source URL, the server-side `last-modified`, the period covered and the build
  date, and the runner carries that vintage into its output metadata. The build
  script **fails loudly** rather than writing a partial row, and does not
  silently include the 1989 and 1990 marketing years, whose reported world totals
  of 637 and 392 thousand metric tons against roughly 50,000 in later years show
  the series is not complete before 1991. The table enters no arithmetic.
- **AC-15** -- A committed check, run outside the image, proves the modelling
  claims. No historical trade episode is available to reproduce a price move
  (see Constraints), so the check proves instead: the hand-worked
  bushels -> shock -> price chain to full precision; both signs; the zero-scenario
  identity of AC-3; the log-space composition of AC-10; the interval ordering of
  AC-12; the denominator of AC-6; that no exports figure is double-counted; that
  a scenario removing more bushels than the latest complete marketing year's
  total US corn exports **fails loudly**, naming that figure; and that the
  destination table ties out to node 3's own `exports_mil_bu`.
- **AC-16** -- The destination table's world total for the latest complete
  marketing year, converted to bushels, equals node 3's committed
  `exports_mil_bu` for that year to the committed precision. Same file, same
  vintage, same marketing-year convention, demonstrated rather than assumed.
- **AC-17** -- The output reports the scenario as a share of the latest complete
  marketing year's total US corn exports and as a share of total use, beside the
  destination table's recent purchases, so a reader can see immediately whether
  the scenario is large or small against what is actually bought.
- **AC-18** -- The Modelfile `not_for`, the README and the output document each
  state that the output is not a price forecast, not a trading signal, not
  investment advice and **not a political forecast**; that the scenario is an
  input the user states rather than something the model predicts; and that trade
  reallocates, so a headline tariff is not a bushel loss and the
  tariff-to-bushels step belongs to whoever states the scenario.
- **AC-19** -- `Modelfile.toml` validates with no annotation warnings,
  `validity_domain` within 600 characters, `provenance` within 400, `not_for`
  kept under 600 by the same caution `corn-price` uses, and every key in a
  `required` array has a declared `properties.<key>.type`. The output's
  required-key set includes `scenario` and is therefore distinguishable from node
  3's.
- **AC-20** -- The README documents: the two inputs and how the scenario is
  wired as an inline literal in a flow; the bushels-to-shock denominator and why
  that basis; the sign convention; the reused coefficient and the symmetry
  assumption; the log-space composition; the destination table's source, vintage
  and context-only role; the determinism and offline semantics; the measured
  reallocation evidence; what the model is not; and **the soybean channel** --
  what it is, why the evidence says it is probably the larger channel for a China
  tariff, and how it would be approached if built.

## Constraints and dependencies

- **Node 3's `metadata.export_exposure` is the balance-sheet source, and node 4
  never re-sources it.** It was merged to `ag-commodity-bundles` `main` as
  `896f6ca`, "Merge pull request #2: corn-price export exposure (brief 0002)",
  and added specifically so node 4 would not pick a different vintage from node
  3's. Take the field names from the merged `corn-price/Modelfile.toml`,
  `runner.py` and `price_history.meta.json`, not from the branch and not from
  this brief. A local checkout that predates that merge will read the wrong
  contract, so confirm the working copy is current before planning.
- **The denominator is the model's biggest arithmetic risk, and node 3 does not
  currently emit the right figure.** Node 3's transmission regressor is the
  national yield's deviation from an ERS trend, so the commensurate bushel base
  is national trend production on the ERS basis, area harvested times trend
  yield. Node 3's output carries neither. Measured, for the committed 2026 row:
  ERS trend production 16,344 mil bu; total use 16,180 mil bu, recoverable from
  `metadata.export_exposure` as exports over export share; node 3's
  `us_trend_production_bu` 14,894 mil bu, which is 8.9% below the ERS basis
  because it is built from 2022 Census acreage in a year with 88.5 mil acres. On
  a 300 mil bu scenario those three bases give -1.426%, -1.440% and -1.564%. The
  gap between
  total use and ERS trend production is not stable either: it runs from -3.4% to
  +6.7% over 2015-2026. See D-1 in General guidance.
- **Percent versus fraction, and bushels versus mil bu.** Node 3 emits
  `us_trend_production_bu` and `us_production_shock_bu` in **bushels**, while the
  balance-sheet quantities in `metadata.export_exposure` are in **mil bu**. Both
  appear in the same arithmetic. Convert at one boundary, name every variable for
  its unit, and comment every conversion with both units and the factor. The
  destination table is published in 1,000 metric tons and needs the same
  treatment.
- **The transmission is applied in log space.** Node 3 computes
  `(exp(b0 * d) - 1) * 100`. Two shocks therefore combine inside the exponential,
  and the combined impact is **not** the sum of the two component percentages.
- **Exports are a component of total use, never an addition to it.** A
  lost-export scenario reduces the denominator as well as the numerator. This is
  the easiest arithmetic error available in this repo and node 3's
  `price_history.meta.json` carries a definition saying so.
- **The coefficient was fitted on supply shocks.** `b0 = -0.7826`, bootstrap 95%
  `[-1.269, -0.393]`, n = 50, R-squared 0.329, sample 1976-2025, on a
  marketing-year average cash price. Its own `not_captured` list states that
  export demand shocks and trade policy are outside it. Reusing it is a choice
  with a cost, taken deliberately, and the cost is stated in the output.
- **No historical trade episode validates this model, and the reason is the
  model's own headline caveat.** Measured, from node 3's committed table and the
  ERS destination table: China went from 2,991 to 33 thousand metric tons of US
  corn between marketing years 2023 and 2024, while **total US corn exports rose**
  from 57.3 to 73.0 million tonnes; and across the 1980 Soviet embargo US corn
  exports were 2,401 mil bu in 1979 against 2,391 in 1980, essentially flat, with
  that year's price move confounded by a -7.2% yield deviation. Both candidate
  episodes show an aggregate bushel loss of roughly zero because trade
  reallocated. The validation check must therefore prove the arithmetic and the
  labelling rather than a reproduced price move, and the README must say why.
- **The destination shares are measured, not recalled.** China's share of US corn
  exports by marketing year, from ERS Table 22: 0.5% (2018), 4.6% (2019), 30.8%
  (2020), 23.3% (2021), 18.3% (2022), 5.2% (2023), 0.04% (2024). Mexico runs 22%
  to 40% throughout and is 35.1% in 2024; Japan 16% to 25%. China's purchases are
  episodic; Mexico and Japan are the steady buyers. Any statement the bundle
  makes about destinations must come from the committed table, not from these
  figures restated.
- **The destination table lags the balance sheet by one marketing year.** ERS
  Table 22 ends at the latest complete marketing year, while Table 4 carries a
  WASDE projection row beyond it. The output must not present the two as the same
  year.
- **Determinism.** No network calls at run time. The bundle is a pure function of
  its two input documents plus the committed destination table, whose vintage
  ships in the output metadata.
- **A schedule re-sends a fixed input**, so a scheduled node 4 run re-prices the
  same stored scenario every day. Anything that should change per run, such as
  "today", is defaulted in the runner. The scenario itself is meant to be fixed;
  the output must date itself clearly enough that a stale scenario is visible.
- **Every key in a Modelfile `required` array needs a declared
  `properties.<key>.type`**; `validity_domain` is capped at 600 characters and
  `provenance` at 400. The schema format has **no nullable type**, so a field
  that can be empty must not appear in any `required` list.
- **Licence** MIT.

Repo-wide conventions -- mirroring `corn-price/`, `corn-yield/`,
`crop-weather/` and `bond/`, the Modelfile and runner contracts, the verified
platform facts, the upstream contract, unit discipline, modelling honesty,
determinism, region identity and the data sources -- live in
[`CLAUDE.md`](../../CLAUDE.md) and are not restated here.

## General guidance

- **The four open design questions were answered by John on 2026-09-20**, after
  the underlying claims were verified against the ERS data rather than recalled.
  Record them as decisions in the plan:

  1. **Scope: corn only, with destination context.** The arithmetic is corn-only
     and national. ERS Table 22 ships as a committed context table because it is
     free -- the same keyless file, the same vintage, one more read in one more
     build script -- and because it is what stops a user stating a scenario that
     the purchase record contradicts. The soybean and acreage channel is
     **documented in the README and not built**.
  2. **Transmission: reuse node 3's coefficient**, with the symmetry assumption
     declared in the output, the README and `not_for`. A separate demand-side fit
     was rejected: exports are endogenous to the price within the marketing year,
     so it would need an instrument, and the relevant episodes are about three in
     fifty years, which the repo's fixed |t| >= 2.0 rule would reject anyway.
  3. **Scenario: bushels not sold, national**, plus an optional free-text label.
     The tariff-to-bushels step stays with whoever states the scenario. The two
     measured episodes above are the argument.
  4. **Shape: national only**, no region join, no region array. Export demand is
     a national quantity and there is no defensible way to attribute a lost cargo
     to one state rather than another.

- **D-1, and the one question the plan must settle before coding: which
  denominator converts bushels into the coefficient's shock.** The criterion is
  fixed -- it must be the base the regressor is normalised by, which is national
  trend production on the ERS basis -- but node 3 emits neither that figure nor
  the area harvested to compute it. Three routes, and the plan picks one with
  reasons:
  (a) ask `ag-commodity-bundles` to carry national trend production in node 3's
  output metadata, exactly the precedent `export_exposure` set, and depend on it;
  (b) use total use, recovered from `metadata.export_exposure` as exports over
  export share, and document the residual basis gap, which is -1.0% on the
  committed row but has run from -3.4% to +6.7% since 2015;
  (c) commit node 4's own copy of the ERS national area and trend yield, which
  re-sources what node 3 already owns and risks a different vintage from node
  3's -- the thing this flow is built to avoid.
  Route (a) is cleanest and route (b) is the obvious interim. Whichever is
  chosen, the basis, its value and its source appear in the output document, and
  `us_trend_production_bu` is not silently substituted for it.

- **Read node 3 before writing the plan**, in this order:
  `ag-commodity-bundles/docs/plans/0001-corn-price.md`, which records where that
  design broke and why; `docs/features/0002-export-exposure.md`, whose closing
  section is the original reasoning for separating node 4; and
  `corn-price/Modelfile.toml` on the merged branch, for field names and
  semantics. Take them from the source, never from a README and never from this
  brief.

- **Verify by running, not by reading.** Node 3's own two worst review findings
  were only visible when something was actually executed. Run node 3 on its
  committed sample to produce node 4's sample input; run the platform's
  `check_schema_compatibility` for AC-2; run the container with `--network none`.

- **The destination table is cheap because the file is already there.**
  `build_price_history.py` downloads
  `https://www.ers.usda.gov/media/5766/feed-grains-yearbook-tables-all-years.csv`
  and caches it. Inside it, `table_name` =
  `Table 22--U.S. corn and sorghum exports by selected destinations`, with
  `commodity` = `Corn`, `frequency` = `Annual`, `timeperiod` =
  `Marketing year Sep-Aug`, `unit` = `1,000 metric tons`, 108 destinations plus a
  `World total` row, years 1989-2024 of which 1991 onward are usable. Match the
  attribute and table strings from the file rather than guessing them, the way
  `read_series` already does, and let a mismatch fail loudly.

- **What the README's soybean section should say.** The direct corn channel is
  the one this bundle prices, and the data says it is probably the smaller one
  for a China tariff: China takes roughly half of US soybean exports -- about
  51% in 2024 and an average near 47% across 2018-2024, against about 60% before
  2018, figures the plan must confirm from ERS rather than restate from here --
  while taking close to nothing of US corn in most years, as the committed
  destination table shows. The indirect channel runs through acreage -- a soybean price fall makes corn
  relatively more attractive, acres shift to corn the following spring, and the
  larger corn crop pushes the corn price down a year later. Building it would
  need a soybean balance sheet from the ERS Oil Crops Yearbook (a separate
  keyless CSV whose location and format changed in March 2026 and which must be
  verified, not assumed), a soybean price transmission fitted the way node 3 fits
  its own, a corn acreage response to the expected new-crop corn-to-soybean price
  ratio, and a one-year lag so the corn effect lands in the following marketing
  year. That is two more fits and a second balance sheet, which is a separate
  model and a separate brief, not a term in this one. Say that plainly, and say
  that until it exists the bundle prices only the direct channel.

- **Keep it boring.** Node 3 ships with no pip layer at all and this model is
  one division, one exponential and a table lookup. Expect the same here.

- Before you write the plan, ask any questions you need to in order to best
  implement the brief.
