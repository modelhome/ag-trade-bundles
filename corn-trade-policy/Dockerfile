# to build and run from your local machine (build context is this
# corn-trade-policy/ folder, which is also what Model Home uses when the model is
# added from
# github.com/modelhome/ag-trade-bundles/tree/main/corn-trade-policy):
#   cd corn-trade-policy && docker build -t ag-trade-corn-trade-policy:local .
#   docker run --rm --network none ag-trade-corn-trade-policy:local  # uses the bundled samples
#   mkdir -p run && cp sample_corn_price_impact.json run/corn_price_impact.json
#   cp sample_scenario.json run/scenario.json
#   docker run --rm --network none -v "$PWD/run:/run" ag-trade-corn-trade-policy:local \
#       /run/corn_price_impact.json /run/scenario.json \
#       > run/corn_trade_policy_impact.output.json
# The model makes no network calls at run time: --network none is the test.

FROM python:3.12-slim

WORKDIR /app

# No pip install layer. The whole model is one division, two exponentials and a
# table lookup; the fit it applies was done upstream and arrives in the input
# document. There is nothing here that numpy or pandas would make clearer or
# faster, and the repo's rule is that a dependency needs a reason.

# The committed table is part of the model, not an input: US corn exports by
# destination and marketing year, carried so a reader can see who actually buys
# US corn before deciding how many bushels a scenario should remove. It enters no
# arithmetic. build_destinations.py and check_trade_policy.py are development
# tools and are deliberately not copied in -- the first needs the network and an
# 18 MB USDA export, and the second shells out to the runner.
# sample_payload.json is deliberately NOT copied: it is the keyed envelope the
# platform's run form takes, not something runner.py reads. The runner takes
# the two documents as separate paths.
COPY runner.py \
     destinations.csv \
     destinations.meta.json \
     sample_corn_price_impact.json \
     sample_scenario.json \
     ./

ENTRYPOINT ["python", "runner.py"]

# irl the input paths come from the Modelfile; for local testing we default to
# the bundled samples, so a bare `docker run` produces a real result.
CMD ["sample_corn_price_impact.json", "sample_scenario.json"]
