import subprocess
import sys
import re
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.airport import Airport
from src.config import AIRPORTS_DIR

AIRPORTS = ["ORD", "LJU", "MUC", "ATL", "MEX", "BOS", "SEA", "IAH", "BOG", "EZE", "CAI", "JNB", "DUB", "BCN", "VIE", "SYD", "PKX", "BOM",
            # Top 10 busiest US airports
            "DFW", "LAX", "DEN", "JFK", "LAS", "CLT", "MCO", "MIA",
            # Top 10 busiest European airports
            "LHR", "IST", "CDG", "AMS", "FRA", "MAD", "FCO", "LGW",
            # Top 10 busiest Chinese airports
            "PVG", "CAN", "PEK", "SZX", "TFU", "CKG", "HGH", "SHA", "KMG",
            # Additional airports
            "DXB", "DOH", "DEL", "BLR", "CCU", "MEL", "CGK", "SIN", "HND", "NRT",
            "ICN", "TPE", "LOS", "ADD", "RAK", "ACC", "SVO", "VKO", "HNL", "AKL",
            "BKK", "CPH", "BEG", "IND", "ATH", "BRU", "YYZ", "YVR", "YUL",
            "CMI"]

KNOWN_ISSUES = {
    "GP Aviation",
    "Travelcoup",
    "FlyGabon",
    "GoTo Fly",
    "Sishen",
    "Havana Air",
    "Crown Airlines",
    "Meraj Airlines",
    "Fly Oya",
    "MedSky Airways",
    "Air Sierra Leone",
    "Sky Shuttle",
    "Barrier Air",
    "Enugu Air",
    "Bayelsa International Airport",
    "Kebbi International Airport",
    "Gianair",
    "Sola Air",
    "Corilair",
    "Iskwew Air",
    "Seair Seaplanes",
    "Gulf Island Seaplanes",
    "Sunshine Coast Air",
    "Comox Water Aerodrome",
    "Sechelt",
    "TezJet",
    "Vologda Aviation Enterprise",
    "Yamburg Airport",
}

def count_raw_rows(code):
    """Count data rows in the destination list template using a simple independent method.

    Counts pipe-separated rows between the {{Airport destination list}} opening
    and the next section header (==). Avoids template-close detection entirely,
    so it won't be fooled by either inline {{citation needed}} templates or
    data rows that end with }}.
    """
    path = os.path.join(AIRPORTS_DIR, f"{code}.txt")
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        text = f.read()
    text = re.sub(r'<ref[^>]*/>', '', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    lines = text.splitlines()
    in_template = False
    in_wikitable = False  # track {|...|}  blocks to avoid counting their rows
    count = 0
    for line in lines:
        if not in_template:
            if re.search(r'\{\{\s*(Airport-dest-list|Airport destination list)', line, re.IGNORECASE):
                in_template = True
        else:
            if re.match(r'==', line):
                break
            # Stop at the next template (e.g. a separate cargo table), since
            # _parseDestTable only uses one template per airport.
            if re.search(r'\{\{\s*(Airport-dest-list|Airport destination list)', line, re.IGNORECASE):
                break
            # Skip {|...|}  wikitables that may appear after the destination template
            # closes — their multi-pipe rows would otherwise inflate the count.
            if line.strip().startswith('{|'):
                in_wikitable = True
            if in_wikitable:
                if line.strip().startswith('|}'):
                    in_wikitable = False
                continue
            if line.count('|') > 1 and not re.match(r'\s*<br', line):
                count += 1
    return count


def extract_name(warning):
    m = re.search(r"skipping (?:airline|airport) '(.*?)'", warning)
    return m.group(1) if m else None

def run(code):
    result = subprocess.run(
        ["python3", "-m", "src.main", "-t", code],
        capture_output=True, text=True
    )
    warnings = [line.strip() for line in result.stdout.splitlines() if line.startswith("Warning:")]
    return warnings

def test_all():
    Airport.code_table.clear()
    Airport.name_table.clear()
    Airport.contents_table.clear()

    failed = False
    for code in AIRPORTS:
        warnings = run(code)
        unexpected = [w for w in warnings if extract_name(w) not in KNOWN_ISSUES]

        raw = count_raw_rows(code)
        parsed = len(Airport(code)._parseDestTable())
        coverage_ok = raw == 0 or parsed >= raw * 0.5

        if unexpected or not coverage_ok:
            print(f"FAIL {code}")
            for w in sorted(unexpected):
                print(f"  unexpected warning: {w}")
            if not coverage_ok:
                print(f"  low parse coverage: parsed {parsed} rows, raw has ~{raw}")
            failed = True
        else:
            print(f"PASS {code}  (parsed {parsed}/{raw} raw rows)")
    return not failed

if __name__ == "__main__":
    sys.exit(0 if test_all() else 1)
