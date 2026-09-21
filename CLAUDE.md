# ag-trade-bundles

Standalone Model Home **model bundles** for agricultural trade: the layer that
turns a market quantity into the consequence of a trade-policy or export-demand
shock. Each bundle is a self-contained folder with everything Model Home needs
to run one model: a `Modelfile.toml`, a `Dockerfile`, a `runner.py`, and sample
input(s).

This repo holds only the Model Home packaging layer plus the data tables and the
economics that sit on top of them. Nothing upstream is vendored.

```
ag-trade-bundles/
  CLAUDE.md                 <- you are here
  README.md
  LICENSE                   (MIT)
  .claude/skills/feat/      <- vendored feat skill (brief -> plan -> PR workflow)
  docs/features/            <- feature briefs (NNNN-name.md)
  docs/plans/               <- implementation plans, one per brief
  <bundle>/                 <- one self-contained model per folder
```

This is the trade end of a climate -> agriculture -> finance flow:

| Node | Repo | Job |
|---|---|---|
| 1 | `agromet-bundles/crop-weather/` | the daily weather series, in PCSE's own variables and units |
| 2 | `wofost-bundles/corn-yield/` | phenology, projected yield, weather-driven yield anomaly per state |
| 3 | `ag-commodity-bundles/corn-price/` | the national production shock and the price impact it implies |
| **4** | **`ag-trade-bundles/corn-trade-policy/`** | **the price impact a stated export-demand shock implies, beside node 3's** |

Node 3's output is node 4's input, unchanged: they are semantic peers, composed
in a Model Home Flow. Node 4 never re-derives anything node 3 produces, never
refits node 3's transmission, and never redefines the region set.

---

## The templates: `corn-price/`, `corn-yield/`, `crop-weather/`, `bond/`

[`corn-price/`](https://github.com/modelhome/ag-commodity-bundles),
[`corn-yield/`](https://github.com/modelhome/wofost-bundles),
[`crop-weather/`](https://github.com/modelhome/agromet-bundles) and
[`bond/`](https://github.com/modelhome/QuantLib-bundles) are the authoritative
templates. Read them before starting a bundle and mirror them. `bond` is the
minimal shape; `crop-weather` is the shape for a bundle with a committed table
built by a one-time script; **`corn-price` is the immediate upstream and the
closest model for this repo's conventions** -- read its `CLAUDE.md`, its README
and `docs/plans/0001-corn-price.md` before writing anything here. Consistency
with them matters more than any local preference:

- **`Modelfile.toml` keys.** `name`, `description`, `run`, `image`, `args`,
  `[resources]`, `[[inputs]]` with a documented `[inputs.schema]` (every
  property has a plain-language `description`; the schema's `default` is what
  the platform offers as the "Example to paste", so it must stay runnable), and
  `[[outputs]]` with `[outputs.schema]`. Add the annotation fields Model Home
  validates: `determinism`, `expected_runtime`, `validity_domain`, `not_for`,
  `provenance`, and per-property `unit`. Rationale the schema cannot express
  goes in TOML comments beside it. The platform validator caps
  `validity_domain` at **600 characters** and `provenance` at **400**, and
  rejects any key listed in a `required` array that has no declared
  `properties.<key>.type`. `not_for` has no documented cap; `corn-price` keeps
  it under 600 anyway rather than gamble on the validator.
- **Runner I/O contract.** Input JSON file path(s) arrive as positional args.
  The result JSON goes to **stdout** and nothing else does; logs go to stderr.
  The Modelfile's `run` redirects stdout to `run/<output>.output.json`. Further
  outputs are passed as `{output:NAME}` args.
- **`required = []` and defaults in the runner.** A present-but-empty value
  (`""` or `null`) falls back the same way a missing key does, so the model runs
  standalone or composed.
- **Dockerfile.** `python:3.12-slim`, `WORKDIR /app`, exact `==` pins installed
  in one `pip install --no-cache-dir` layer, `COPY` paths relative to the bundle
  folder, `ENTRYPOINT ["python", "runner.py"]`, and a `CMD` naming the bundled
  sample input so a bare `docker run` works.
- **Stdlib over dependencies.** `corn-price` ships with no pip layer at all.
  Expect the same here until something genuinely needs otherwise.

## Model Home platform facts (verified against the platform code)

- **Build context is the bundle subfolder.** Adding a model from
  `github.com/modelhome/ag-trade-bundles/tree/main/<bundle>` promotes that
  folder to the build-context root, exactly like `cd <bundle> && docker build .`.
  Never use repo-relative `COPY <bundle>/...` paths; the on-platform build fails.
  Note that a `.dockerignore` at the repo root does **not** apply when the
  context is the subfolder.
- **Every output is a JSON file.** The platform collects only
  `/run/<name>.output.json` for each declared `[[outputs]]` name and parses it
  with `json.loads`. Any other file a runner writes (a CSV, a PNG) is discarded
  on-platform.
- **A schedule re-sends a fixed input.** A scheduled run passes the same stored
  input every time, so anything that should change per run (such as "today")
  must be defaulted inside the runner, not baked into the schedule's input.
- **Flow steps connect by output shape, not by name**, and "shape" has an exact
  meaning: `check_schema_compatibility` in
  `orchestration/modelfile/validation.py` requires the downstream input's
  `required` keys to be a **subset** of the upstream output's `required` keys,
  then recurses into `properties` and array `items`, comparing declared `type`s
  by equality with one widening (a `number` input accepts an `integer` output).
  A property with no declared `type` is unconstrained and is not compared.
- **A step's inputs need not all come from the step before it.** `flow_service`
  resolves each input independently: to any *earlier* step's output
  (`source_step_index` / `source_artifact`), to an `inline` literal JSON
  document, or to an `http(s)` `url`. Auto-matching by name only happens against
  the immediately previous step; anything else is wired explicitly. **This is
  how a scenario input reaches node 4** -- as an `inline` literal the flow
  author supplies, not as something the model fetches.
- **The Modelfile schema format has no nullable type.** `schema_type` requires a
  plain string, so `["number", "null"]` is not expressible. A field that can be
  empty therefore must not appear in any `required` list -- and if a required
  field can go null, fix the model rather than the declaration.

## The upstream contract: node 3's `corn_price_impact`

Node 4's input schema **is** node 3's output schema. Take the field list from
`ag-commodity-bundles/corn-price/Modelfile.toml`, not from memory. What matters:

- The document's required keys are `["generated_at", "metadata", "national",
  "regions", "assumptions"]`. **Bind on that set.** Node 3's *other* output,
  `corn_price_regions`, has required keys `["metadata", "columns", "rows"]`,
  which also matches node 2's `corn_yield_snapshot` -- declaring that set would
  be ambiguous and would bind the wrong thing.
- `national` carries the weather-driven `price_impact_pct` with its `_low` and
  `_high`, the `us_yield_shock_pct`, `us_production_shock_bu`, the
  `reference_price_usd_bu` and `coverage_share_of_us_production`.
- `metadata.export_exposure` carries `exports_mil_bu` and `export_share_of_use`
  for both the current (WASDE projection) and latest complete marketing year,
  with the ERS vintage behind them. **This exists specifically so node 4 does
  not re-source the balance sheet** and cannot silently pick a different
  vintage from node 3's. It was added by brief 0002 in that repo.
- **Exports are a component of total use, not an addition to it.** A lost-export
  scenario reduces the denominator as well as the numerator. Adding exports to
  total use double-counts them. This is the easiest arithmetic error available
  in this repo.
- **Node 3's transmission is fitted on supply-side weather shocks**,
  `dlog_price = a + b0*d + c*d[t-1]`, 1976-2025, n=50, b0 = -0.7826
  (bootstrap 95% [-1.269, -0.393], R^2 0.329). Its `not_captured` list states
  that export demand shocks and trade policy are outside it. Reusing b0 for a
  demand shock is a *choice with a cost*, not a free move -- see below.

## Conventions for every bundle

- **Read the upstream Modelfile and the upstream plan before coding.** Take
  field names, units and semantics from the source, not from a README or from
  this file.
- **Unit slips are the classic bug.** Convert at one boundary and name variables
  with their unit (`exports_mil_bu`, `price_usd_bu`). Every conversion gets a
  comment naming both units and the factor.
- **Percent versus fraction is a standing trap.** Node 3 emits percentages;
  elasticity arithmetic is natural in fractions. Pick one internally, name the
  variables for it, and convert once.
- **Commit a validation check** per bundle, run outside the image, that proves
  the *modelling claims* rather than the plumbing: that a known historical
  episode reproduces a known move within the stated interval, that the sign is
  right, that a malformed scenario fails loudly.
- **Pin everything** in the Dockerfile.
- **Parameters, not constants.** Economic choices are declared, annotated inputs
  with sensible defaults, and they appear in the output metadata.
- **No emojis** in source files.

### Modelling honesty

This repo publishes numbers that look tradeable, about a subject people hold
political views on. Nothing else here matters more than getting the labelling
right. Everything in `ag-commodity-bundles/CLAUDE.md` under this heading applies
here unchanged, plus three that are specific to trade:

- **It is an implied impact under a scenario the user states.** Never a
  forecast, never advice.
- **This repo does not forecast politics.** No bundle here predicts whether a
  tariff will be imposed, extended or lifted, and none should read as though it
  does. The scenario is an input, not an output.
- **The tariff-to-bushels step is the user's assumption, not the model's.**
  Trade reallocates: in 2018-19 soybean flows largely rerouted rather than
  disappeared, so the realised bushel loss was far below the headline tariff.
  A model that converts a tariff rate into lost sales by itself is claiming
  knowledge it does not have. Take **bushels not sold** as the input and say
  loudly that the step before it belongs to whoever states the scenario.

### Determinism

Like `corn-price` and `corn-yield`, bundles here make **no network calls at run
time**: they are pure functions of their inputs plus committed tables. Any
committed table is produced only by a one-time committed build script, ships a
`*.meta.json` recording the source URL, the file's server-side `last-modified`,
the period covered and the build date, and the runner puts that vintage in its
output metadata.

Two things learned the hard way next door, worth not relearning:

- A committed table is **only ever written by its build script**, never edited
  by hand, and the build script **fails loudly** rather than writing a blank
  cell when a series has a gap.
- A seeded build is reproducible run-to-run on one host but **not bit-identical
  across hosts**: `corn-price`'s refit moved a coefficient by one unit in the
  last place purely from floating-point differences. Don't mistake that for a
  data revision, and don't chase it.

### Region identity

If a bundle here joins on region, the `region_key` originates in
`agromet-bundles/crop-weather/regions.csv` -- `ia, il, mn, ne, in, sd, oh, wi,
ks, mo` -- and propagates unchanged. Never redefine the key, and fail loudly on
one with no matching row. Note that node 4 may well be **national only**, in
which case it has no region join at all; decide that in the brief rather than
inheriting a per-region shape out of habit.

### Data sources

**Unverified as of repo creation.** Node 3's sources -- the USDA NASS bulk
exports and the USDA ERS Feed Grains Yearbook Tables -- are keyless and proven,
and the ERS table already carries national corn exports. What node 4 may
additionally need, *if* it goes beyond a national bushel scenario, is
destination-level trade data. Candidates to **verify before relying on**, in
the plan and not from memory:

- USDA FAS **GATS** (Global Agricultural Trade System) -- destination-level
  agricultural trade.
- USDA FAS **Export Sales Reporting** -- weekly commitments by destination.
  Believed to need an API key; confirm.
- US Census **USA Trade Online** -- the underlying trade statistics.

Check what each actually requires, whether a keyless bulk form exists, and
whether the model needs it at all. A national lost-bushels scenario may need no
new source whatsoever, which is the cheapest correct answer and should be ruled
out before anything is downloaded.

## How features are built: `feat`

Features are developed from versioned briefs with the vendored
[`feat`](./.claude/skills/feat/SKILL.md) skill, so the brief, the plan and the
implementation land together in one pull request:

1. `/feat create <name>` scaffolds `docs/features/NNNN-<name>.md`. Hand-written
   briefs in the same template are fine.
2. `/feat plan <name>` writes `docs/plans/NNNN-<name>.md` and stops. John reviews
   and revises the plan before anything is built.
3. `/feat run <name>` implements the approved plan on `feat/NNNN-<name>` and
   stops at the pull request. It never merges, releases or deploys.

Repo-wide conventions live in this file; briefs reference them rather than
restating them.

## The `corn-trade-policy/` bundle

**US Corn Trade Policy Impact.** Takes node 3's `corn_price_impact` document and
a stated export-demand scenario -- million bushels of US corn not sold -- and
returns the price impact that scenario implies, reported beside node 3's
weather-driven impact, each component with its own interval and a combined
figure composed inside the transmission rather than by adding percentages. Built
2026-09-20 from brief `docs/features/0001-corn-trade-policy.md`; plan with every
decision and its reasoning: `docs/plans/0001-corn-trade-policy.md`. User-facing
documentation: [`corn-trade-policy/README.md`](./corn-trade-policy/README.md).

```
corn-trade-policy/
  Modelfile.toml            two inputs (node 3's document, a scenario), one JSON output
  Dockerfile                python:3.12-slim, no pip layer at all
  runner.py                 the model
  destinations.csv          US corn exports by destination, 1992-2024 (2,312 rows)
  destinations.meta.json    provenance, the tie-out and the excluded years
  build_destinations.py     one-time destination-table build (not in the image)
  check_trade_policy.py     validation, needs Python 3.11+ (not in the image)
  sample_input.json         a real node 3 corn_price_impact
  sample_scenario.json      the illustrative 300 mil bu scenario
  README.md
```

### Why node 4 is a separate model rather than a term inside node 3

Three reasons, in descending order of force:

1. **Node 3's fit cannot carry it.** Fifty annual observations and a selection
   rule fixed at |t| >= 2.0. The relevant trade shocks are roughly three
   episodes -- the 1980 Soviet embargo, the 2018-19 Chinese retaliation, 2025.
   A tariff term would fail that rule, and the repo's posture is to report such
   a failure as a finding rather than ship the term anyway.
2. **It would break node 3's identity.** Node 3's contract is one upstream
   document plus committed tables. A tariff is not a function of weather, it
   changes intra-season on announcement, and a committed tariff table would have
   a vintage measured in weeks.
3. **The time base is wrong.** Node 3's transmission is fitted on a
   marketing-year average cash price. Weather accumulates over a season; a
   tariff is a discrete jump that futures price within hours.

### Design notes

- **The model fits nothing, and hard-codes no coefficient.** The transmission,
  its bootstrap interval, the fit statistics, the reference price and the export
  exposure are all read from node 3's output document. An upstream refit
  therefore propagates with no change here, and the check asserts it: a doubled
  coefficient in the input must move the result, and `runner.py` must not
  contain the coefficient's digits.
- **The denominator is the model's biggest arithmetic risk, and the obvious
  field is the wrong one.** Node 3's coefficient is fitted on the national
  yield's deviation from an ERS trend, whose commensurate bushel base is area
  harvested times trend yield: 16,344 mil bu for marketing year 2026. Node 3
  emits neither that figure nor the area to compute it. The model divides by
  **total use**, 16,180 mil bu, recovered from `metadata.export_exposure` as
  exports over export share. Node 3's `us_trend_production_bu` (14,894 mil bu) is
  **deliberately not used**: it is built on 2022 Census acreage and sits 8.9%
  below the fitted basis, which would inflate a 300 mil bu scenario from -1.44%
  to -1.56%. The remaining gap is about 1% for 2026 and has run -3.4% to +6.7%
  since 2015; closing it is an upstream follow-up, not a change here.
- **The two effects compose, they do not add.** The transmission is log-linear,
  so the combined impact is `exp(b0 * (d_weather + d_trade)) - 1`, not the sum of
  the two percentages. Both components share one coefficient, so their intervals
  are perfectly correlated and the combined interval comes from applying the
  bounds to the combined shock.
- **The destination table's window is derived, not declared.** A marketing year
  is committed only when ERS Table 22's world total ties out to Table 4's exports
  within 1e-4. 1989, 1990 and 1991 fail by 98.9%, 99.1% and 34.3% and are
  excluded with their errors recorded; 1992-2024 tie out to 2.1e-06. A
  hard-coded start year would have encoded today's answer and gone quietly wrong
  on an ERS backfill.
- **No new data source was needed.** ERS Table 22 lives in the same keyless file
  node 3 already downloads, so FAS GATS, FAS Export Sales Reporting and Census
  USA Trade Online were all ruled out before anything was fetched.

### The four problems, as answered

1. **Corn is not soybeans -- and the shares are now measured, not recalled.**
   China's share of US corn exports by marketing year, from ERS Table 22: 0.5%
   (2018), 4.6% (2019), 30.8% (2020), 23.3% (2021), 18.3% (2022), 5.2% (2023),
   **0.04% (2024)**. Mexico runs 22-40% throughout and is 35.1% in 2024; Japan
   16-25%. China is episodic; Mexico and Japan are the steady buyers. **Decision:
   corn only**, with the destination table shipped as context so a scenario can
   be stated against measured purchases. The soybean and acreage channel --
   probably the larger one for a China tariff, since China takes roughly half of
   US soybean exports -- is documented in the bundle README and in the output's
   `not_captured`, and is a separate brief.
2. **The coefficient was fitted on supply shocks. Decision: reuse it**, with the
   symmetry assumption stated in the output document, the README and `not_for`.
   A separate demand-side fit was rejected: exports are endogenous to the price
   within the marketing year, so it would need an instrument, and three episodes
   in fifty years would fail the |t| >= 2.0 rule anyway.
3. **A tariff is not a one-for-one sales loss. Decision: bushels, national.**
   Measured, and the reason this is not negotiable: US corn sales to China fell
   from 118 mil bu in marketing year 2023 to 1 mil bu in 2024 while **total US
   corn exports rose** from 2,255 to 2,873 mil bu; and across the 1980 Soviet
   embargo exports were 2,401 mil bu in 1979 against 2,391 in 1980. Both
   episodes reallocated instead of disappearing.
4. **Announcement and expectation.** Stated in `not_for`, the README and the
   output document, all three, together with the fact that this is not a
   political forecast.

### The consequence nobody expected: nothing validates it

Because both candidate episodes produced an aggregate bushel loss of roughly
zero, **there is no historical trade episode this bundle can reproduce**, the
way `corn-price` reproduces 2012. That is not a gap in the work; it is the
model's own headline caveat showing up in its test plan. The check suite proves
the arithmetic, the labelling and the loud failures instead, and the README says
why. Do not let a later reviewer's reasonable request for a validated episode
turn into a fitted number.

### Verified results (2026-09-20)

- `check_trade_policy.py`: **200/200 checks pass** (171 before the Copilot review).
- **Sample run** (real node 1 -> node 2 -> node 3 chain, 300 mil bu scenario):
  the scenario is +1.8541% of 16,180 mil bu of total use. Weather **-0.18%**
  [-0.29, -0.09], carried through from node 3 unchanged. Trade **-1.44%**
  [-2.33, -0.73]. Combined **-1.62%** [-2.61, -0.82] = **-$0.0777/bu** on $4.80.
  The naive sum would have been -1.6206% against the correct -1.6179%.
- **Docker build and run** produce output **identical** to the local run apart
  from `generated_at`, with `--network none`. A bare `docker run` works from the
  bundled samples.
- **Modelfile validates** (`OK`, no annotation warnings), and
  `check_schema_compatibility` confirms the first input **binds** node 3's
  `corn_price_impact` and is **refused** by `corn_price_regions`,
  `corn_yield_snapshot` and `corn_yield_trajectory`.
- **Copilot review (PR #1):** four findings, all legitimate, all addressed. Two
  were schema text that contradicted the runner's own supported behaviour -- a
  field the runner always emits missing from `required`, and two share fields
  documented as "from 0 to 1" when a negative scenario legitimately produces
  negative shares. Two were real robustness holes: a falsey non-string
  `scenario_label` was coerced to empty instead of rejected, and the upstream
  bootstrap interval's elements reached `float()` unvalidated, so a malformed
  bound exited with a traceback rather than a named `RunError`. Checks went
  171 -> **200**. No committed table, coefficient or headline figure changed.
- **Not yet verified:** the Model Home import, which needs a signed-in human at
  the Auth0 login.

### Task list

1. Add the model on the local Model Home stack from the branch subfolder URL and
   run it after `corn-price` in a flow, with the scenario wired as an `inline`
   literal; mark the pull request ready once it passes.
2. After merge: register on Model Home from `main` and compose after
   `corn-price`.
3. Upstream follow-up in `ag-commodity-bundles`: carry the ERS national trend
   production (area harvested times trend yield) in node 3's output metadata, the
   same way `export_exposure` was added for this model, and switch this model's
   denominator to it.
4. The soybean and acreage channel, as its own brief in this repo. The bundle
   README's soybean section is its specification.

## Task list

1. ~~Create `modelhome/ag-trade-bundles` with boilerplate and the vendored feat
   skill.~~ Done 2026-09-21.
2. ~~Brief, plan and build `corn-trade-policy/` (node 4).~~ Done 2026-09-20;
   see that bundle's task list above for what remains.
3. Upstream follow-up in `ag-commodity-bundles`: `corn-price/README.md` gives
   the 2012 end-to-end result as -22.04% while its `CLAUDE.md` gives -21.92%.
   They cannot both be right.
