import requests
import re
import os
import time
import json
import argparse
import difflib

from .config import (
    AIRPORTS_DIR, AIRPORTS_LIST, PETSCAN_AIRPORTS_CATEGORY,
    AIRLINES_DIR, AIRLINES_LIST, PETSCAN_AIRLINES_CATEGORY,
    PETSCAN_DEPTH,
)

API = "https://en.wikipedia.org/w/api.php"
PETSCAN = "https://petscan.wmcloud.org/"
HEADERS = {"User-Agent": "WikiRunway/1.0"}

AIRPORTS = {
    "pages_dir": AIRPORTS_DIR,
    "names_file": AIRPORTS_LIST,
    "category": PETSCAN_AIRPORTS_CATEGORY,
}

AIRLINES = {
    "pages_dir": AIRLINES_DIR,
    "names_file": AIRLINES_LIST,
    "category": PETSCAN_AIRLINES_CATEGORY,
}


def extract_airport_iata(text):
    text = re.sub(r'<!--.*?-->', '', text)
    match = re.search(r'\|\s*IATA\s*=\s*([A-Z]{3})', text)
    return match.group(1) if match else None


def extract_airline_iata(text):
    match = re.search(r'\|\s*IATA\s*=\s*([A-Z0-9]{2})', text)
    return match.group(1) if match else None


def load_names(names_file):
    if os.path.exists(names_file):
        with open(names_file, "r") as f:
            return json.load(f)
    return {}


def save_names(name_table, names_file):
    with open(names_file, "w") as f:
        json.dump(name_table, f, ensure_ascii=False, indent=2)


def petscan_query(category, depth):
    print(f"Querying PetScan: {category} (depth={depth})...")
    r = requests.get(PETSCAN, headers=HEADERS, params={
        "categories": category,
        "depth": depth,
        "ns[0]": 0,
        "output_type": "page",
        "doit": 1,
        "format": "json",
    })
    r.raise_for_status()
    pages = r.json()["*"][0]["a"]["*"]
    titles = [p["title"].replace("_", " ") for p in pages]
    print(f"Found {len(titles)} pages.")
    return titles


def fetch_page(title):
    """Fetch a Wikipedia page by title, following redirects.
    Returns (canonical_title, text) or (None, None) on failure.
    """
    r = requests.get(API, headers=HEADERS, params={
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "redirects": 1,
        "format": "json",
    })
    r.raise_for_status()
    page = next(iter(r.json()["query"]["pages"].values()))
    if "revisions" not in page:
        return None, None
    return page["title"], page["revisions"][0]["slots"]["main"]["*"]


def fetch_and_save_batch(titles, name_table, cfg, extract_iata):
    """Fetch wikitext for a list of titles in batches of 50 and save each batch."""
    pages_dir = cfg["pages_dir"]
    names_file = cfg["names_file"]
    saved = 0
    skipped = 0
    for i in range(0, len(titles), 50):
        batch = titles[i:i+50]
        r = requests.get(API, headers=HEADERS, params={
            "action": "query",
            "titles": "|".join(batch),
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": 1,
            "format": "json",
        })
        r.raise_for_status()
        for page in r.json()["query"]["pages"].values():
            if "revisions" in page:
                text = page["revisions"][0]["slots"]["main"]["*"]
                iata = extract_iata(text)
                if iata:
                    os.makedirs(pages_dir, exist_ok=True)
                    with open(os.path.join(pages_dir, iata + ".txt"), "w") as f:
                        f.write(text)
                    if iata not in name_table:
                        name_table[iata] = [page["title"]]
                    elif page["title"] not in name_table[iata]:
                        name_table[iata].append(page["title"])
                    saved += 1
                else:
                    skipped += 1
        save_names(name_table, names_file)
        print(f"  Fetched {min(i+50, len(titles))}/{len(titles)} — saved: {saved}, skipped: {skipped}")
        time.sleep(0.5)
    return saved, skipped


def fetch_redirects(name_table, names_file, missing_only=False, iata_filter=None, verbose=True):
    """Query Wikipedia redirect aliases and add them to the name table.
    Returns (before, added) alias counts.
    """
    name_to_iata = {names[0]: iata for iata, names in name_table.items()}
    all_known_names = {n for names in name_table.values() for n in names}
    titles = list(name_to_iata.keys())

    if iata_filter:
        all_iata_names = name_table[iata_filter]
        name_to_iata.update({n: iata_filter for n in all_iata_names})
        titles = all_iata_names
    elif missing_only:
        titles = [t for t in titles if len(name_table[name_to_iata[t]]) == 1]
        if verbose:
            print(f"{len(titles)} entries have no aliases yet.")

    if verbose:
        print(f"Fetching redirects for {len(titles)} pages...")

    before = len(name_table[iata_filter]) if iata_filter else 0
    added = 0
    for i in range(0, len(titles), 50):
        batch = titles[i:i+50]
        r = requests.get(API, headers=HEADERS, params={
            "action": "query",
            "titles": "|".join(batch),
            "prop": "redirects",
            "rdlimit": "max",
            "format": "json",
        })
        r.raise_for_status()
        data = r.json()
        for norm in data.get("query", {}).get("normalized", []):
            if norm["from"] in name_to_iata:
                name_to_iata[norm["to"]] = name_to_iata[norm["from"]]
        for page in data["query"]["pages"].values():
            iata = name_to_iata.get(page.get("title", ""))
            if iata and "redirects" in page:
                for rd in page["redirects"]:
                    alias = rd["title"]
                    if alias not in all_known_names:
                        name_table[iata].append(alias)
                        all_known_names.add(alias)
                        added += 1
        save_names(name_table, names_file)
        if verbose:
            print(f"  Processed {min(i+50, len(titles))}/{len(titles)} — aliases added: {added}")
        time.sleep(0.5)
    if verbose:
        print(f"Done. Added {added} aliases.")
    return before, added


def update_entry(canonical_title, text, iata, name_table, cfg, replace=False):
    """Save a fetched page and update the name table. Returns (iata, diff_added, diff_removed)."""
    names_file = cfg["names_file"]
    pages_dir = cfg["pages_dir"]

    if iata not in name_table:
        name_table[iata] = []

    new_names = [canonical_title] if replace else \
        [canonical_title] + [n for n in name_table[iata] if n != canonical_title]
    name_table[iata] = new_names
    save_names(name_table, names_file)

    os.makedirs(pages_dir, exist_ok=True)
    path = os.path.join(pages_dir, iata + ".txt")
    old_text = open(path).read() if os.path.exists(path) else ""
    with open(path, "w") as f:
        f.write(text)

    diff = list(difflib.unified_diff(old_text.splitlines(), text.splitlines()))
    added   = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
    return iata, added, removed


def do_update(query, replace):
    airport_names = load_names(AIRPORTS["names_file"])
    airline_names = load_names(AIRLINES["names_file"])

    q = query.strip()
    qu = q.upper()
    cfg = None
    iata = None
    title = q

    if re.fullmatch(r'[A-Z]{3}', qu):
        if qu not in airport_names:
            print(f"Error: {qu} not found in airport database.")
            return
        cfg, iata, title = AIRPORTS, qu, airport_names[qu][0]
    elif re.fullmatch(r'[A-Z0-9]{2}', qu):
        if qu not in airline_names:
            print(f"Error: {qu} not found in airline database.")
            return
        cfg, iata, title = AIRLINES, qu, airline_names[qu][0]
    else:
        for code, names in airport_names.items():
            if q in names:
                cfg, iata, title = AIRPORTS, code, names[0]
                break
        if cfg is None:
            for code, names in airline_names.items():
                if q in names:
                    cfg, iata, title = AIRLINES, code, names[0]
                    break

    canonical_title, text = fetch_page(title)
    if text is None:
        print(f"Error: could not fetch page for '{title}'")
        return

    if cfg is None:
        # New entry: determine type from IATA extracted from page
        airport_iata = extract_airport_iata(text)
        airline_iata = extract_airline_iata(text)
        if airport_iata:
            cfg, iata = AIRPORTS, airport_iata
        elif airline_iata:
            cfg, iata = AIRLINES, airline_iata
        else:
            print(f"Error: no IATA code found in page for '{title}'")
            return

    name_table = airport_names if cfg is AIRPORTS else airline_names
    iata, diff_added, diff_removed = update_entry(canonical_title, text, iata, name_table, cfg, replace)
    if iata:
        aliases_before, aliases_added = fetch_redirects(
            load_names(cfg["names_file"]), cfg["names_file"], iata_filter=iata, verbose=False
        )
        print(f"IATA: {iata}, canonical title: {canonical_title}")
        print(f"  Article: +{diff_added}/-{diff_removed} lines")
        print(f"  Redirects: {aliases_before} → {aliases_before + aliases_added} (+{aliases_added})")


def do_all(redirects_only, missing_only):
    for cfg, extract_iata in [(AIRPORTS, extract_airport_iata), (AIRLINES, extract_airline_iata)]:
        name_table = load_names(cfg["names_file"])
        if not redirects_only and not missing_only:
            titles = petscan_query(cfg["category"], PETSCAN_DEPTH)
            all_known = {n for names in name_table.values() for n in names}
            titles = [t for t in titles if t not in all_known]
            print(f"{len(titles)} new pages to fetch.")
            if titles:
                saved, skipped = fetch_and_save_batch(titles, name_table, cfg, extract_iata)
                print(f"Done. Saved: {saved}, skipped (no IATA): {skipped}")
        name_table = load_names(cfg["names_file"])
        fetch_redirects(name_table, cfg["names_file"], missing_only=missing_only)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", metavar="NAME_OR_IATA",
                        help="Update a specific airport or airline by name or IATA code")
    parser.add_argument("--replace", action="store_true",
                        help="Replace all existing name aliases instead of keeping them")
    parser.add_argument("--all", action="store_true",
                        help="Fetch/update the full database from PetScan")
    parser.add_argument("--redirects-only", action="store_true",
                        help="(With --all) Only fetch redirect aliases, skip page fetching")
    parser.add_argument("--missing-only", action="store_true",
                        help="(With --all) Only fetch redirects for entries with no aliases yet")
    args = parser.parse_args()

    if args.update:
        for query in args.update.split(","):
            do_update(query.strip(), args.replace)
    elif args.all:
        do_all(args.redirects_only, args.missing_only)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
