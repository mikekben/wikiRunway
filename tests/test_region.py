import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.airport import Airport


# (IATA, expected_country, expected_subdivision)
# expected_subdivision is only asserted when not None
REGION_CASES = [
    ("ORD", "US", "IL"),
    ("LHR", "GB", "HIL"),
    ("GUA", "GT", None),
    ("LJU", "SI", None),
    ("PVG", "CN", "31"),
    ("SYD", "AU", "NSW"),
    ("BOM", "IN", None),
    ("JNB", "ZA", "GP"),
    ("EZE", "AR", None),
]


def test_regions():
    for iata, expected_country, expected_subdivision in REGION_CASES:
        r = Airport(iata).region()
        assert r is not None, f"{iata}: expected region, got None"
        assert r.country == expected_country, f"{iata}: expected country {expected_country}, got {r.country}"
        if expected_subdivision is not None:
            assert r.subdivision == expected_subdivision, f"{iata}: expected subdivision {expected_subdivision}, got {r.subdivision}"
