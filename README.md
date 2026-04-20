# WikiRunway

Queries Wikipedia to build a database of airports and airlines, then uses that database to look up destination tables by airport IATA code. Right now, two basic pieces of functionality are supported
+ Printing destination tables: Useful if you are familiar with IATA codes
+ Finding "bugs" in Wikipedia: if Delta flies from Atlanta to Cancun, then Delta probably also flies from Cancun to Atlanta. This tool can report violations of this property

## Quickstart

**1. Fetch the full dataset** (bootstrap from scratch — downloads all airports and airlines from Wikipedia):

```
python3 -m src.fetch --all
```

**2. Produce a destination table** for an airport by IATA code:

```
python3 -m src.main -t ORD
```

**3. Run a verify pass** to check for asymmetric routes at an airport:

```
python3 -m src.main -v ORD
```

---

## Usage

### Looking up destinations

```
python3 -m src.main -t <IATA>
```

Prints a table of airlines and their destinations for the given airport. For example:

```
python3 -m src.main -t ORD
```

### Looking up a region

```
python3 -m src.main -r <IATA>
```

Prints the ISO 3166-2 region code for the given airport, parsed from its Wikipedia coordinates. For example:

```
python3 -m src.main -r LHR
```

### Verifying routes

```
python3 -m src.main -v <IATA>
python3 -m src.main -vu <IATA>
```

Checks that every route departing from the given airport is also present in the reverse direction. For example, if Delta is listed as flying ORD→ATL, it should also appear in ATL's table flying to ORD.

#### `-v / --verify CODE`

Reports all asymmetric route pairs as warnings. For example:

```
python3 -m src.main -v ORD
```

#### `-vu / --verify-update CODE`

Like `--verify`, but for each asymmetric airport found, fetches and updates its Wikipedia page in the database, then re-runs the verify pass. Useful for finding real Wikipedia inconsistencies versus stale local data.

### Managing the database

```
python3 -m src.fetch --update <NAME_OR_IATA> [--replace]
python3 -m src.fetch --all [--redirects-only | --missing-only]
```

#### `--update NAME_OR_IATA`

Re-fetches the Wikipedia page for a specific airport or airline and updates its entry in the database. The argument can be:

- A 3-character IATA code → looked up as an airport (e.g. `ORD`)
- A 2-character IATA code → looked up as an airline (e.g. `AA`)
- A Wikipedia page name → searched in both databases (e.g. `"United Airlines"`)
- A Wikipedia page name not yet in the database → fetched and added automatically, type inferred from the IATA code found in the page

After updating the page text, redirect aliases are also refreshed.

`--replace`: discard all existing name aliases and replace with just the new canonical title. Without this flag, the new title is prepended and existing aliases are kept.

#### `--all`

Rebuilds or updates the full database by querying PetScan for all pages in the Wikipedia categories `Airports_by_country` and `Airlines_by_country` (depth 5). Only pages not already in the database are fetched. This is also the command to bootstrap the database from scratch.

`--redirects-only`: skip fetching page content; only refresh redirect aliases for all entries.

`--missing-only`: like `--redirects-only`, but only for entries that currently have no aliases.

## Impact

WikiRunway has been used to update 49 Wikipedia pages; see [impact.md](impact.md) for the full list.

[todo.md](todo.md) has a list of issues that have been identified but not yet fixed.

## Running the tests

```
python3 -m pytest tests/
```

> **Note:** The tests are fragile — they assert against specific destination table contents that reflect Wikipedia as of **1 April 2026**. Because Wikipedia is continuously edited, tests may fail if the local data files have been updated since then.

## Data directory

```
data/
  airport_list.json          # maps IATA code → [canonical name, alias, ...]
  airline_list.json          # maps IATA code → [canonical name, alias, ...]
  airline_manual_aliases.json  # hand-curated name → IATA overrides
  airports/                  # cached Wikipedia wikitext, one file per airport
    ORD.txt
    LHR.txt
    ...
  airlines/                  # cached Wikipedia wikitext, one file per airline
    AA.txt
    UA.txt
    ...
```

The JSON list files map each IATA code to a list of known Wikipedia page names. The first entry in each list is the canonical page title used for fetching; the rest are redirect aliases used for name lookup. The `airline_manual_aliases.json` file contains hand-curated mappings for airline names that appear in destination tables but don't have their own Wikipedia pages (e.g. regional brand names like `"American Eagle"`).

The `.txt` files contain raw Wikipedia wikitext and are used by `src/main.py` to parse destination tables without making live network requests.
