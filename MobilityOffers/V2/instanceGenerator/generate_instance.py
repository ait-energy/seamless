from entities import create_company
from distancematrix import DistanceMatrix, MoT
from numpy.random import choice
from i_utils import to_date
from mobilityOfferGenerator import createMobilityOfferInstance
import os
import csv
import json
import logging
import sys


"""
- the instance starts with each employee at her office location.
- employees are uniformly distributed over all office locations.
"""

NUMBER_OF_EMPLOYEES = choice(range(10, 500))
# read number of employees as first parameter
if len(sys.argv) > 1:
    NUMBER_OF_EMPLOYEES = int(sys.argv[1])

INSTANCE_NUMBER = 0
if len(sys.argv) > 2:
    INSTANCE_NUMBER = int(sys.argv[2])

print(sys.argv)

OFFICES = 2

INSTANCE_DIRECTORY = "./instances/E" + str(NUMBER_OF_EMPLOYEES) + "_" + str(INSTANCE_NUMBER)

logfile = os.path.join(INSTANCE_DIRECTORY, "instancegeneration.log")
log_format= "%(asctime)-15s %(levelname)s\t(%(filename)s:%(lineno)d) -  %(message)s"


def ensure_empty_target_dir_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
    for dirpath, dirnames, files in os.walk(dir):
        if files:
            raise Exception("Directory '" + dir + "' must be empty")


def prepare_mot_preferences(employees):
    d = []
    for e in employees:
        for m in e.mot_preferences.to_dict():
            d.append({"isChosen": m["accepted"], "motIndex": m["id"], "userIndex": e.id})
    return d


def prepare_trips(employees, matrix):
    d = []
    for e in employees:
        logging.info(e.to_dict())

        for w in e.schedule.get():
            node = matrix.get_node(w.loc)
            dur = w.end-w.begin
            d.append(entry(e.id, w.loc, node.lon(), node.lat(), w.activity, w.begin, w.end, dur))
            logging.info("\t{:} {:} - {:} dur {:}h loc {:} ".format(w.activity.value[:4], to_date(w.begin), to_date(w.end), dur/60, w.loc))
    return d


def entry(i, h, lon, lat, t, arr, dep, dur):
    return {"assignedUser": i, "id": h, "coordinateX": lon, "coordinateY": lat, "type": t,
            "earliestDeparture": dep, "latestArrival": arr, "serviceDuration": dur}


def write_csv(fn, list, sep=";"):
    filename = os.path.join(INSTANCE_DIRECTORY, fn+".csv")

    if not type(list[0]) is dict:
        list = [d.to_dict() for d in list]

    header = [x for x in list[0].keys()]

    with open(filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, delimiter=sep)

        writer.writeheader()
        for entry in list:
            assert type(entry) == dict
            writer.writerow(entry)


def write_json(fn, d, indent=0):
    filename = os.path.join(INSTANCE_DIRECTORY, fn+".json")

    if type(d) is list:
        data = [x.to_dict() for x in d]
        indent = 2
    else:
        data = d.to_dict()

    with open(filename, 'w') as jsonfile:
        jsonfile.write(json.dumps(data, indent=indent))


def write_mobilityOfferInstance(fn, d, indent=0):
    filename = os.path.join(INSTANCE_DIRECTORY, fn)
    data = d
    with open(filename, 'w') as file:
        file.write(data)


try:
    ensure_empty_target_dir_exists(INSTANCE_DIRECTORY)
    logging.basicConfig(filename=logfile, level=20, format=log_format)
except Exception as e:
    print(e)


matrix = DistanceMatrix()
company = create_company(NUMBER_OF_EMPLOYEES, car_types=3, ecar_types=3, offices=OFFICES)
trips = prepare_trips(company.employees, matrix)

mobilityOfferInstance = createMobilityOfferInstance(company, MoT.manager.to_list(), trips, matrix)

#write_csv("moveOptions", matrix.move_options)
#write_csv("motDependentNodeInfos", prepare_mot_preferences(company.employees))
#write_csv("nodes", trips)
#write_json("mots", MoT.manager.to_list())
#write_json("employees", company.employees)
#write_json("company", company)
write_mobilityOfferInstance("E" + str(NUMBER_OF_EMPLOYEES) + "_C0.15_" + str(INSTANCE_NUMBER) + ".mo.input", mobilityOfferInstance)