from entities import ActivityType
from mot import unlimitedNumber
from itertools import groupby
from math import floor, ceil
from itertools import chain

"""
generates a mobility offer instance from the data of the created company
"""

"""
TODO: change the hard coded name mapping  
"""
CAR_TO_INDEX = {'Type.BIKE_Bike': 'n_bikes', 'Type.ICEV_CarSmall': 'car_0', 'Type.ICEV_CarMedium': 'car_1',
                'Type.ICEV_Van': 'car_2', 'Type.BEV_SmartED': 'ecar_0', 'Type.BEV_NissanLeaf': 'ecar_1',
                'Type.BEV_Mitsubishi-iMIEV': 'ecar_2'}

COST_PER_TIME_REDUCTION_PRIVATE = 0.2

motLine = []

"""
Needed for easy initialization of 3d-dictionary (for matrix)
source: https://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries
"""
class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)() # retain local pointer to value
        return value                     # faster to return than dict lookup


class MoTLine (object):
    def __init__(self, id):
        self.id = id
        self.type = "unknown"
        self.nmbAvailable = -1
        self.startIndex = -1

    def toString(self):
        return str(self.id) + " " + self.type + " " + str(self.nmbAvailable) + " " + str(self.startIndex)


class Offer (object):
    def __init__(self, cost = -1, start = -1, end = -1, motIdx = -1):
        self.cost = cost
        self.start = start
        self.end = end
        self.motIdx = motIdx

    def toString(self):
        return str(self.cost) + " " + str(self.start) + " " + str(self.end) + " " + str(self.motIdx)


"""
compute the cost of an offer for a demand derived from events with mot motID based on cost values of matrix
"""
def computeOfferCost(mots, motID, events, matrix):
    cost = 0
    currentEvent = events[0]
    for e in events[1:]:
        cost += matrix[currentEvent["id"]][e["id"]][motID].cost
        # subtract costs per time for private events
        # i.e., only consider (full) time costs (= personel costs) for work -> meeting and meeting -> work events
        timeCostsRelevant = (currentEvent["type"] == ActivityType.work and e["type"] == ActivityType.meeting) or (e["type"] == ActivityType.work and currentEvent["type"] == ActivityType.meeting)
        if not timeCostsRelevant:
            cost -= matrix[currentEvent["id"]][e["id"]][motID].duration_seconds * mots[motID].costPerTime * (1.0 - COST_PER_TIME_REDUCTION_PRIVATE)

        currentEvent = e

    # add setup costs
    # assumption that mots is sorted by id
    setup_costs = mots[motID].overheadDuration * mots[motID].costPerTime
    return setup_costs + cost

"""
compute the start time of an offer for a demand derived from events with mot motID based on cost values of matrix
"""
def computeOfferStart(mots, motID, events, matrix):
    startEvent = events[0]
    firstEvent = events[1]
    travelTime = matrix[startEvent["id"]][firstEvent["id"]][motID].duration_seconds
    start = ceil(firstEvent["latestArrival"] - travelTime / 60.0)
    start -= ceil(mots[motID].overheadDuration / 60.0 / 2.0)
    return start


def computeOfferEnd(mots, motID, events, matrix):
    endEvent = events[-1]
    lastEvent = events[-2]
    travelTime = matrix[lastEvent["id"]][endEvent["id"]][motID].duration_seconds
    end = floor(lastEvent["earliestDeparture"] + travelTime / 60.0)
    end += floor(mots[motID].overheadDuration / 60.0 / 2.0)
    return end


"""
returns a list of offers for the given list of work - work events  
"""
def getOffersFromEvents(events, mots, employee, matrix):

    offers = []
    mot_prefs = employee.mot_preferences

    for m in mot_prefs.to_dict():
        # create offer if user accepts this mot
        if m["accepted"] is True:

            # get nmb offers
            nmbOffers = motLine[m["id"]].__dict__["nmbAvailable"]
            if nmbOffers == unlimitedNumber:
                nmbOffers = 1

            # compute cost
            cost = computeOfferCost(mots, motLine[m["id"]].id, events, matrix)

            # compute start
            start = computeOfferStart(mots, motLine[m["id"]].id, events, matrix)

            # compute end
            end = computeOfferEnd(mots, motLine[m["id"]].id, events, matrix)

            # generate nmbOffers offers for MoT type m
            for i in range(0, nmbOffers):
                # compute mot index
                motIndex =  motLine[m["id"]].__dict__["startIndex"] + i
                o = Offer(cost, start, end, motIndex)
                offers.append(o)

    return offers


def generateMobilityDemands(t, mots, employees, matrix):

    mobilityDemands = []
    t.sort(key=lambda x: (x["assignedUser"], x["latestArrival"]))

    for user, g in groupby(t, lambda x: x["assignedUser"]):
        entry = []
        eventsOfUser = list(g)
        eventsOfUser.sort(key=lambda x: x["latestArrival"])

        nmbWorkEvents = 0
        for event in eventsOfUser:
            mobilityOffers = []
            entry.append(event)

            if event["type"] == ActivityType.work:
                nmbWorkEvents += 1

            if nmbWorkEvents == 2:
                mobilityOffers.extend(getOffersFromEvents(entry, mots, next(x for x in employees if x.id == user), matrix))
                # start with same event again
                entry = [event]
                nmbWorkEvents = 1
                mobilityDemands.append(list(mobilityOffers))

        # add (artificial) final work event - first work event of the following week
        finalEvent = eventsOfUser[0].copy()
        finalEvent["latestArrival"] = finalEvent["latestArrival"] + 7*24*60
        finalEvent["earliestDeparture"] = finalEvent["latestArrival"] + 7*24*60
        entry.append(finalEvent)
        mobilityOffers.extend(getOffersFromEvents(entry, mots, next(x for x in employees if x.id == user), matrix))
        mobilityDemands.append(list(mobilityOffers))

    return mobilityDemands


def createMobilityOfferInstance(company, mots, trips, matrix):
    nmbCars = company.sum_cars() + company.sum_ecars()
    nmbMots = len(mots)

    mots.sort(key=lambda x: x.id)

    index = 0
    for mot in mots:

        m = MoTLine(mot.id)
        m.type = str(mot.type) + "_" + str(mot.name)
        m.nmbAvailable = mot.nmbVehicles

        if CAR_TO_INDEX.get(m.type) is not None:
            m.nmbAvailable = company.fleet.to_dict()[CAR_TO_INDEX[m.type]]

        m.startIndex = index
        motLine.append(m)

        if m.nmbAvailable == unlimitedNumber:
            index += 1
        else:
            index += m.nmbAvailable

    # prepare matrix
    prepMatrix = Vividict()
    for row in matrix.move_options:
        prepMatrix[row.fromNode][row.toNode][row.modeOfTransport] = row

    mobilityDemands = generateMobilityDemands(trips, mots, company.employees, prepMatrix)

    nmbDemands = len(mobilityDemands)
    nmbOffers = len(list(chain.from_iterable(mobilityDemands)))

    mobilityOfferInstance = [str(nmbCars) + " " + str(nmbDemands) + " " + str(nmbOffers) + " " + str(nmbMots) + "\n"]
    for m in motLine:
        mobilityOfferInstance.append(m.toString() + "\n")

    for d in mobilityDemands:
        mobilityOfferInstance.append(str(len(d)) + " ")
        for o in d:
            mobilityOfferInstance.append(o.toString() + " ")
        mobilityOfferInstance.append("\n")

    return ''.join(mobilityOfferInstance)