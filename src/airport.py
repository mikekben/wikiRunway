import requests
import re
import os
import json

from .airline import Airline
from .config import AIRPORTS_DIR, AIRPORTS_LIST
from .region import Region

_request_count = 0
_REQUEST_LIMIT = 100


class Airport:
    NAME_TABLE_PATH = AIRPORTS_LIST
    CONTENTS_PATH = AIRPORTS_DIR
    name_table = {}     # name -> IATA
    code_table = {}     # IATA -> [names]
    contents_table = {}

    def filePath(code):
        return os.path.join(Airport.CONTENTS_PATH, code + ".txt")

    def getPage(title):
        global _request_count
        if _request_count > _REQUEST_LIMIT:
            raise Exception("Request limit exceeded")
        print("Doing request: "+title)
        response = requests.get(f"https://en.wikipedia.org/w/index.php?title={title}&action=raw")
        _request_count += 1
        if response.status_code == 200:
            if '#REDIRECT' in response.text:
                return Airport.getPage(re.findall(r'\[\[(.*?)\]\]',response.text)[0])
            return response.text
        else:
            return None

    def extractIATA(text):
        text = re.sub(r'<!--.*?-->', '', text)
        iata_regex = r'\|\s*IATA\s*=\s*([A-Z]{3})'
        match = re.search(iata_regex, text)
        if match:
            return match.group(1)
        else:
            return None

    def addToTable(code, name, contents=None):
        changed = False
        if code not in Airport.code_table:
            Airport.code_table[code] = [name]
            Airport.name_table[name] = code
            changed = True
        elif name not in Airport.code_table[code]:
            Airport.code_table[code].append(name)
            Airport.name_table[name] = code
            changed = True
        if changed:
            with open(Airport.NAME_TABLE_PATH, "w") as f:
                json.dump(Airport.code_table, f, ensure_ascii=False, indent=2)
        if contents is not None:
            Airport.contents_table[code] = contents

    def __str__(self):
        return self.code

    def __hash__(self):
        return self.code.__hash__()

    def __eq__(self, other):
        return self.code.__eq__(other.code)

    def __init__(self, code=None, name=None):
        #Make sure the tables are updated from files
        if not Airport.code_table:
            with open(Airport.NAME_TABLE_PATH, "r") as f:
                data = json.load(f)
            for iata, names in data.items():
                Airport.code_table[iata] = names
                for n in names:
                    Airport.name_table[n] = iata

        if not Airport.contents_table:
            for kk in Airport.code_table.keys():
                if os.path.exists(Airport.filePath(kk)):
                    with open(Airport.filePath(kk),"r") as file:
                        Airport.contents_table[kk] = file.read()
                else:
                    Airport.contents_table[kk] = None

        if code == None and name == None:
            raise Exception("Either the code, the name, or both must be provided")
        if name == None:
            self.code = code
            if self.code not in Airport.code_table:
                raise Exception("Input code is not in the database and no name is provided")
            elif self.code not in Airport.contents_table:
                self.update()
        elif code == None:
            # Wikipedia treats underscores and spaces as equivalent in page titles.
            name = name.replace('_', ' ')
            if name in Airport.name_table:
                self.code = Airport.name_table[name]
            else:
                contents = Airport.getPage(name)
                if contents is None:
                    raise Exception(f"Could not retrieve page for '{name}'")
                self.code = Airport.extractIATA(contents)
                if self.code is None:
                    raise Exception(f"No IATA code found in page for '{name}'")
                Airport.addToTable(self.code, name, contents)

            if self.code not in Airport.contents_table or Airport.contents_table[self.code] == None:
                self.update()
        else:
            self.code = code
            Airport.addToTable(self.code, name)
            if self.code not in Airport.contents_table or Airport.contents_table[self.code] == None:
                self.update()

    def names(self):
        return Airport.code_table[self.code]

    def contents(self):
        if self.code not in Airport.contents_table or Airport.contents_table[self.code] == None:
            print("couldn't find contents for "+self.code)
            self.update()
        return Airport.contents_table[self.code]

    def update(self, contents=None):
        if contents==None:
            path = Airport.filePath(self.code)
            if os.path.exists(path):
                with open(path, "r") as file:
                    contents = file.read()
            else:
                print(f"Warning: {self.code} not found locally, downloading from Wikipedia")
                contents = Airport.getPage(self.names()[0])
        if contents:
            Airport.contents_table[self.code] = contents
            with open(Airport.filePath(self.code),"w") as file:
                file.write(contents)

    def _parseDestTable(self):
        """Parse the Airport destination list template.

        Returns a list of (airline_name, [dest_names]) tuples where airline_name
        is the Wikipedia page title of the airline (or None if not linked).
        """
        text = re.sub(r'<ref[^>]*/>', '', self.contents())
        text = re.sub(r'<ref[^>]*>.*?<\/ref>', '', text, flags=re.DOTALL)
        text = re.sub(r'\{\{(?:efn|sfn|refn)\b.*?\}\}', '', text, flags=re.DOTALL)
        lines = text.splitlines()

        # Some airport pages use {{Airport destination list}} for more than one table —
        # for example, DCA has one under "Perimeter restrictions" (a slot allocation
        # table with prose in the destination cell) and the real one under "Airlines and
        # destinations". We collect every occurrence and score each by whether its nearest
        # preceding section header mentions airlines or destinations, then pick the
        # best-scoring one (ties broken by last occurrence, so the real table wins when
        # the specialty table appears first and shares the same score).
        def find_relevant_rows(list_start):
            """Extract data rows from a single template starting at list_start."""
            for i in range(list_start + 1, len(lines)):
                # Mask {{...}} using leaf-first repeated passes to handle nesting like
                # {{nowrap|{{cn|...}}}} — matching only leaf templates ([^{}]*) ensures
                # inner templates are removed before outer ones, leaving nothing behind.
                masked_line = lines[i]
                while True:
                    next_mask = re.sub(r'\{\{[^{}]*\}\}', '', masked_line)
                    if next_mask == masked_line:
                        break
                    masked_line = next_mask
                if re.search(r'(?:^(?:<!--.*?>)?\}\}|\}\}\s*$)', masked_line):
                    list_end = i
                    break
            else:
                return []
            candidate = lines[list_start:list_end]
            closing_stripped = re.sub(r'\}\}\s*$', '', lines[list_end]).rstrip()
            if closing_stripped.strip().startswith('|') and closing_stripped.count('|') > 1:
                candidate = candidate + [closing_stripped]
            return [x for x in candidate if x.count("|") > 1
                    and not re.search(r'\{\{\s*(Airport-dest-list|Airport destination list)', x, re.IGNORECASE)
                    and not re.match(r'\s*<br', x)]

        def section_score(list_start):
            """Score based on the nearest preceding top-level (==) section header.

            We intentionally skip subsection headers (===, ====, ...) and only consider
            top-level ones. This matters for airports like ATL, which have both a
            Passenger and a Cargo table under the same top-level "Airlines and
            destinations" section: subsection headers ("=== Passenger ===" and
            "=== Cargo ===") would both score 0, losing the distinction we need.
            By looking at the top-level header we correctly score both as 1.

            Headers containing 'airline' or 'destination' score 1; others score 0.
            """
            for i in range(list_start - 1, -1, -1):
                if re.match(r'==[^=]', lines[i]):  # exactly top-level: == but not ===
                    header = lines[i].lower()
                    return 1 if ('airline' in header or 'destination' in header) else 0
            return 0

        best_score = -1
        relevant = []
        for i, line in enumerate(lines):
            if re.search(r'\{\{\s*(Airport-dest-list|Airport destination list)', line, re.IGNORECASE):
                score = section_score(i)
                if score > best_score:  # strict > so first occurrence wins ties
                    best_score = score  # (e.g. ATL's Passenger table before Cargo)
                    relevant = find_relevant_rows(i)

        rows = []
        for x in relevant:
            s = x.lstrip().lstrip('|')
            masked = re.sub(r'\[\[.*?\]\]', lambda m: '\x00' * len(m.group()), s)
            while True:
                next_mask = re.sub(r'\{\{[^{}]*\}\}', lambda m: '\x00' * len(m.group()), masked)
                if next_mask == masked:
                    break
                masked = next_mask
            split_at = masked.find('|')
            airline_cell = s[:split_at].strip() if split_at >= 0 else s.strip()
            dest_cell = s[split_at + 1:] if split_at >= 0 else ''

            links = re.findall(r'\[\[(.*?)\]\]', airline_cell)
            if links:
                airline_name = links[0].split('|')[0].strip()
            else:
                plain = re.sub(r"'{2,3}", '', airline_cell).strip()
                plain = re.sub(r'<!--.*?-->', '', plain).strip()
                if plain and not re.match(r'\w[\w\s]*=', plain):
                    print(f"Warning: skipping airline '{plain}': not linked in Wikipedia")
                airline_name = None

            dest_names = [link.split('|')[0].strip() for link in re.findall(r'\[\[(.*?)\]\]', dest_cell)]
            rows.append((airline_name, dest_names))
        return rows

    def destinationList(self, airline=None):
        if airline is not None:
            def normalize(n): return n[0].upper() + n[1:]
            def matches(name):
                n = normalize(name)
                return n in airline.names() or Airline.manual_aliases.get(n) == airline.code

        airports = set()
        for airline_name, dest_names in self._parseDestTable():
            if airline is not None and (airline_name is None or not matches(airline_name)):
                continue
            for name in dest_names:
                try:
                    airports.add(Airport(name=name))
                except Exception as e:
                    print(f"Warning: skipping airport '{name}': {e}")
        return airports

    def printDestinationTable(self):
        for line in sorted(self.airlineList(), key=lambda a: a.code):
            print(f"{line}: {','.join(sorted(str(d) for d in self.destinationList(line)))}")

    def region(self):
        match = re.search(r'region:([A-Z]{2}(?:-[A-Z0-9]+)?)', self.contents())
        if match:
            return Region(match.group(1))
        return None

    def airlineList(self):
        airlines = set()
        for airline_name, _ in self._parseDestTable():
            if airline_name is None:
                continue
            try:
                airlines.add(Airline(name=airline_name))
            except Exception as e:
                print(f"Warning: skipping airline '{airline_name}': {e}")
        return airlines
