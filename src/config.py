import os

DATA_DIR = "./data"

AIRPORTS_DIR = os.path.join(DATA_DIR, "airports")
AIRPORTS_LIST = os.path.join(DATA_DIR, "airport_list.json")

AIRLINES_DIR = os.path.join(DATA_DIR, "airlines")
AIRLINES_LIST = os.path.join(DATA_DIR, "airline_list.json")
AIRLINES_MANUAL_ALIASES = os.path.join(DATA_DIR, "airline_manual_aliases.json")

PETSCAN_AIRPORTS_CATEGORY = "Airports_by_country"
PETSCAN_AIRLINES_CATEGORY = "Airlines_by_country"
PETSCAN_DEPTH = 5
