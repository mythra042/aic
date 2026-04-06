"""Frequency Allocation - OPL Section 2 model translated to PyCSP3.

Original structure (Figure 1 in the paper):
- one variable per transmitter,
- intra-cell distance constraints,
- inter-cell distance constraints.

Added objective for the project requirement:
- minimize the number of distinct frequencies used.
"""

from itertools import combinations, product
import argparse
import json
import sys

from pycsp3 import *


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--time-limit", type=int, default=15)
args, _ = parser.parse_known_args(sys.argv[1:])


with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

nb_cells = data["nbCells"]
nb_freqs = data["nbFreqs"]
nb_trans = data["nbTrans"]
distance = data["distance"]

transmitters = [(c, t) for c in range(nb_cells) for t in range(nb_trans[c])]
id = {(c, t): i for i, (c, t) in enumerate(transmitters)}

# OPL: var Freqs freq[Transmits], with Freqs = 1..nbFreqs
freq = VarArray(size=len(transmitters), dom=range(1, nb_freqs + 1))


satisfy(
    # intra-cell
    [abs(freq[id[c, t1]] - freq[id[c, t2]]) >= 16
     for c in range(nb_cells)
     for t1, t2 in combinations(range(nb_trans[c]), 2)],

    # inter-cell
    [abs(freq[id[c1, t1]] - freq[id[c2, t2]]) >= distance[c1][c2]
     for c1, c2 in combinations(range(nb_cells), 2)
     if distance[c1][c2] > 0
     for t1, t2 in product(range(nb_trans[c1]), range(nb_trans[c2]))],

    # symmetry breaking
     [    freq[id[c, t]] < freq[id[c, t + 1]]
    for c in range(nb_cells)
    for t in range(nb_trans[c] - 1)],
    Minimum(freq) == 1
)
# we want to minimize the number of distinct frequencies used as asked in the project requirement
minimize(NValues(freq)) 

# Ace
instance = compile()
ace = solver(ACE)
dict_simplified = dict()
if args.time_limit > 0:
    dict_simplified["limit_time"] = str(args.time_limit)

print(f"generating with ACE solver log... ({args.time_limit} seconds time limit)")
# Solve and get the status
result = ace.solve(instance,
                  dict_simplified_options=dict_simplified)

if result is SAT:
    print("ACE solver log generated")
    frequencies = values(freq)
    print("SAT")
    print("Number of distinct frequencies :", len(set(frequencies)))
    print("frequencies =", frequencies)
elif result is UNSAT:
    print("ACE solver log generated")
    print("UNSAT")
else:
    print("error")