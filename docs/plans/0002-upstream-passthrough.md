# Plan: Upstream passthrough

Source brief: docs/features/0002-upstream-passthrough.md
Status: implemented
Planned against commit: 93d0d18 ("Merge pull request #2: corn-trade-policy sample naming for the two inputs")
Base commit: 93d0d18 (branch feat/0002-upstream-passthrough created from it)

Upstream at planning time: `ag-commodity-bundles` `main` = `7a07216`, "Merge pull
request #3: corn-price twelve-region strata (brief 0003)". Node 3's output
schema below was read from that checkout's `corn-price/Modelfile.toml`, not
from the brief.

## Outcome

`corn-trade-policy/` (node 4) keeps node 3's `regions`, `national` and
`assumptions`, which it already receives and currently drops, and publishes them
unchanged in its `corn_trade_policy_impact` output under one new top-level key.
A reader of the four-model flow then gets the per-region weather evidence in
the same `output.json` as the trade scenario. The carried block says it is node
3's result, carried through for reference, recomputed by nothing and feeding
none of node 4's arithmetic. No figure node 4 publishes today changes.

The first consumer is damagefunction.com's corn trade desk
(`modelhome/damagefunctions`, brief 0005), which seeds its per-region sliders
from these rows.

## Scope

### In scope

- `runner.py`: add `upstream_price_impact` to the output document.
- `Modelfile.toml`: declare the new output key; correct the two input
  descriptions and the output comment that say node 4 does not read or carry
  node 3's regions.
- `check_trade_policy.py`: new checks for AC-1, AC-3, AC-4, AC-7 and the new
  loud failures (D-5); update the AC-20 README checks for the new output section.
- `corn-trade-policy/README.md`: a new **Output** section (the README has none
  today; the brief assumed one), the amended national-only statement, and the
  sample-refresh follow-up under Future work.
- `CLAUDE.md`: amend the national-only notes, correct the stale ten-key region
  list, update the verified results, and add the sample-refresh follow-up.

### Out of scope

As the brief states: any change to node 3 or to anything under
`ag-commodity-bundles`; per-region attribution of the trade scenario; any change
to node 4's arithmetic, inputs, sign convention, denominator or published
figures; carrying node 2's output; the damagefunction.com page; the Model Home
import and flow update after merge.

Added by this plan: **refreshing the committed sample to node 3's current
twelve-region output** is deferred (D-3), and is recorded as a follow-up.

## Assumptions and decisions

Answers received while planning (John, 2026-09-24):

- **D-3 -- keep the committed sample; record a refresh as a follow-up.**
  Answered directly: "Keep the sample as recommended, but record the suggestion
  for a follow up in the README and anywhere else it makes sense."

The other two planning questions were asked and dismissed without an answer, so
this plan uses the recommended option for each. **Both are open for review
before `run`:**

- **D-1 -- placement: a new top-level key, `upstream_price_impact`** *(open
  for review)*. The brief allowed either this or `metadata.upstream`. A
  top-level key was chosen because these rows are results rather than a record
  of how the run was made, which is what `metadata` describes. It also gives the
  block a schema where each member can be declared and described (AC-4), whereas
  `metadata` is an undeclared plain object. The name matches node 3's output
  name, `corn_price_impact`, so a reader can see where the block came from. The
  runner always emits the key, so it is added to the output's `required` list;
  the Copilot review of PR #1 established that a field the runner always emits
  belongs there.
- **D-2 -- carry the three members, not the whole document; declare only the
  three members** *(open for review)*. Of the two options the brief offered,
  this plan takes the three members, `regions`, `national` and `assumptions`.
  The whole document would repeat node 3's `metadata`, which node 4 already
  echoes in part in `metadata.transmission`, `metadata.export_exposure` and
  `metadata.upstream`. In the schema the three members are declared with their
  types (`array` of `object`, `object`, `object`) and descriptions, and the
  descriptions point to node 3's Modelfile for the fields inside each. Node 3's
  per-field declarations are not copied: brief 0003 added four region fields to
  node 3 after node 4 shipped, and a copied declaration would have gone stale
  without anyone noticing.

Decisions made while planning, from the brief and the repository:

- **D-3 -- the sample stays at ten regions.** Node 3 moved to twelve regions
  in brief 0003 (`ks` and `ne` each split into `_irrigated` and `_rainfed`,
  with new per-row `stratum` fields). Node 4's committed
  `sample_corn_price_impact.json` predates that and has ten. The passthrough
  does not depend on the shape of the document, so AC-1 is proved on the
  committed sample as it is, and the AC-2 before/after comparison stays clean
  because no committed input changes. The twelve-region shape is covered by a
  one-off verification (see Verification) rather than a committed fixture.
  **Wording:** the brief says "ten states"; the README and `CLAUDE.md` will say
  "node 3's regions (twelve today)", since the carried rows are regions, and
  Kansas and Nebraska each appear twice.
- **D-4 -- the block's contents.** `upstream_price_impact` is
  `{"source": <text>, "regions": ..., "national": ..., "assumptions": ...}`. The
  three members are `copy.deepcopy` of the input's members, so a later in-place
  edit elsewhere in the runner cannot change what is published. They go through
  no rounding and no formatting. `source` states that this is the US Corn Price
  Impact model's (node 3's) result, carried through unchanged for reference;
  that it is not recomputed and not an input to any figure elsewhere in the
  document; that the per-region rows describe the weather component only and the
  trade scenario is national and attributed to no region; and that node 3's
  `national` repeats figures in `national.weather`, and the two agree by
  construction (AC-7). `copy` is stdlib; no new dependency.
- **D-5 -- a missing or mistyped member fails loudly.** Node 3's schema
  requires all three members, and node 4's input schema already requires them,
  so a flow refuses a document without them. Standalone, the runner today reads
  `assumptions` with `.get(...) or {}` and never touches `regions`. After this
  change the runner uses `require(...)` for each member and checks its type
  (`regions` a list, `national` and `assumptions` objects), and raises a named
  `RunError` rather than publishing a partial block. A document that already
  broke the declared input schema used to run and now stops. That is the only
  behaviour change, and it follows the repo's "fail loudly" convention. The
  existing `not_captured` inheritance keeps its current logic.
- **D-6 -- Modelfile text corrections.** The input `regions` description ("This
  model is national only and does not read them") and the output comment above
  `[[outputs]]` ("does no region join at all") become false or incomplete. They
  are reworded to say the rows are carried through unchanged and are never
  joined on or attributed to. The input `assumptions` description gains the same
  note. The declared types and `required` lists of both inputs are unchanged, so
  binding is unaffected (AC-5).
- **D-7 -- binding follows from the design, and is still checked.** Node 3's
  input set is `[generated_at, metadata, national, regions, assumptions]`. Node
  4's output set becomes `[generated_at, metadata, scenario, national,
  assumptions, upstream_price_impact]`: it still has no top-level `regions`, and
  node 4's `national` lacks the keys node 4's first input requires there
  (`us_yield_shock_pct`, `price_impact_pct`, ...). So node 4's output is refused
  as a `corn_price_impact` for two independent reasons.
- **D-8 -- the platform picks up a rebuilt model through its `model_id`.** In
  `modelhome/backend/app/repositories/flow_version_repository.py` a flow step
  references a `model_id`, and a flow's versioned fields are `model_id`,
  `step_order`, `primitive_type` and `input_mapping`, with no model version
  pinned. Rebuilding node 4 under its existing model should therefore reach the
  `corn-weather-yield-price-policy` flow without re-pointing it. The code
  suggests this; nobody has confirmed it on the platform. It is a post-merge
  check (see Risks), not part of `run`.

## Acceptance-criteria traceability

The IDs are the brief's own, AC-1 to AC-9, unchanged.

| ID | Acceptance criterion | Implementation | Verification | Status |
|---|---|---|---|---|
| AC-1 | Output carries node 3's `regions`, `national`, `assumptions` exactly as received; a check asserts deep equality against the input for the committed sample | `runner.py` `carried_upstream()`, `copy.deepcopy` of each member | check_passthrough: three deep-equality checks pass on the committed sample; one-off: identical on a fresh twelve-region node 3 run (12 regions, 34 KB); a mutation dropping one region row is caught (242/243) | pass |
| AC-2 | Every pre-existing field present with same name, type and value on the committed samples, apart from `generated_at` | `runner.py` adds one key, `upstream_price_impact`; nothing else in the output changes | one-off diff vs the pre-edit baseline: `identical`; check: the only new top-level key is `upstream_price_impact`; all 207 pre-existing checks still pass | pass |
| AC-3 | Perturbing a carried region anomaly or a carried national figure (keeping the fields node 4 reads) leaves `national.trade` and `national.combined` unchanged | the carried block is a deep copy taken from the input and read by no calculation | check_passthrough perturbs `regions[0].yield_anomaly_real_pct`, `national.us_production_shock_bu`, `national.coverage_share_of_us_production` and `assumptions.weighting`: `national.trade`, `national.combined`, `national.weather` and `scenario` are unchanged, and the carried block shows the perturbed values | pass |
| AC-4 | Output schema declares the new block with a description on every new property; Modelfile validates with no annotation warnings | `Modelfile.toml` `[outputs.schema.properties.upstream_price_impact]` with `source`, `regions` (+`items`), `national` and `assumptions`, each typed and described; added to `required` | check_passthrough schema checks pass; the `check_annotations` walk passes; validator `OK`, exit 0, no warnings | pass |
| AC-5 | Binds node 4's first input to `corn_price_impact`; refuses `corn_price_regions`, `corn_yield_snapshot`, `corn_yield_trajectory`, and node 4's own widened output | schema only; no input schema type or required list changed | binding script exit 0: BINDS node 3 `corn_price_impact`; REFUSED `corn_price_regions`, `corn_yield_snapshot`, `corn_yield_trajectory`, node 4's own output (missing `regions`) | pass |
| AC-6 | No file under `ag-commodity-bundles` changes; node 3's committed sample output still binds to node 4 exactly as before | no file under `ag-commodity-bundles` touched | `git status --short` shows only the untracked `corn-price/.claude/` that predates this work; `git diff --stat 7a07216` is empty; node 4 runs on the committed sample and on a fresh node 3 run | pass |
| AC-7 | The carried block labels itself as node 3's result, carried through and not recomputed | `runner.py` `UPSTREAM_SOURCE` in `upstream_price_impact.source` | six check_passthrough source-note checks pass (names node 3's model, carried through unchanged, not recomputed, feeds no figure, weather only, attributed to no region) | pass |
| AC-8 | Bundle README and `CLAUDE.md` document the new block and the amended national-only note | README: new **Output** section, input note, Future work item; `CLAUDE.md`: Region identity, design note, problem 3, verified results, task list items 5-6 | README checks for `## output` and `upstream_price_impact` pass; `CLAUDE.md` read in the branch diff | pass |
| AC-9 | `docker run --network none` on the bundled samples still works and matches the local run apart from `generated_at` | no Dockerfile change | rebuilt on final code; `docker run --network none` exit 0; output identical to the local run apart from `generated_at` | pass |

## Verification

Run from the repository root unless the row says otherwise. `SP` is a scratch
directory outside the repo.

| Command | Purpose | Baseline result | Final result |
|---|---|---|---|
| `uv run --python 3.12 python corn-trade-policy/runner.py corn-trade-policy/sample_corn_price_impact.json corn-trade-policy/sample_scenario.json > $SP/after.json` (baseline: the same to `$SP/before.json`, **before any edit**) | the model runs; AC-1, AC-2 | exit 0; weather -0.18% [-0.29, -0.09], trade -1.44% [-2.33, -0.73], combined -1.62% [-2.61, -0.82] = -0.0777 $/bu | exit 0; identical figures |
| `python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); [d.pop("generated_at") for d in (a,b)]; b.pop("upstream_price_impact"); assert a==b, "changed"; print("identical")' $SP/before.json $SP/after.json` | AC-2: nothing published before has changed | n/a (needs both runs) | `identical` |
| `uv run --python 3.12 python corn-trade-policy/check_trade_policy.py $SP/after.json` | the modelling claims, plus AC-1, 3, 4, 7, 8 | **207/207** pass, exit 0 (the plan expected 200; PR #2 added seven sample-payload checks after plan 0001 recorded 200) | **243/243** pass, exit 0; 36 new checks |
| `cd corn-trade-policy && docker build -t ag-trade-corn-trade-policy:local . && docker run --rm --network none ag-trade-corn-trade-policy:local > $SP/docker.json`, then the row-2 comparison between `$SP/after.json` and `$SP/docker.json` without the `pop("upstream_price_impact")` | AC-9 | build exit 0; `docker run --network none` exit 0; identical to the local run apart from `generated_at` | rebuilt on final code: exit 0; identical apart from `generated_at` |
| `cd /Users/john/repos/modelhome && uv run python -m orchestration.modelfile validate <abs path>/corn-trade-policy/Modelfile.toml` | AC-4 | `OK`, exit 0 | `OK`, exit 0, no annotation warnings |
| `cd /Users/john/repos/modelhome && uv run python $SP/bind.py` -- a scratch script calling `check_schema_compatibility` for: node 4 input 1 vs node 3 `corn_price_impact` (bind); vs node 3 `corn_price_regions`, node 2 `corn_yield_snapshot`, node 2 `corn_yield_trajectory` (refuse); vs node 4's own `corn_trade_policy_impact` (refuse) | AC-5 | exit 0: BINDS node 3 `corn_price_impact`; REFUSED `corn_price_regions`, `corn_yield_snapshot`, `corn_yield_trajectory`, and node 4's own output (missing `regions`) | unchanged: exit 0, same five verdicts |
| `cd ~/repos/ag-commodity-bundles/corn-price && uv run --python 3.12 python runner.py sample_input.json > $SP/n3.json`, then node 4 on `$SP/n3.json` and a deep-equality comparison of the carried block against it | AC-1 and AC-6 on node 3's **current twelve-region** shape, without committing a fixture (D-3) | done at planning: node 4 runs on it today (exit 0, 12 regions, 23 KB) | exit 0; carried block identical to node 3's members; 12 regions; node 4 output 34 KB |
| `git -C ~/repos/ag-commodity-bundles status --short && git -C ~/repos/ag-commodity-bundles diff --stat 7a07216` | AC-6 | clean apart from an untracked `corn-price/.claude/` present before this work | unchanged: only that untracked directory; empty diff |

The binding script and the comparison one-liners are verification tools, not
committed files, as in plan 0001. The check suite needs Python 3.11 or newer.

## Implementation steps

1. **Baseline.** Before editing, capture `$SP/before.json` and run the check
   suite and the Modelfile validator; record the results in the Verification
   table.
2. **Runner.** In `process()`, after the arithmetic and before assembling the
   return value, read the three members with `require(...)` and type-check them
   (D-5). Build `upstream_price_impact` from `copy.deepcopy` of each, with the
   `source` text (D-4) as a module-level constant beside `NOT_A_FORECAST`. Add
   it as the last top-level key of the returned document. Replace the
   `upstream.get("assumptions") or {}` read with the required value, keeping
   the `not_captured` logic. Update the module docstring's summary to mention
   the passthrough in one sentence. Change nothing else.
3. **Modelfile.** Add `upstream_price_impact` to `[outputs.schema].required`.
   Declare `[outputs.schema.properties.upstream_price_impact]` (object, with
   required `["source", "regions", "national", "assumptions"]`) and its four
   properties with types and descriptions; `regions` gets an `items` of type
   object with a description. Descriptions point to node 3's Modelfile for the
   fields inside (D-2). Reword the input `regions` and `assumptions`
   descriptions and the output comment (D-6). Extend the output `description`
   by one clause. Keep `validity_domain`, `provenance` and `not_for` as they
   are: no cap is at risk, and nothing in them becomes false.
4. **Check suite.** Add a `check_passthrough(document)` section covering AC-1,
   AC-3 and AC-7, a loud-failure case for each of the three members missing and
   mistyped (D-5), and schema assertions for AC-4 (required, typed, described).
   Extend `check_readme()` with the output section and the key name. Update the
   module docstring's list of what could go wrong with "a carried block that
   silently feeds the arithmetic".
5. **README.** Add an **Output** section after "How the number is worked out",
   listing the five existing top-level keys briefly and describing
   `upstream_price_impact`: what it holds, that it is node 3's result carried
   through, that it is not recomputed and feeds nothing, that the per-region
   rows describe weather only, and where its field definitions live. Amend any
   national-only statement to "national for the trade scenario; carries node
   3's regions but attributes nothing to them". Under **Future work** add:
   *refresh `sample_corn_price_impact.json` (and `sample_payload.json`, which
   embeds it) from a real node 1 -> 2 -> 3 run on node 3's twelve-region
   output, and update the worked figures recorded in this README and
   `CLAUDE.md`.*
6. **`CLAUDE.md`.** In "Region identity", replace the ten-key list with node
   1's current twelve keys (`ia, il, mn, ne_irrigated, ne_rainfed, in, sd, oh,
   wi, ks_irrigated, ks_rainfed, mo`, verified against
   `agromet-bundles/crop-weather/regions.csv` at planning time), and change the
   node 4 sentence to say that node 4 has no region join and carries node 3's
   regions unchanged without attributing anything to them. In the
   `corn-trade-policy/` section, add the new output key to the design notes and
   the file tree comment where relevant. Update "Verified results" with the new
   check count and the date. Add the sample refresh to the bundle's task list.
   Add a "Built ... from brief 0002" line beside the existing brief 0001
   reference.
7. **Verify.** Run every Verification row and record the results. Spot-read the
   output: the carried block is last, `source` reads plainly, and nothing above
   it has moved.
8. **Plan bookkeeping.** Update this plan's statuses, base commit and any
   deviations, then open the pull request as `feat` `run` prescribes.

## Files likely to change

- `corn-trade-policy/runner.py`
- `corn-trade-policy/Modelfile.toml`
- `corn-trade-policy/check_trade_policy.py`
- `corn-trade-policy/README.md`
- `CLAUDE.md`
- `docs/plans/0002-upstream-passthrough.md` (this file, at run time)

Not changing: `Dockerfile`, both committed samples and `sample_payload.json`
(D-3), `destinations.*`, `build_destinations.py`, the repo `README.md` (its
"never redefines the region set" line stays true), and anything under
`ag-commodity-bundles`.

## Deviations from the plan

- **Baseline check count was 207, not 200.** Plan 0001 recorded 200; PR #2
  (sample naming) added seven sample-payload checks. The plan's expectation was
  corrected when the baseline was recorded.
- **A mistyped `national` fails on its first field read, not in
  `carried_upstream()`.** The arithmetic reads `national.us_yield_shock_pct`
  before the passthrough runs, so a `national` that is a list fails there with
  "the upstream document has no national.us_yield_shock_pct". The run still
  stops with a named `RunError` that mentions `national`, which is what D-5 and
  the check require; the type check in `carried_upstream()` is the backstop.
- **README input section gained one paragraph** pointing to the new Output
  section. The plan named only the Output section and Future work.
- **`CLAUDE.md` gained a second follow-up** (task 6, confirm the flow picks up
  the rebuilt model), recording D-8's post-merge check where the next session
  will see it, beside the sample-refresh item the user asked for.
- **Mutation check (not committed).** A scratch copy of the bundle whose runner
  dropped one carried region row failed exactly one check ("the carried regions
  equals the input's regions exactly", 242/243), confirming the new checks detect
  a broken passthrough.

## Risks and follow-ups

- **Follow-up: refresh the committed sample to twelve regions (D-3).**
  Regenerate `sample_corn_price_impact.json` and `sample_payload.json` from a
  real node 1 -> 2 -> 3 chain on current `main`, and update the worked figures
  in `corn-trade-policy/README.md` and `CLAUDE.md`. The weather, combined and
  dollar figures will change; trade stays at -1.44% as long as the export
  exposure is unchanged. Recorded in the bundle README's Future work and the
  `CLAUDE.md` task list.
- **Post-merge: confirm the flow picks up the rebuilt model (D-8).** Rebuild
  node 4 from `main`, run `corn-weather-yield-price-policy`, and confirm its
  `output.json` carries `upstream_price_impact`. If the platform instead needs a
  new model or the step re-pointed, record that in `CLAUDE.md`'s
  platform facts.
- **The consumer's slider count.** Brief 0005 in `damagefunctions` refers to
  ten state sliders; the carried rows are twelve regions, with Kansas and
  Nebraska each appearing as irrigated and rainfed. That is the page's decision,
  but worth raising when that brief is planned.
- **Schema depth (D-2).** A consumer reading the declared schema will not find
  node 3's per-row fields there, only a pointer to node 3's Modelfile. If the
  page needs declared fields, mirroring them is a later, separable change.
- **Duplication.** Node 3's `national` repeats `national.weather`. The two agree
  by construction; the `source` text says which block belongs to which model.
  If they ever disagreed, the existing reproduction check on the weather figure
  would already have stopped the run.
