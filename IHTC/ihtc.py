from pycsp3 import *
import sys
import json

# ==========================================
# Data import
# ==========================================
data_file = None
for arg in sys.argv:
    if arg.startswith("-mydata="):
        data_file = arg.split("=")[1]
        break

if data_file is None:
    print("Erreur : Veuillez spécifier un fichier JSON avec -mydata=votre_fichier.json")
    sys.exit(1)

with open(data_file, 'r', encoding='utf-8') as file:
    instance = json.load(file)

D = instance.get("days", 14)
patients_data = instance.get("patients", [])
rooms_data = instance.get("rooms", [])
surgeons_data = instance.get("surgeons", [])
ots_data = instance.get("operating_theaters", [])

nb_patients = len(patients_data)
nb_rooms = len(rooms_data)
nb_ots = len(ots_data)
nb_surgeons = len(surgeons_data)

room_idx = {r["id"]: i for i, r in enumerate(rooms_data)}
surgeon_idx = {s["id"]: i for i, s in enumerate(surgeons_data)}
ot_idx = {o["id"]: i for i, o in enumerate(ots_data)}

# ==========================================
# DECISION VAR
# ==========================================
x_admitted = VarArray(size=nb_patients, dom={0, 1})
x_day = VarArray(size=[nb_patients, D], dom={0, 1})
x_room = VarArray(size=[nb_patients, nb_rooms], dom={0, 1})
x_ot = VarArray(size=[nb_patients, nb_ots], dom={0, 1})

# ==========================================
# CONSTRAINTS
# ==========================================
for i, p in enumerate(patients_data):
    satisfy(Sum(x_day[i]) == x_admitted[i])
    satisfy(Sum(x_room[i]) == x_admitted[i])
    satisfy(Sum(x_ot[i]) == x_admitted[i])
    
    if p.get("mandatory", False):
        satisfy(x_admitted[i] == 1)
        
    incompatible_rooms = p.get("incompatible_room_ids", [])
    for r_id in incompatible_rooms:
        if r_id in room_idx:
            satisfy(x_room[i][room_idx[r_id]] == 0)

for d in range(D):
    for r_index, r in enumerate(rooms_data):
        all_presents = []
        males_presents = []
        females_presents = []
        
        for i, p in enumerate(patients_data):
            los = p.get("length_of_stay", 1)
            first_day = max(0, d - los + 1)
            
            for start in range(first_day, d + 1):
                presence = x_day[i][start] * x_room[i][r_index]
                all_presents.append(presence)
                
                gender = p.get("gender", "A") 
                if gender in ["A", "M"]:
                    males_presents.append(presence)
                else:
                    females_presents.append(presence)
                    
        if len(all_presents) > 0:
            satisfy(Sum(all_presents) <= r.get("capacity", 1))
        
        if len(males_presents) > 0 and len(females_presents) > 0:
            satisfy((Sum(males_presents) == 0) | (Sum(females_presents) == 0))

for d in range(D):
    for o_idx, o in enumerate(ots_data):
        capa = o.get("availability", [480]*D)[d]
        satisfy(
            Sum(x_day[i][d] * x_ot[i][o_idx] * patients_data[i].get("surgery_duration", 0) for i in range(nb_patients)) <= capa
        )
        
    for s_idx, s in enumerate(surgeons_data):
        capa = s.get("max_surgery_time", [480]*D)[d]
        satisfy(
            Sum(x_day[i][d] * patients_data[i].get("surgery_duration", 0) 
                for i in range(nb_patients) 
                if surgeon_idx.get(patients_data[i].get("surgeon_id")) == s_idx
               ) <= capa
        )

# S8
unplanned_optionals = [
    (1 - x_admitted[i]) for i, p in enumerate(patients_data) if not p.get("mandatory", False)
]
minimize(Sum(unplanned_optionals))

status = solve(options="-t=10s -rr")
