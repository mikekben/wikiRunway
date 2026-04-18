import requests
import re
import os
import json

from .config import AIRLINES_DIR, AIRLINES_LIST, AIRLINES_MANUAL_ALIASES

_request_count = 0
_REQUEST_LIMIT = 100


class Airline:
    NAME_TABLE_PATH = AIRLINES_LIST
    MANUAL_ALIASES_PATH = AIRLINES_MANUAL_ALIASES
    CONTENTS_PATH = AIRLINES_DIR
    name_table = {}     # name -> IATA
    code_table = {}     # IATA -> [names]
    contents_table = {}
    manual_aliases = {}  # name -> IATA (hand-curated overrides)

    def filePath(code):
        return os.path.join(Airline.CONTENTS_PATH, code + ".txt")

    def getPage(title):
        global _request_count
        if _request_count > _REQUEST_LIMIT:
            raise Exception("Request limit exceeded")
        print("Doing request: "+title)
        response = requests.get(f"https://en.wikipedia.org/w/index.php?title={title}&action=raw")
        _request_count += 1
        if response.status_code == 200:
            if '#REDIRECT' in response.text:
                return Airline.getPage(re.findall(r'\[\[(.*?)\]\]',response.text)[0])
            return response.text
        else:
            return None

    def extractIATA(text):
        match = re.search(r'\|\s*IATA\s*=\s*([A-Z0-9]{2})', text)
        return match.group(1) if match else None

    def addToTable(code, name, contents=None):
        changed = False
        if code not in Airline.code_table:
            Airline.code_table[code] = [name]
            Airline.name_table[name] = code
            changed = True
        elif name not in Airline.code_table[code]:
            Airline.code_table[code].append(name)
            Airline.name_table[name] = code
            changed = True
        if changed:
            with open(Airline.NAME_TABLE_PATH, "w") as f:
                json.dump(Airline.code_table, f, ensure_ascii=False, indent=2)
        if contents is not None:
            Airline.contents_table[code] = contents

    def __str__(self):
        return self.code

    def __hash__(self):
        return self.code.__hash__()

    def __eq__(self, other):
        return self.code.__eq__(other.code)

    def __init__(self, code=None, name=None):
        if not Airline.code_table:
            with open(Airline.NAME_TABLE_PATH, "r") as f:
                data = json.load(f)
            for iata, names in data.items():
                Airline.code_table[iata] = names
                for n in names:
                    Airline.name_table[n] = iata
            if os.path.exists(Airline.MANUAL_ALIASES_PATH):
                with open(Airline.MANUAL_ALIASES_PATH, "r") as f:
                    Airline.manual_aliases = json.load(f)

        if not Airline.contents_table:
            for kk in Airline.code_table.keys():
                if os.path.exists(Airline.filePath(kk)):
                    with open(Airline.filePath(kk), "r") as file:
                        Airline.contents_table[kk] = file.read()
                else:
                    Airline.contents_table[kk] = None

        if code == None and name == None:
            raise Exception("Either the code, the name, or both must be provided")
        if name is not None:
            name = name[0].upper() + name[1:]
        if name == None:
            self.code = code
            if self.code not in Airline.code_table:
                raise Exception("Input code is not in the database and no name is provided")
            elif self.code not in Airline.contents_table:
                self.update()
        elif code == None:
            if name in Airline.name_table:
                self.code = Airline.name_table[name]
            elif name in Airline.manual_aliases:
                self.code = Airline.manual_aliases[name]
            else:
                contents = Airline.getPage(name)
                if contents is None:
                    raise Exception(f"Could not retrieve page for '{name}'")
                self.code = Airline.extractIATA(contents)
                if self.code is None:
                    raise Exception(f"No IATA code found in page for '{name}'")
                Airline.addToTable(self.code, name, contents)

            if self.code not in Airline.contents_table or Airline.contents_table[self.code] == None:
                self.update()
        else:
            self.code = code
            Airline.addToTable(self.code, name)
            if self.code not in Airline.contents_table or Airline.contents_table[self.code] == None:
                self.update()

    def names(self):
        return Airline.code_table[self.code]

    def contents(self):
        if self.code not in Airline.contents_table or Airline.contents_table[self.code] == None:
            print("couldn't find contents for "+self.code)
            self.update()
        return Airline.contents_table[self.code]

    def update(self, contents=None):
        if contents == None:
            path = Airline.filePath(self.code)
            if os.path.exists(path):
                with open(path, "r") as file:
                    contents = file.read()
            else:
                print(f"Warning: {self.code} not found locally, downloading from Wikipedia")
                contents = Airline.getPage(self.names()[0])
        if contents:
            Airline.contents_table[self.code] = contents
            with open(Airline.filePath(self.code), "w") as file:
                file.write(contents)
