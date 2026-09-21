#!/usr/bin/env python3
"""
One-time build script for corn-trade-policy/destinations.csv. Not part of the
model image.

Assembles US corn exports by destination and marketing year: the context this
bundle prints beside a scenario so a reader can see who actually buys US corn
before deciding how many bushels a scenario should remove. Nothing in the
model's arithmetic reads it.

Source, public and needing no API key -- the SAME file node 3
(ag-commodity-bundles/corn-price) builds price_history.csv from, so the two
bundles share a vintage rather than picking different ones:

- USDA ERS Feed Grains Database, "Feed Grains Yearbook Tables -- All Years"
  machine-readable CSV, https://www.ers.usda.gov/media/5766/
  feed-grains-yearbook-tables-all-years.csv (about 18 MB).

Two tables are read:

  Table 22  U.S. corn and sorghum exports by selected destinations -- the series
            this script commits, in 1,000 metric tons, marketing year Sep-Aug.
  Table 4   Corn: Supply and disappearance -- the national "Exports" line, read
            ONLY to validate Table 22 against the balance sheet node 3 already
            publishes. Nothing from Table 4 is committed here; re-sourcing node
            3's balance sheet is exactly what this flow is built to avoid.

Why the window is derived rather than declared. Table 22 carries rows back to
1989, but its early years are not the whole trade: measured against Table 4 in
the same file, 1989 is 99% short, 1990 is 99% short and 1991 is 34% short, while
1992 onward ties out to within 2.1e-06 relative. A hard-coded start year would
encode today's answer and quietly go wrong if ERS backfills. So the rule is the
tie-out itself: a marketing year is committed only when Table 22's world total
matches Table 4's exports for that year within TIE_OUT_TOLERANCE, and the years
that fail are recorded in the meta with their error. The excluded years must
form an unbroken run at the start of the series; a gap in the middle means
something changed that this script does not understand, and it stops.

Units. ERS publishes Table 22 in 1,000 metric tons and the balance sheet in
million bushels. One bushel of corn is 56 lb = 25.4012 kg, so one metric ton is
1000 / 25.4012 = 39.36822 bushels, and one thousand metric tons is 0.03936822
million bushels. The conversion happens once, here, at build time; the committed
table is in million bushels and nothing downstream converts again.

Usage:

    python build_destinations.py     # writes destinations.csv beside this file

Downloads are cached in .ers-cache/ (gitignored); delete it to force a refetch.
"""
import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".ers-cache"
OUT_PATH = HERE / "destinations.csv"
META_PATH = HERE / "destinations.meta.json"

ERS_URL = (
    "https://www.ers.usda.gov/media/5766/feed-grains-yearbook-tables-all-years.csv"
)
ERS_VINTAGE = "USDA ERS Feed Grains Database, Feed Grains Yearbook Tables -- All Years"
USER_AGENT = "modelhome-ag-trade-bundles/corn-trade-policy (build_destinations.py)"

TABLE_22 = "Table 22--U.S. corn and sorghum exports by selected destinations"
TABLE_4 = "Table 4--Corn: Supply and disappearance"

# The row ERS uses for the annual total across every destination.
WORLD_TOTAL = "World total"

# 1,000 metric tons -> million bushels. 1 bu corn = 56 lb = 25.4012 kg, so
# 1 t = 1000 / 25.4012 = 39.36822 bu and 1,000 t = 0.03936822 mil bu.
KG_PER_BUSHEL = 25.4012
MIL_BU_PER_THOUSAND_TONNES = (1000.0 / KG_PER_BUSHEL) / 1000.0

# A committed year must match the balance sheet this closely. The years that do
# match come in at 2.1e-06 or better, and the years that do not are out by 0.34
# or more, so anything in between would be a new situation worth stopping for.
TIE_OUT_TOLERANCE = 1e-4


def log(message):
    print(message, file=sys.stderr)


def download(url, path):
    """Fetch url to path unless it is already cached. Returns (path, last_modified)."""
    headers_path = path.with_suffix(path.suffix + ".headers.json")
    if path.exists():
        log(f"cached  {path.name}")
        if headers_path.exists():
            return path, json.loads(headers_path.read_text()).get("last_modified")
        return path, None
    path.parent.mkdir(parents=True, exist_ok=True)
    log(f"fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    partial = path.with_suffix(path.suffix + ".partial")
    with urllib.request.urlopen(request, timeout=600) as response, open(partial, "wb") as fh:
        last_modified = response.headers.get("Last-Modified")
        while chunk := response.read(1 << 20):
            fh.write(chunk)
    partial.rename(path)
    headers_path.write_text(json.dumps({"last_modified": last_modified}))
    log(f"saved   {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    return path, last_modified


def read_destinations(rows):
    """{year: {destination: mil_bu}} from Table 22, including the world total."""
    out = {}
    for row in rows:
        if not row["table_name"].startswith(TABLE_22):
            continue
        if row["commodity"] != "Corn":
            continue
        if row["frequency"] != "Annual":
            continue
        if row["timeperiod"] != "Marketing year Sep-Aug":
            continue
        # The unit is asserted rather than assumed: the conversion factor below
        # is only correct for this one, and a silent unit change upstream would
        # otherwise produce a table that is wrong by a factor.
        if row["unit"] != "1,000 metric tons":
            raise SystemExit(
                f"unexpected unit {row['unit']!r} in {TABLE_22!r}; this script "
                "converts from '1,000 metric tons' and cannot read anything else"
            )
        amount = (row["amount"] or "").strip()
        if not amount:
            continue
        year = int(row["year"])
        out.setdefault(year, {})[row["geography"]] = (
            float(amount) * MIL_BU_PER_THOUSAND_TONNES
        )
    if not out:
        raise SystemExit(
            f"no corn rows in {TABLE_22!r}; the ERS export may have changed"
        )
    return out


def read_national_exports(rows):
    """{year: mil_bu} from Table 4, for validation only. Never committed."""
    out = {}
    for row in rows:
        if not row["table_name"].startswith(TABLE_4):
            continue
        if row["commodity"] != "Corn" or row["geography"] != "United States":
            continue
        if row["attribute"] != "Exports" or row["frequency"] != "Annual":
            continue
        amount = (row["amount"] or "").strip()
        if not amount:
            continue
        out[int(row["year"])] = float(amount)
    if not out:
        raise SystemExit(
            f"no 'Exports' rows for US corn in {TABLE_4!r}; the ERS export may "
            "have changed, and Table 22 cannot be validated without them"
        )
    return out


def main():
    path, last_modified = download(ERS_URL, CACHE / "feed-grains-all-years.csv")
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    log(f"ers: {len(rows)} rows")

    by_year = read_destinations(rows)
    national = read_national_exports(rows)
    log(f"table 22: {len(by_year)} marketing years, {min(by_year)}-{max(by_year)}")

    # Every year must carry the world total: the shares are computed against it
    # and it is what the tie-out compares. A year without one is not usable.
    missing_total = sorted(y for y, d in by_year.items() if WORLD_TOTAL not in d)
    if missing_total:
        raise SystemExit(
            f"no {WORLD_TOTAL!r} row for {missing_total} in {TABLE_22!r}; the "
            "annual total cannot be inferred by summing selected destinations"
        )

    # The destinations must account for the world total. ERS carries an 'Other'
    # line for exactly this reason, so any shortfall means a row was dropped by
    # the filters above rather than that the table is genuinely partial.
    for year, dests in sorted(by_year.items()):
        total = dests[WORLD_TOTAL]
        summed = sum(v for k, v in dests.items() if k != WORLD_TOTAL)
        if total and abs(summed - total) / total > TIE_OUT_TOLERANCE:
            raise SystemExit(
                f"{year}: destinations sum to {summed:.3f} mil bu against a world "
                f"total of {total:.3f}; a destination row is being dropped"
            )

    # The window is the tie-out, not a hard-coded year. See the module docstring.
    tie_out = {}
    for year, dests in sorted(by_year.items()):
        if year not in national:
            raise SystemExit(
                f"{year} is in {TABLE_22!r} but not in {TABLE_4!r}; Table 22 "
                "cannot be validated against the balance sheet for that year"
            )
        table_4_mil_bu = national[year]
        error = abs(dests[WORLD_TOTAL] - table_4_mil_bu) / table_4_mil_bu
        tie_out[year] = error

    excluded = sorted(y for y, e in tie_out.items() if e > TIE_OUT_TOLERANCE)
    included = sorted(y for y, e in tie_out.items() if e <= TIE_OUT_TOLERANCE)
    if not included:
        raise SystemExit(
            "no marketing year in Table 22 ties out to Table 4 within "
            f"{TIE_OUT_TOLERANCE}; the two series are not the same quantity"
        )
    # The failures are an artefact of ERS's early destination coverage, so they
    # belong at the start of the series. A gap in the middle is a different
    # problem and must not be papered over by dropping a year from the middle.
    if excluded and excluded != [y for y in sorted(tie_out) if y < included[0]]:
        raise SystemExit(
            f"years failing the tie-out are {excluded}, which is not an unbroken "
            f"run before the first good year {included[0]}; refusing to guess"
        )
    for year in excluded:
        log(f"excluded {year}: world total is {tie_out[year]:.1%} from Table 4")
    log(f"committing {included[0]}-{included[-1]} ({len(included)} marketing years)")

    out_rows = []
    annual_totals = {}
    for year in included:
        dests = by_year[year]
        total = dests[WORLD_TOTAL]
        annual_totals[str(year)] = round(total, 3)
        for destination, mil_bu in sorted(
            ((k, v) for k, v in dests.items() if k != WORLD_TOTAL),
            key=lambda kv: (-kv[1], kv[0]),
        ):
            out_rows.append({
                "marketing_year": year,
                "destination": destination,
                # Six decimals, not three: ERS carries destinations as small as
                # 3.9e-06 mil bu (a few tonnes to Tokelau), and rounding those to
                # zero would put a false zero in a table whose every value is a
                # real positive shipment.
                "exports_mil_bu": f"{mil_bu:.6f}",
                "share_of_total_exports": f"{mil_bu / total:.6f}",
            })

    with open(OUT_PATH, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "marketing_year", "destination", "exports_mil_bu",
                "share_of_total_exports",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)
    log(f"wrote {OUT_PATH.name} ({len(out_rows)} rows)")

    latest = included[-1]
    meta = {
        "vintage": ERS_VINTAGE,
        "source": ERS_URL,
        "source_last_modified": last_modified,
        "tables": [TABLE_22, f"{TABLE_4} (validation only, not committed)"],
        "unit": "million bushels",
        "source_unit": "1,000 metric tons",
        "conversion": (
            "1,000 metric tons x 0.03936822 = million bushels "
            "(1 bu corn = 56 lb = 25.4012 kg, so 1 t = 39.36822 bu)"
        ),
        "marketing_year": "Sep-Aug",
        "period": f"{included[0]}-{included[-1]}",
        "latest_marketing_year": latest,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "destinations": len({r["destination"] for r in out_rows}),
        "annual_total_exports_mil_bu": annual_totals,
        "tie_out": {
            "method": (
                f"Table 22's {WORLD_TOTAL} compared against Table 4's US corn "
                "Exports for the same marketing year, in the same file and the "
                "same vintage"
            ),
            "tolerance_relative": TIE_OUT_TOLERANCE,
            "years_committed": len(included),
            "max_relative_error_committed": max(tie_out[y] for y in included),
            "excluded_years": {
                str(y): round(tie_out[y], 6) for y in excluded
            },
        },
        "definitions": {
            "role": (
                "context only. This table tells a reader who buys US corn and how "
                "much; it enters no arithmetic in this model and is never used to "
                "convert a scenario into bushels"
            ),
            "share_of_total_exports": (
                "a destination's exports over that marketing year's world total, "
                "both from Table 22"
            ),
            "lag": (
                "Table 22 ends one marketing year before the balance sheet, which "
                "carries a WASDE projection. The two must never be presented as "
                "the same year"
            ),
        },
        "note": (
            "Built once by build_destinations.py and never edited by hand. The "
            "window is derived from the tie-out above rather than declared, so a "
            "future ERS backfill widens it on the next build instead of being "
            "locked out by a hard-coded start year."
        ),
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n")
    log(f"wrote {META_PATH.name}")
    log(
        f"latest marketing year {latest}: "
        f"{annual_totals[str(latest)]:.1f} mil bu across "
        f"{len([r for r in out_rows if r['marketing_year'] == latest])} destinations"
    )


if __name__ == "__main__":
    main()
