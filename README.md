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

Wikipedia pages updated using this tool:

- **Airports:** [ACE](https://en.wikipedia.org/wiki/Lanzarote_Airport), [AGP](https://en.wikipedia.org/wiki/M%C3%A1laga_Airport), [ALC](https://en.wikipedia.org/wiki/Alicante%E2%80%93Elche_Miguel_Hern%C3%A1ndez_Airport), [AMM](https://en.wikipedia.org/wiki/Queen_Alia_International_Airport), [ATH](https://en.wikipedia.org/wiki/Athens_International_Airport), [ATL](https://en.wikipedia.org/wiki/Hartsfield%E2%80%93Jackson_Atlanta_International_Airport), [BLQ](https://en.wikipedia.org/wiki/Bologna_Guglielmo_Marconi_Airport), [BNA](https://en.wikipedia.org/wiki/Nashville_International_Airport), [BOG](https://en.wikipedia.org/wiki/El_Dorado_International_Airport), [BRI](https://en.wikipedia.org/wiki/Bari_Karol_Wojty%C5%82a_Airport), [COD](https://en.wikipedia.org/wiki/Yellowstone_Regional_Airport), [CTG](https://en.wikipedia.org/wiki/Rafael_N%C3%BA%C3%B1ez_International_Airport), [FRA](https://en.wikipedia.org/wiki/Frankfurt_Airport), [GUA](https://en.wikipedia.org/wiki/La_Aurora_International_Airport), [IDA](https://en.wikipedia.org/wiki/Idaho_Falls_Regional_Airport), [IBZ](https://en.wikipedia.org/wiki/Ibiza_Airport), [IND](https://en.wikipedia.org/wiki/Indianapolis_International_Airport), [JED](https://en.wikipedia.org/wiki/King_Abdulaziz_International_Airport), [JFK](https://en.wikipedia.org/wiki/John_F._Kennedy_International_Airport), [KBP](https://en.wikipedia.org/wiki/Boryspil_International_Airport), [KOA](https://en.wikipedia.org/wiki/Kona_International_Airport), [KWI](https://en.wikipedia.org/wiki/Kuwait_International_Airport), [LAS](https://en.wikipedia.org/wiki/Harry_Reid_International_Airport), [LAX](https://en.wikipedia.org/wiki/Los_Angeles_International_Airport), [MED](https://en.wikipedia.org/wiki/Prince_Mohammad_bin_Abdulaziz_International_Airport), [MUC](https://en.wikipedia.org/wiki/Munich_Airport), [OAJ](https://en.wikipedia.org/wiki/Albert_J._Ellis_Airport), [ORD](https://en.wikipedia.org/wiki/O%27Hare_International_Airport), [OWB](https://en.wikipedia.org/wiki/Owensboro%E2%80%93Daviess_County_Regional_Airport), [PRG](https://en.wikipedia.org/wiki/V%C3%A1clav_Havel_Airport_Prague), [PUJ](https://en.wikipedia.org/wiki/Punta_Cana_International_Airport), [RHO](https://en.wikipedia.org/wiki/Rhodes_International_Airport), [RNO](https://en.wikipedia.org/wiki/Reno%E2%80%93Tahoe_International_Airport), [SAN](https://en.wikipedia.org/wiki/San_Diego_International_Airport), [SKG](https://en.wikipedia.org/wiki/Thessaloniki_Airport), [STL](https://en.wikipedia.org/wiki/St._Louis_Lambert_International_Airport), [SVQ](https://en.wikipedia.org/wiki/Seville_Airport), [TAO](https://en.wikipedia.org/wiki/Qingdao_Jiaodong_International_Airport), [TAS](https://en.wikipedia.org/wiki/Tashkent_International_Airport), [URC](https://en.wikipedia.org/wiki/%C3%9Cr%C3%BCmqi_Tianshan_International_Airport), [VCE](https://en.wikipedia.org/wiki/Venice_Marco_Polo_Airport), [VIE](https://en.wikipedia.org/wiki/Vienna_International_Airport), [VLC](https://en.wikipedia.org/wiki/Valencia_Airport), [Chinua Achebe International Airport](https://en.wikipedia.org/wiki/Chinua_Achebe_International_Airport), [Çukurova International Airport](https://en.wikipedia.org/wiki/%C3%87ukurova_International_Airport), [Bayelsa International Airport](https://en.wikipedia.org/wiki/Bayelsa_International_Airport)
- **Airlines:** [Havana Air](https://en.wikipedia.org/wiki/Havana_Air)

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
