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

**Not yet built.** No brief, no plan, no code. What follows is the design
context carried over from the node 3 discussion that produced this repo. It is
**recorded reasoning, not settled design**: the brief is where it becomes a
decision, and every open question below is genuinely open.

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

### Shape, as far as it is understood

Input 1: node 3's `corn_price_impact`, bound on its required-key set. Input 2: a
**scenario**, supplied per run as an `inline` literal -- bushels of export demand
removed. Output: the combined implied impact with the weather and trade
components reported **separately**, each with its own interval.

Illustrative magnitude, using node 3's committed coefficient and the 2026
projection row, purely to show the channel is worth modelling: 300 mil bu
removed against 16,180 mil bu of total use is a 1.85% demand shock; times
-0.7826 is about -1.45%, or roughly -$0.07/bu on $4.80, interval -0.73% to
-2.35%. That is several times the weather signal in node 3's committed sample
run (-0.18%). **An illustration of magnitude, not a result**, and it inherits
every caveat below.

### The four problems the brief has to answer

1. **Corn is not soybeans.** China's corn purchases are episodic -- near zero in
   most years, a large spike in 2020-22, then down again -- while Mexico and
   Japan are the steady buyers. The dominant China-tariff channel for corn is
   probably *indirect*: a soybean price fall shifts acreage to corn the
   following spring and pushes the corn price down with a one-year lag. A
   corn-only direct-sales model would miss the larger effect. **Verify these
   shares against ERS and Census data; they are recollection, not measurement.**
2. **Node 3's coefficient was fitted on supply shocks.** Reusing b0 for a demand
   shock assumes symmetry. Post-harvest supply is near-vertical so it is not
   unreasonable, but it is an assumption that belongs in the output rather than
   buried in a build script. Fitting a separate demand-side transmission is the
   alternative and is more work; decide in the brief, with reasons.
3. **A tariff is not a one-for-one sales loss.** See the modelling-honesty
   section: take bushels, not tariff rates.
4. **Announcement and expectation.** Once a tariff is known it is in the price.
   Node 4 answers "what does this scenario imply against a no-tariff baseline",
   which is not "what happens next". Say so in `not_for`, in the README and in
   the output document -- all three, the way node 3 does.

### Task list

1. Write brief `docs/features/0001-corn-trade-policy.md`, resolving the four
   questions above with John before planning.
2. `/feat plan`, review, `/feat run`.
3. Register on Model Home and compose after `corn-price` in the flow.

## Task list

1. ~~Create `modelhome/ag-trade-bundles` with boilerplate and the vendored feat
   skill.~~ Done 2026-09-21.
2. Brief, plan and build `corn-trade-policy/` (node 4).
3. Upstream follow-up in `ag-commodity-bundles`: `corn-price/README.md` gives
   the 2012 end-to-end result as -22.04% while its `CLAUDE.md` gives -21.92%.
   They cannot both be right.
