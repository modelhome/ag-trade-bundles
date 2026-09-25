# Upstream passthrough

## Outcome

`corn-trade-policy/` publishes node 3's per-state weather result alongside its
own, so a reader of the four-model flow's single `output.json` sees the whole
chain: the ten states' yield anomalies that made the weather shock, the national
figures that summarise them, and the trade scenario priced beside them.

Today node 4 receives node 3's complete `corn_price_impact` document -- its
`regions` rows, its `national` block and its `assumptions` included -- and
drops most of it. That was right for a model that is national only, but it
leaves the four-model flow unable to show *why* the weather component is what it
is. A flow serves only its last step's output, and node 3's own `latest`
excludes runs made as a flow step, so node 4's document is the only place those
rows can reach a reader of this flow.

The first consumer is damagefunction.com's corn trade desk
(`modelhome/damagefunctions`, brief 0005), which puts ten state sliders and a
trade slider on one page and needs the state rows to seed them. The change is
not specific to that page: any reader of the flow gains the evidence behind the
weather figure node 4 already reports.

## Scope

### In scope

- **Carry node 3's document through, unchanged.** Node 4's
  `corn_trade_policy_impact` output gains node 3's `regions`, `national` and
  `assumptions`, copied from the input exactly as received -- no field renamed,
  recomputed, rounded, filtered or reordered. Where they sit is the plan's
  decision, within the constraints below. Also in scope: whether to carry those
  three members or node 3's whole document under one key. The whole document
  is simpler to state and to test; the three members avoid duplicating node 3's
  `metadata`, which node 4 already echoes in part.
- **Say what it is.** The carried block states in its own words that it is node
  3's result, carried through for reference, not recomputed and not an input to
  any of node 4's arithmetic. The per-state rows describe the weather, not the
  trade scenario, which remains national.
- **Declare it in the output schema** with a plain-language `description` on
  each new property, following the repo's Modelfile conventions.
- **README and `CLAUDE.md`.** The bundle README's output section documents the
  new block. `CLAUDE.md`'s "national only" design note is amended to say that
  node 4 carries node 3's regions but still attributes nothing to them.
- **The check suite proves the passthrough**: that the carried block equals the
  input's corresponding members exactly, that node 4's existing output fields
  are unchanged by this feature, and that none of the new fields feeds any of
  node 4's arithmetic -- for example, perturbing a carried region's anomaly
  leaves `national.trade` and `national.combined` unchanged.
- **Binding verified.** `check_schema_compatibility` still binds node 4's first
  input to node 3's `corn_price_impact` and still refuses `corn_price_regions`,
  `corn_yield_snapshot` and `corn_yield_trajectory`. And node 4's widened output
  does **not** bind as a `corn_price_impact` input, including node 4's own first
  input.
- **Samples refreshed**, if the plan finds any committed sample output or
  worked figure that the new block would make stale.

### Out of scope

- **Any change to node 3** (`ag-commodity-bundles/corn-price/`), its outputs or
  its schema. The three-model flow that ends at node 3 must be untouched by
  this brief; see Constraints.
- Per-state attribution of the trade scenario. Export demand is national; node 4
  still does no region join, and nothing here splits a lost cargo across states.
- Any change to node 4's arithmetic, its inputs, its sign convention, its
  denominator, or any published figure.
- Carrying node 2's `corn_yield_trajectory` or any other earlier step's output.
  Node 4 receives only node 3's document and carries only that.
- The damagefunction.com page itself, and the Model Home import and flow update,
  which happen after merge.

## Acceptance criteria

- **AC-1** -- Node 4's output carries node 3's `regions`, `national` and
  `assumptions` exactly as received, and a check asserts deep equality against
  the input for the committed sample.
- **AC-2** -- Every field node 4 published before this change is present with
  the same name, type and value on the committed samples, apart from
  `generated_at`.
- **AC-3** -- A check shows the carried block feeds no arithmetic: changing a
  carried region's anomaly or a carried national figure, while keeping the
  fields node 4 reads, leaves `national.trade` and `national.combined`
  unchanged.
- **AC-4** -- The output schema declares the new block with a description on
  every new property, and the Modelfile still validates with no annotation
  warnings.
- **AC-5** -- `check_schema_compatibility` binds node 4's first input to node 3's
  `corn_price_impact`, refuses `corn_price_regions`, `corn_yield_snapshot` and
  `corn_yield_trajectory`, and refuses node 4's own widened output as a
  `corn_price_impact`.
- **AC-6** -- No file under `ag-commodity-bundles` changes, and node 3's
  committed sample output still binds to node 4 exactly as before.
- **AC-7** -- The carried block labels itself as node 3's result, carried
  through and not recomputed, in the output document.
- **AC-8** -- The bundle README and `CLAUDE.md` document the new block and the
  amended national-only note.
- **AC-9** -- `docker run --network none` on the bundled samples still works
  and its output matches the local run apart from `generated_at`.

## Constraints and dependencies

- **The three-model flow must keep working, and it does by construction.** That
  flow ends at node 3, and this brief changes only node 4's output. Node 3's
  document already contains everything to be carried, so node 3 needs no
  change. Node 4's first input schema is unchanged, so the four-model flow's
  wiring from node 3 is unchanged too. AC-6 holds the line.
- **Do not add a top-level `regions` key to node 4's output.** Flow steps bind
  by required-key set. Node 3's `corn_price_impact` is identified by
  `["generated_at", "metadata", "national", "regions", "assumptions"]`, and node
  4's output already has four of those five. Adding top-level `regions` would
  let node 4's output pass for node 3's at the key level, which is exactly the
  ambiguity this repo's `CLAUDE.md` warns about with `corn_price_regions`.
  Nest the carried block instead: under `metadata.upstream`, which already
  echoes node 3's tables and upstream run, or under a single new top-level key.
  AC-5 checks the result either way.
- **`metadata` is a plain object in node 4's output schema**, as it is in node
  3's. If the block goes under it, declaring sub-properties there is optional,
  but the descriptions in AC-4 are not; document them where the schema allows.
- **Unchanged means unchanged.** Node 3's values are rounded as published. The
  passthrough copies them as parsed JSON and does not round-trip them through
  any arithmetic or formatting.
- **Duplication is accepted and stated.** Node 3's `national` repeats figures
  node 4 already carries in `national.weather`. The duplication is the cost of
  carrying the source unchanged. The output says which block is node 4's result
  and which is node 3's, and the two agree by construction.
- **Output size.** Ten region rows plus node 3's national and assumptions add a
  few kilobytes. No platform limit is near.
- **After merge**, the Model Home model for node 4 must be rebuilt from `main`,
  and the four-model flow `corn-weather-yield-price-policy` must run on the new
  version before its output carries the block. Whether the flow picks up a new
  model version automatically or has to be re-pointed is a platform question
  for the plan to verify, not assume.
- Follows the repo conventions in `CLAUDE.md`: no network at run time, no new
  dependency, no emojis, stdlib only.

## General guidance

- Before you write the plan, ask any questions you need to in order to best
  implement the brief.
- Read node 3's `corn-price/Modelfile.toml` output schema for the carried
  fields' names, types and nullability rather than taking them from this brief.
