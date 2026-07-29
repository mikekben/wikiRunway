import argparse
from .airport import Airport
from .airline import Airline
from .fetch import do_update, do_update_batch


def run_verify(current):
    """Run one verify pass. Returns list of (airline, other) pairs that are asymmetric."""
    asymmetric = []
    for airline in current.airlineList():
        for other in current.destinationList(airline):
            if current not in other.destinationList(airline):
                asymmetric.append((airline, other))
    return sorted(asymmetric, key=lambda x: (x[0].code, x[1].code))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--dtable", metavar="CODE",
                        help="Print the destination table for the given airport IATA code")
    parser.add_argument("-v", "--verify", metavar="CODE",
                        help="Verify two-directionality of all routes departing from the given airport")
    parser.add_argument("-vu", "--verify-update", metavar="CODE",
                        help="Like --verify, but fetches and updates asymmetric airports then re-runs")
    parser.add_argument("-r", "--region", metavar="CODE",
                        help="Print the ISO 3166 region of the given airport IATA code")
    parser.add_argument("-ar", "--all-airports", metavar="REGION",
                        help="List all airports in the given ISO 3166 region code")
    parser.add_argument("-aa", "--airline-airports", nargs=2, metavar=("AIRLINE", "SEED"),
                        help="List all airports served by AIRLINE, found via BFS starting from SEED airport IATA code")
    parser.add_argument("-ad", "--airline-dests", nargs=2, metavar=("AIRPORT", "AIRLINE"),
                        help="List all destinations AIRLINE flies from AIRPORT")
    parser.add_argument("-arb", "--airline-routes-both", nargs=2, metavar=("AIRLINE", "SEED"),
                        help="List all routes flown by AIRLINE as ORIGIN-DEST pairs, including both directions")
    parser.add_argument("-aro", "--airline-routes-oneway", nargs=2, metavar=("AIRLINE", "SEED"),
                        help="List all routes flown by AIRLINE as ORIGIN-DEST pairs, collapsing each pair to one direction")
    parser.add_argument("-arc", "--airline-route-counts", nargs=2, metavar=("AIRLINE", "SEED"),
                        help="List AIRLINE's airports sorted by number of destinations served from each")
    args = parser.parse_args()


    # dl_hubs = [Airport(x) for x in ["ATL", "BOS", "DTW", "JFK", "LAX", "LGA", "MSP", "SEA", "SLC"]]

    # ua_hubs = [Airport(x) for x in ["EWR", "IAD", "ORD", "IAH", "DEN", "SFO", "LAX"]]

    # hubs = [Airport(x) for x in ["LGA", "JFK", "PHL", "DCA", "CLT", "MIA", "DFW", "ORD", "PHX", "LAX"]]

    # airline = Airline("AA")

    # dests = set().union(*[ap.destinationList(airline) for ap in hubs])

    # dests = {x : [1 if x in ap.destinationList(airline) else 0 for ap in hubs] for x in dests}

    # for dest, vals in dests.items():
    #     if sum(vals) == len(hubs):
    #         print(dest)
    #     if sum(vals) == len(hubs)-1 and dest not in hubs:
    #         other = hubs[vals.index(0)]
    #         print(f"{dest.code} (missing {other.code})")

    # exit()
        

    if args.region:
        code = args.region.upper()
        region = Airport(code).region()
        if region:
            print(region.code)
        else:
            print(f"No region found for {code}")

    if args.all_airports:
        from .region import Region
        for code in Region(args.all_airports.upper()).allAirports():
            print(code)

    if args.airline_airports:
        airline_code, seed_code = args.airline_airports
        airline = Airline(airline_code.upper())
        seed = Airport(seed_code.upper())
        print(",".join(sorted(a.code for a in airline.airportList(seed))))

    if args.airline_dests:
        airport_code, airline_code = args.airline_dests
        airport = Airport(airport_code.upper())
        airline = Airline(airline_code.upper())
        print(",".join(sorted(a.code for a in airport.destinationList(airline))))

    if args.airline_routes_both:
        airline_code, seed_code = args.airline_routes_both
        airline = Airline(airline_code.upper())
        seed = Airport(seed_code.upper())
        routes = sorted(airline.routes(seed))
        print(",".join(f"{o}-{d}" for o, d in routes))

    if args.airline_routes_oneway:
        airline_code, seed_code = args.airline_routes_oneway
        airline = Airline(airline_code.upper())
        seed = Airport(seed_code.upper())
        seen = set()
        oneway = []
        for o, d in sorted(airline.routes(seed)):
            pair = frozenset((o, d))
            if pair in seen:
                continue
            seen.add(pair)
            oneway.append(f"{o}-{d}")
        print(",".join(oneway))

    if args.airline_route_counts:
        airline_code, seed_code = args.airline_route_counts
        airline = Airline(airline_code.upper())
        seed = Airport(seed_code.upper())
        counts = airline.airportsByRouteCount(seed)
        for ap, n in counts:
            print(f"{ap.code}:{n}")

    if args.dtable:
        code = args.dtable.upper()
        print(f"---{code}---")
        Airport(code).printDestinationTable()
        print("-------")

    if args.verify:
        current = Airport(args.verify.upper())
        for airline, other in run_verify(current):
            print(f"Warning: {airline} has {current}-{other} but not {other}-{current}")

    if args.verify_update:
        code = args.verify_update.upper()
        # Update the passed airport first so verify runs against its latest data,
        # catching any new destinations introduced by the update.
        do_update(code, replace=False)
        Airport.code_table.clear()
        Airport.name_table.clear()
        Airport.contents_table.clear()
        Airline.code_table.clear()
        Airline.name_table.clear()
        current = Airport(code)
        asymmetric = run_verify(current)
        if asymmetric:
            other_codes = sorted({other.code for _, other in asymmetric})
            print(f"\nFetching {len(other_codes)} asymmetric airport(s)...")
            do_update_batch(other_codes, replace=False)
            Airport.code_table.clear()
            Airport.name_table.clear()
            Airport.contents_table.clear()
            Airline.code_table.clear()
            Airline.name_table.clear()
            print(f"\n--- Re-running verify after updates ---\n")
            current = Airport(code)
            for airline, other in run_verify(current):
                print(f"Warning: {airline} has {current}-{other} but not {other}-{current}")




if __name__ == "__main__":
    main()
