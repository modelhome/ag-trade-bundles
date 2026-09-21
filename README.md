# ag-trade-bundles

Standalone [Model Home](https://modelhome.run) model bundles for agricultural
**trade**: the layer that turns a market quantity into the consequence of a
trade-policy or export-demand shock. Each subfolder is a self-contained model: a
`Modelfile.toml`, a `Dockerfile`, a `runner.py`, and sample inputs.

Nothing upstream is vendored here. Libraries these bundles depend on are
installed as pinned pip packages inside each bundle's image.

## Bundles

| Bundle | Model | Inputs -> Outputs |
|---|---|---|
| `corn-trade-policy/` | **Not yet built.** US corn trade-policy impact: the price move implied by a stated export-demand scenario, beside the weather-driven move the upstream model reports | a `corn-price` impact document plus a stated lost-sales scenario -> the combined implied impact, weather and trade components reported separately |

This is the trade end of a climate -> agriculture -> finance flow:

| Node | Repo | Job |
|---|---|---|
| 1 | [`agromet-bundles/crop-weather/`](https://github.com/modelhome/agromet-bundles) | the daily weather series, in PCSE's own variables and units |
| 2 | [`wofost-bundles/corn-yield/`](https://github.com/modelhome/wofost-bundles) | phenology, projected yield, weather-driven yield anomaly per state |
| 3 | [`ag-commodity-bundles/corn-price/`](https://github.com/modelhome/ag-commodity-bundles) | the national production shock and the price impact it implies |
| **4** | **`ag-trade-bundles/corn-trade-policy/`** | **the price impact a stated export-demand shock implies, beside node 3's** |

Node 3's output is node 4's input, unchanged. Node 4 never re-derives anything
node 3 produces, never refits node 3's transmission, and never redefines the
region set.

## Quick start

Each bundle builds and runs from its own folder, which is also the build context
Model Home uses:

```bash
cd corn-trade-policy
docker build -t ag-trade-corn-trade-policy:local .
docker run --rm ag-trade-corn-trade-policy:local   # needs no network
```

Or, when creating a new model on Model Home, paste the bundle folder's GitHub
URL (for example
`https://github.com/modelhome/ag-trade-bundles/tree/main/corn-trade-policy`)
into the "classic import" option.

Each bundle's README covers its inputs, outputs, data sources, the transmission
it assumes and its limits. See [`CLAUDE.md`](./CLAUDE.md) for the design notes,
the conventions every bundle follows, and how features are briefed, planned and
built.

## What these numbers are not

Nothing here is a price forecast, a trading signal, or investment advice, and
nothing here is a political forecast: no bundle in this repo predicts whether a
tariff will be imposed, extended or lifted. A bundle reports the price impact
*implied by* a scenario **the user states**, under a stated transmission, with
its assumptions and its uncertainty printed beside the number. Read the bundle
README before using a figure for anything.

## Licence

MIT. See [`LICENSE`](./LICENSE). Each bundle's README carries the full
attribution for its own data tables.
