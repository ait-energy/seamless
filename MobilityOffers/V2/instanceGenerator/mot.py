# -*- coding: utf-8 -*-


from random import randint
from itertools import count
from enum import Enum


""" Defines a range of integers in order to generate uniformly distributed random integers within that range (inclusive) """
class RandomRange(object):

    def __init__(self, min, max):
        self.min = int(min)
        self.max = int(max)

    def __str__(self):
        return "U[" + str(self.min) + "," + str(self.max) + "]"

    def get(self):
        return randint(self.min, self.max)

    def __repr__(self):
        return self.__str__()


def euroPerHour2CentsPerSecond(value):
    return value * 100 / 3600


def kilometerPerHour2MeterPerSecond(value):
    return value / 3.6


def days2Seconds(days):
    return days * 3600 * 10


def minutes2Seconds(days):
    return days * 60


def euroPerKm2centsPerMeter(value):
    return value * 100 / 1000


def kwHPerKm2kwHPerMeter(value):
    return value / 1000


salaryInCentsPerSecond = euroPerHour2CentsPerSecond(19.42)
durationOfPlanningHorizonInSeconds = days2Seconds(1)
fixedCostReferenceDuration = days2Seconds(265)
fixedCostCorrectionFactor = durationOfPlanningHorizonInSeconds / fixedCostReferenceDuration
unlimitedNumber = 1000000  # used where a number (e.g. of vehicles) should be unlimited
costPerUnitOfEmission = 500 / (1000 * 1000)  # 5€ per tonne -> cents per gram


class Type(Enum):
    ICEV = "ICEV"  # internal combustion engine vehicle
    BEV = "BEV"    # battery electric vehicle"
    HEV = "HEV"    # hybrid electric vehicle"
    PHEV = "PHEV"  # Plug-in hybrid electric vehicle"
    BIKE = "Bike"
    FOOT = "Pedestrian"
    PT = "PublicTransport"
    TAXI = "Taxi"


mot_mapping = {
    "car" : [Type.ICEV],
    "ecar": [Type.BEV],
    "bike": [Type.BIKE],
    "foot": [Type.FOOT],
    "pt"  : [Type.PT],
    "taxi": [Type.TAXI],
}


class ModeOfTransport (object):
    def __init__(self, id):
        self.id = id
        self.name = "default"
        self.type = "unknown"
        self.nmbVehicles = -1
        self.personCapacity = -1
        self.slopingFactor = -1
        self.overheadDuration = -1
        self.fixedCost = -1
        self.energyConsumptionPerDistance = -1
        self.costPerDistance = -1
        self.costPerTime = -1
        self.durationPerDistance = -1
        self.emissionsPerDistance = -1
        self.batteryCapacity = -1
        self.inverseRechargingSpeed = -1
        self.rechargingCostRange = RandomRange(-1, -1)
        self.reachabilityProbability = 100

    def to_dict(self):
        d = vars(self).copy()
        d["type"] = str(self.type)
        d["rechargingCostRange"] = str(self.rechargingCostRange)
        return d


class MoTManager(object):
    def __init__(self):
        self.mots = {}
        for m in _create_mots_list():
            self.add(m)

    def to_list(self):
        res = []
        for x in self.mots.values():
            for y in x:
                res.append(y)
        return res

    def add(self, mot):
        if mot.type not in self.mots:
            self.mots[mot.type] = []
        self.mots[mot.type].append(mot)

    def get_mots(self, type):
        m = mot_mapping.get(type)
        selected_mots = []
        if m:
            for x in m:
                selected_mots.extend(self.mots.get(x))
        return selected_mots

    def to_dict(self):
        res = []
        for x in self.to_list():
            res.append(x.to_dict())
        return res


def _create_mots_list():
    mots = []
    unique_id = count(start=0)

    m = ModeOfTransport(next(unique_id))
    m.name = "Pedestrian"
    m.type = Type.FOOT
    m.nmbVehicles = unlimitedNumber
    m.personCapacity = 1
    m.overheadDuration = minutes2Seconds(0)
    m.slopingFactor = 1.1
    m.fixedCost = 0 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = 0
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(5)
    m.emissionsPerDistance = 0
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "Bike"
    m.type = Type.BIKE
    m.nmbVehicles = 10
    m.personCapacity = 1
    m.overheadDuration = minutes2Seconds(2)
    m.slopingFactor = 1.3
    m.fixedCost = 58 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = 0
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(16)
    m.emissionsPerDistance = 0
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "CarSmall"
    m.type = Type.ICEV
    m.nmbVehicles = 10
    m.personCapacity = 2
    m.overheadDuration = minutes2Seconds(10)
    m.slopingFactor = 1.3
    m.fixedCost = 1800 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = euroPerKm2centsPerMeter(0.116)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 153.3 / 1000
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "CarMedium"
    m.type = Type.ICEV
    m.nmbVehicles = 4
    m.personCapacity = 4
    m.overheadDuration = minutes2Seconds(10)
    m.slopingFactor = 1.3
    m.fixedCost = 3420 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = euroPerKm2centsPerMeter(0.188)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 200.9 / 1000
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "Van"
    m.type = Type.ICEV
    m.nmbVehicles = 1
    m.personCapacity = 8
    m.overheadDuration = minutes2Seconds(10)
    m.slopingFactor = 1.3
    m.fixedCost = 5220 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = euroPerKm2centsPerMeter(0.292)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 356 / 1000
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "SmartED"
    m.type = Type.BEV
    m.nmbVehicles = 2
    m.personCapacity = 2
    m.overheadDuration = minutes2Seconds(10)
    m.slopingFactor = 1.3
    m.fixedCost = 2590 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = kwHPerKm2kwHPerMeter(0.2)
    m.costPerDistance = euroPerKm2centsPerMeter(0.082)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 31.9 / 1000
    m.batteryCapacity = 17.6
    m.inverseRechargingSpeed = 204.6
    m.rechargingCostRange = RandomRange(15, 25) #cent per kwH
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "NissanLeaf"
    m.type = Type.BEV
    m.overheadDuration = minutes2Seconds(10)
    m.nmbVehicles = 4
    m.personCapacity = 4
    m.slopingFactor = 1.3
    m.fixedCost = 3756 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = kwHPerKm2kwHPerMeter(0.22)
    m.costPerDistance = euroPerKm2centsPerMeter(0.094)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 42.7 / 1000
    m.batteryCapacity = 24
    m.inverseRechargingSpeed = 93.6
    m.rechargingCostRange = RandomRange(15, 25) #cent per kwH
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "Mitsubishi-iMIEV"
    m.type = Type.BEV
    m.nmbVehicles = 2
    m.personCapacity = 4
    m.overheadDuration = minutes2Seconds(10)
    m.slopingFactor = 1.3
    m.fixedCost = 3108 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = kwHPerKm2kwHPerMeter(0.2)
    m.costPerDistance = euroPerKm2centsPerMeter(0.082)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 31.9 / 1000
    m.batteryCapacity = 16
    m.inverseRechargingSpeed = 120
    m.rechargingCostRange = RandomRange(15, 25) #cent per kwH
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "PublicTransport"
    m.type = Type.PT
    m.nmbVehicles = unlimitedNumber
    m.personCapacity = 1
    m.overheadDuration = minutes2Seconds(5)
    m.slopingFactor = 1.5
    m.fixedCost = 365 * fixedCostCorrectionFactor
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = 0
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(20)
    m.emissionsPerDistance = 0
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)

    m = ModeOfTransport(next(unique_id))
    m.name = "Taxi"
    m.type = Type.TAXI
    m.nmbVehicles = unlimitedNumber
    m.personCapacity = 3
    m.overheadDuration = minutes2Seconds(5)
    m.slopingFactor = 1.3
    m.fixedCost = 0
    m.energyConsumptionPerDistance = 0
    m.costPerDistance = euroPerKm2centsPerMeter(1.20)
    m.costPerTime = salaryInCentsPerSecond
    m.durationPerDistance = 1 / kilometerPerHour2MeterPerSecond(30)
    m.emissionsPerDistance = 200.9 / 1000
    m.batteryCapacity = 0
    m.inverseRechargingSpeed = 0
    m.rechargingCostRange = RandomRange(0, 0)
    m.reachabilityProbability = 100
    mots.append(m)
    return mots


class Singleton:
    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state

MoT = Singleton()
MoT.manager = MoTManager()
