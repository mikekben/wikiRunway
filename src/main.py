import argparse
from .airport import Airport
from .airline import Airline
from .fetch import do_update


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
        current = Airport(code)
        asymmetric = run_verify(current)
        if asymmetric:
            other_codes = sorted({other.code for _, other in asymmetric})
            print(f"\nFetching {len(other_codes)} asymmetric airport(s)...")
            for ap_code in other_codes:
                do_update(ap_code, replace=False)
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
