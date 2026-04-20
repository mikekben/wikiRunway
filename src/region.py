class Region:
    def __init__(self, code):
        self.code = code

    @property
    def country(self):
        return self.code.split("-")[0]

    @property
    def subdivision(self):
        parts = self.code.split("-", 1)
        return parts[1] if len(parts) > 1 else None
