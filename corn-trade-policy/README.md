# corn-trade-policy

**US Corn Trade Policy Impact** -- node 4 of the climate -> agriculture ->
finance flow.

Takes the [US Corn Price Impact](https://github.com/modelhome/ag-commodity-bundles)
model's result (node 3) and a trade scenario **you state**, and reports the corn
price impact that scenario implies **beside** the weather-driven impact node 3
already reports. The two components are kept apart, each carries its own range,
and the combined figure is composed the way the transmission is specified rather
than by adding two percentages.

This model **fits nothing**. The transmission coefficient, its bootstrap
interval, the reference price and the export exposure all arrive in the input
document, so an upstream refit propagates here without a change on this side.

## What this is not

It is the price impact **implied by** a scenario you supply, against a baseline
in which that scenario does not happen. It is **not a forecast**: not a price
forecast, not a trading signal and not investment advice. It is also **not a
political forecast** -- nothing here predicts whether a tariff or any other trade
measure will be imposed, extended or lifted. The scenario is an input, never an
output.

It does not convert a tariff rate into lost sales, and deliberately cannot. See
[Why bushels, not tariffs](#why-bushels-not-tariffs).

## Running it

```bash
cd corn-trade-policy
python runner.py sample_corn_price_impact.json sample_scenario.json > impact.json
```

```bash
docker build -t ag-trade-corn-trade-policy:local .
docker run --rm --network none ag-trade-corn-trade-policy:local
```

`--network none` is the test, not a precaution: the model makes no network calls
at run time.

The validation check needs Python 3.11 or newer to read `Modelfile.toml`:

```bash
uv run --python 3.12 python check_trade_policy.py
```

## Input

Two inputs.

**1. `corn_price_impact`** -- node 3's document, unchanged. In a flow this is
wired straight from that model's output. Flow steps bind by required-key set,
and this model declares
`["generated_at", "metadata", "national", "regions", "assumptions"]`, which
matches `corn_price_impact` and **not** `corn_price_regions`, whose required
keys (`metadata` / `columns` / `rows`) also match the yield model's snapshot two
steps up and would bind the wrong document.

Everything economic is read from it:

| Field | Used for |
|---|---|
| `metadata.transmission.shock_coefficient` | the coefficient applied to the scenario |
| `metadata.transmission.shock_coefficient_ci95` | every low and high figure published here |
| `metadata.export_exposure.current` | total use, the basis the scenario is divided by |
| `metadata.export_exposure.latest_complete` | the export ceiling a scenario is checked against |
| `national.us_yield_shock_pct` | the weather shock, combined with the scenario's |
| `national.price_impact_pct` and its range | the weather component, carried through unchanged |
| `national.reference_price_usd_bu` | the dollar figures |

Several of these are *optional* properties in node 3's output schema, so this
model checks each one and **fails loudly naming the path** rather than
defaulting.

Node 3's `regions`, `national` and `assumptions` are also carried through whole,
unchanged, into the output's `upstream_price_impact`. That copy feeds none of
the figures above; see [Output](#output).

**2. `scenario`** -- what you assume, supplied per run. In a flow it is an
**`inline`** literal the flow author writes; the platform resolves each input
independently, so a second input does not have to come from the step before.

```json
{
  "bushels_not_sold_mil_bu": 300,
  "scenario_label": "illustrative: 300 mil bu of export demand removed"
}
```

`required = []`, with the defaults in the runner, so an absent, empty, null or
zero scenario gives a trade component of **exactly zero** and the combined
figure equals node 3's weather figure. The bundle runs standalone.

### Filling in the run form

This model declares **two** inputs, so Model Home asks for one slot per input
name rather than for a single document:

```json
{ "corn_price_impact": null, "scenario": null }
```

`sample_corn_price_impact.json` is the value for the **first slot only**. Paste
it there and the scenario into the second, or paste the whole envelope at once:
**`sample_payload.json`** is exactly that, the two committed samples under their
declared input names.

```json
{
  "corn_price_impact": { "generated_at": "...", "metadata": {}, "national": {}, "regions": [], "assumptions": {} },
  "scenario": { "bushels_not_sold_mil_bu": 300, "scenario_label": "..." }
}
```

The platform also accepts one link standing in for the whole set, returning that
same object. `sample_payload.json` is a paste target for the form; `runner.py`
never reads it, because it takes the two documents as separate paths.

**In a flow you paste nothing**: `corn_price_impact` is wired from the
`corn-price` step's output and `scenario` is the `inline` literal you supply.
That is the path this bundle is built around.

The upstream input deliberately ships **no** schema `default`, because a
runnable example for it is a whole upstream document -- so the platform shows a
placeholder shape for it rather than calling it an example to paste. The
scenario input does ship one.

## Why bushels, not tariffs

**Trade reallocates.** A model that turned a tariff rate into lost bushels by
itself would be claiming knowledge it does not have. Two measured episodes, both
from data committed in this flow:

- US corn sales to China fell from **118 mil bu** in marketing year 2023 to
  **1 mil bu** in 2024 -- and total US corn exports **rose**, from 2,255 to
  2,873 mil bu. The buyer left; the bushels found other buyers.
- Across the 1980 Soviet grain embargo, US corn exports were **2,401 mil bu** in
  marketing year 1979 against **2,391** in 1980. Essentially flat. That year's
  price move belongs mostly to a -7.2% yield deviation, not to the embargo.

So the step from a policy to a number of bushels belongs to whoever states the
scenario, and this model takes the bushels.

The same two episodes are why **no historical episode validates this model**: in
both, the aggregate bushel loss was roughly zero, so there is no known move for a
known shock to reproduce. The check suite proves the arithmetic, the labelling
and the loud failures instead, and says so.

## How the number is worked out

### 1. The scenario becomes a shock

Node 3's coefficient is fitted on the national yield's deviation from trend, as
a fraction. The scenario arrives in million bushels, so it has to be divided by
something to become the same kind of quantity.

**It is divided by total use** for the current marketing year, recovered from
node 3's own export exposure as `exports_mil_bu / export_share_of_use` --
**16,180 mil bu** for marketing year 2026. Nothing is re-sourced.

This is the model's one approximation, and it is reported in the output rather
than buried:

| Basis | 2026 value | 300 mil bu implies |
|---|---|---|
| ERS trend production (area x trend yield) -- what the fit normalises by | 16,344 mil bu | -1.426% |
| **Total use -- what this model uses** | **16,180 mil bu** | **-1.440%** |
| Node 3's `us_trend_production_bu` -- **not used** | 14,894 mil bu | -1.564% |

Node 3's output does not carry the ERS trend production. Total use is the
closest available basis: about 1% below it for 2026, with the gap running -3.4%
to +6.7% over 2015-2026. Node 3's `us_trend_production_bu` is deliberately **not
used** -- it is built from 2022 Census acreage, sits 8.9% below the fitted basis
and would inflate the answer by a tenth. Closing the remaining gap is a
follow-up on node 3, not a change here.

**Exports are a component of total use, never an addition to it.** A lost-export
scenario reduces the denominator as well as the numerator, and nothing here ever
adds the two together.

### 2. The sign convention

Bushels **not sold** are demand removed. For price that is equivalent to a
surplus of the same size, so the scenario enters with the **sign of a surplus**:
a positive `bushels_not_sold_mil_bu` gives a positive equivalent supply shock
and therefore a **negative** price impact. A negative scenario -- extra sales --
runs and gives a positive impact.

### 3. The transmission, reused

The coefficient is node 3's, fitted on `dlog_price = a + b0*d + c*d[t-1]` over
1976-2025, n = 50, **b0 = -0.7826**, bootstrap 95% [-1.269, -0.393], R-squared
0.329. It is read from the input document; no coefficient is written down in
this bundle.

**The symmetry assumption.** That fit is on **supply-side weather shocks**. Node
3's own `not_captured` list states that export demand shocks and trade policy
are outside it. Applying it to a demand shock assumes the price responds
symmetrically to a bushel removed from demand and a bushel added to supply.
Post-harvest the supply curve is close to vertical, which makes the symmetry
defensible -- but it is an assumption this model *makes* and does not
*demonstrate*, and it is stated in the output document, in the Modelfile's
`not_for`, and here.

Fitting a separate demand-side transmission was considered and rejected: exports
are endogenous to the price within the marketing year, so it would need an
instrument, and the relevant episodes are about three in fifty years -- which the
upstream repo's fixed |t| >= 2.0 selection rule would reject anyway.

### 4. The two effects compose, they do not add

The transmission is log-linear: the impact is `exp(b0 * d) - 1`. Two shocks
therefore **compose inside the exponential**, so the combined figure is **not**
the sum of the weather and trade percentages. On the committed sample:

| | shock | price impact |
|---|---|---|
| Weather (from node 3) | +0.2303% | **-0.18%** [-0.29, -0.09] |
| Trade (300 mil bu) | +1.8541% | **-1.44%** [-2.33, -0.73] |
| Combined | +2.0844% | **-1.62%** [-2.61, -0.82] |

The naive sum would be -1.6206%; the correct composition is -1.6179%.

Because both components use the **same** coefficient, their intervals are
perfectly correlated. The combined interval comes from applying the bootstrap
bounds to the combined shock, never from adding two intervals.

## Output

One JSON document, `corn_trade_policy_impact`, with six top-level keys:

| Key | What it holds |
|---|---|
| `generated_at` | when the output was written (UTC) |
| `metadata` | how the run was made: the upstream transmission, the export exposure, the destination table's vintage, the upstream run |
| `scenario` | the scenario as stated, and its size against total use and against a complete year's exports |
| `national` | this model's result: `weather` (from node 3), `trade` and `combined`, each with its range |
| `assumptions` | every assumption behind the numbers, including the inherited `not_captured` list |
| `upstream_price_impact` | node 3's own result, carried through for reference (below) |

### `upstream_price_impact`: node 3's result, carried through

A flow serves only its last step's output, so this block is where a reader of
the four-model flow finds the evidence behind the weather component: the
per-region yield anomalies that made the national weather shock, and the
national figures that summarise them.

```json
"upstream_price_impact": {
  "source": "This block is the upstream US Corn Price Impact model's (node 3's) result, carried through unchanged ...",
  "regions": [ { "region_key": "ia", "yield_anomaly_real_pct": ..., "contribution_pct": ..., ... }, ... ],
  "national": { "us_yield_shock_pct": ..., "price_impact_pct": ..., ... },
  "assumptions": { "not_a_forecast": "...", "not_captured": [ ... ], ... }
}
```

- **Unchanged.** `regions`, `national` and `assumptions` are node 3's members
  exactly as received: no field renamed, recomputed, rounded, filtered or
  reordered. Their fields are defined in node 3's output schema
  (`ag-commodity-bundles/corn-price/Modelfile.toml`), not repeated here.
- **Inert.** None of it enters this model's arithmetic. The check suite changes
  a carried region's anomaly and several carried national figures and confirms
  that `national.trade` and `national.combined` do not move.
- **Weather only.** The per-region rows describe the weather component. The
  trade scenario stays **national**: this model does no region join and
  attributes nothing to any region. Export demand is a national quantity, and
  there is no defensible way to assign a lost cargo to one state rather than
  another.
- **Duplicated on purpose.** Node 3's `national` repeats figures in
  `national.weather`. That is the cost of carrying the source unchanged; the two
  agree by construction, and `source` says which block belongs to which model.
- **Nested on purpose.** There is no top-level `regions` key. Flow steps bind by
  required-key set, and a top-level `regions` would bring this document within
  one key of node 3's `corn_price_impact`.

Node 3 currently returns **twelve regions**: Kansas and Nebraska each appear
twice, as irrigated and rainfed. The committed sample predates that change and
has ten (see [Future work](#future-work)). The block carries whatever node 3
sends.

A missing or mistyped `regions`, `national` or `assumptions` in the input stops
the run with a message naming it, rather than publishing a partial block.

## The interval

Every low and high figure is node 3's bootstrap interval on the transmission
coefficient, reused unchanged. It says how well that relationship is known from
fifty years of supply shocks. It is **not** a probability that the scenario
happens, and **not** a range for what the corn price will do.

## The destination table

`destinations.csv` carries US corn exports by destination and marketing year,
1992-2024, in million bushels. It is **context only**: it enters no arithmetic
and is never used to convert a policy into bushels. Its job is to let you see who
actually buys US corn before deciding how many bushels a scenario should remove.

Marketing year 2024, the latest the table covers:

| Destination | mil bu | share |
|---|---|---|
| Mexico | 1,007.6 | 35.1% |
| Japan | 529.8 | 18.5% |
| Colombia | 300.4 | 10.5% |
| South Korea | 241.8 | 8.4% |
| European Union-27 | 148.2 | 5.2% |
| China | 1.3 | 0.0% |

China's purchases are **episodic** -- 0.5% of US corn exports in 2018, 30.8% in
2020, 23.3% in 2021, 18.3% in 2022, then 0.04% in 2024 -- while Mexico and Japan
are the steady buyers. A scenario built on an impression of who buys US corn is
worth checking against this table first.

| | |
|---|---|
| Source | USDA ERS Feed Grains Database, Feed Grains Yearbook Tables -- All Years, `Table 22--U.S. corn and sorghum exports by selected destinations` |
| Vintage | the same file and vintage node 3 builds `price_history.csv` from |
| Window | derived, not declared: a marketing year is committed only when Table 22's world total ties out to Table 4's exports within 1e-4. 1989, 1990 and 1991 fail that by 98.9%, 99.1% and 34.3% and are excluded, with their errors recorded in `destinations.meta.json`. The committed years tie out to 2.1e-06 |
| Units | published in 1,000 metric tons, converted once at build time at 0.03936822 mil bu per 1,000 t (1 bu corn = 56 lb = 25.4012 kg) |
| Built by | `build_destinations.py`, once, never edited by hand |

**The table lags the balance sheet by one marketing year.** Table 22 ends at
2024 while node 3's balance sheet carries a 2026 WASDE projection. The output
labels both and never presents them as the same year.

## The soybean channel, and how it would be approached

**This model prices the direct corn channel only, and for a China tariff that is
probably the smaller one.**

China takes roughly half of US **soybean** exports -- about 51% in 2024, an
average near 47% across 2018-2024, against about 60% before 2018 -- and, as the
table above shows, close to nothing of US **corn** in most years. So a tariff
aimed at China hits soybeans directly and corn barely at all.

The larger corn effect is **indirect**, and it runs through acreage. A soybean
price fall makes corn relatively more attractive at planting; acres shift to corn
the following spring; the larger corn crop pushes the corn price down **a year
later**. A corn-only direct-sales model misses that entirely, which is why it is
named in the output's `not_captured` list rather than left implicit.

Building it would need, roughly in order:

1. A soybean balance sheet from the **ERS Oil Crops Yearbook** -- a separate
   keyless CSV from the same agency, whose location and format changed in March
   2026 and which must be verified rather than assumed.
2. A soybean price transmission, fitted the way node 3 fits its own, on a
   regressor defined the same way the model defines its shock.
3. A corn acreage response to the expected new-crop corn-to-soybean price ratio.
4. A one-year lag, so the corn effect lands in the following marketing year.

That is two more fits and a second balance sheet. It is a separate model and a
separate brief, not a term in this one. Until it exists, this bundle prices the
direct channel and says so.

## Committed tables

| File | What | Source and vintage |
|---|---|---|
| `destinations.csv` | US corn exports by destination, 1992-2024, mil bu | USDA ERS Feed Grains Yearbook Tables, Table 22 |
| `destinations.meta.json` | source URL, server `last-modified`, period, build date, the tie-out and the excluded years | written by `build_destinations.py` |

`build_destinations.py` is **not** in the image: it needs the network and an
18 MB USDA export. Neither is `check_trade_policy.py`.

## Determinism

Deterministic and offline. The model is a pure function of its two input
documents and the committed destination table: no network calls, no randomness,
and no wall-clock dependence beyond the `generated_at` stamp. The table's vintage
travels in the output metadata so a reader can see how old the context is.

## Limitations

- **The symmetry assumption** above: a supply-side coefficient applied to a
  demand shock.
- **The denominator** is total use, about 1% from the basis the coefficient was
  fitted on for 2026 and up to about 7% away in other years.
- **No historical episode validates the model**, because the candidate episodes
  reallocated rather than disappeared.
- **Announcement and expectation.** Once a measure is known it is in the price.
  This answers what a scenario implies against a baseline without it, which is
  not what happens next.
- **Annual, not intra-season.** The transmission is fitted on a marketing-year
  average cash price, so it says nothing about when within the season a move
  lands. A within-season futures transmission is future work upstream.
- **The soybean and acreage channel** is not modelled.
- Everything node 3's transmission does not capture is inherited, and is carried
  into this model's `not_captured` list rather than dropped.

## Future work

- Take the ERS national trend production from node 3 once it carries it, and
  close the denominator gap.
- The soybean channel, as its own brief.
- A within-season futures transmission, which would let a scenario be priced on
  the time base a policy announcement actually moves.
- Refresh `sample_corn_price_impact.json`, and `sample_payload.json`, which
  embeds it, from a real node 1 -> 2 -> 3 run on node 3's current
  twelve-region output, and update the worked figures in this README and in the
  repo's `CLAUDE.md`. The committed sample predates node 3's twelve-region
  change and still has ten regions. It runs correctly, but it is not what the
  live flow produces.

## Licence

MIT. See [`LICENSE`](../LICENSE). The destination table is derived from USDA ERS
public data.
