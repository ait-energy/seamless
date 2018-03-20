from enum import Enum
from random import randint
import copy
import locale
import math
import os


INSTANCE_DIRECTORY = "./instances"
INSTANCE_FILE_ENDING = ".mo.input"

TIME_HORIZON = 24 * 7 * 4 # horizon for order creation dates (away periods can be afterwards)


def run():
    ensurePathExistsAndEmpty(INSTANCE_DIRECTORY)
    gen = Generator()
    for gen.nmbDemands in [200, 1000, 2000, 5000 ]:
        for gen.longDurationProbability in [ 1, 2, 5 ]:
            for fleetUtilization in [ 20, 40, 60, 80 ]:
                expectedOverallVehicleUsageDuration = gen.getAverageAwayPeriodDuration() * gen.nmbDemands
                extendedTimeHorizon = TIME_HORIZON + gen.twStartRange.max + gen.longDurationRange.max
                minNmbVehiclesIfUtilizationIsMaximal = expectedOverallVehicleUsageDuration / extendedTimeHorizon
                gen.nmbVehicles = minNmbVehiclesIfUtilizationIsMaximal * 100 / fleetUtilization
                for gen.vehicleUsageProbability in [ 40, 60, 80 ]:
                    instanceName = "d" + str(gen.nmbDemands) + "l" + str(gen.longDurationProbability) + "f" + str(fleetUtilization) + "p" + str(gen.vehicleUsageProbability)
                    filename = os.path.join(INSTANCE_DIRECTORY, instanceName + INSTANCE_FILE_ENDING)
                    gen.generate(filename)


class Generator():
    def __init__(self):
        self.vehicleTypes = []
        self.vehicleTypes.append(VehicleType().withCostFactor(2).withPercentageOfFleet(15)) # small car
        self.vehicleTypes.append(VehicleType().withCostFactor(3).withPercentageOfFleet(35)) # medium car
        self.vehicleTypes.append(VehicleType().withCostFactor(4).withPercentageOfFleet(35)) # large car
        self.vehicleTypes.append(VehicleType().withCostFactor(7).withPercentageOfFleet(15)) # bus

        self.nmbAwayPeriodsRange = RandomRange(1, 3)
        self.demandCreationRange = RandomRange(0, TIME_HORIZON) # range for generating demand creation dates
        self.twStartRange = UniqueRandomRange(2, 24 * 7) # time between demand creation date and beginning of away period

        self.shortDurationRange = RandomRange(1, 6)
        self.longDurationRange = RandomRange(7, TIME_HORIZON)

        # extra duration prolonging the away period (at beginning and end), independently for each vehicle type
        self.extraDurationRange = RandomRange(0, 2)

        self.costPerTimeRange = RandomRange(10, 30)
        self.vehicleUsageProbabilityOfNonPreferredVehicleType = 20

        # maximum time between due date and beginning of away period (but not before creation date)
        self.twDueDateRangeMaxVehicle = 12

        # A (public transport like)
        self.probabilityNonVehicleA = 50
        self.twDueDateRangeMaxNonVehicleA = 24 * 2
        self.relativeCostOfNonVehicleA = RandomRange(100, 300) # in percent of the cost for the minimum vehicle type

        # B (taxi like)
        self.probabilityNonVehicleB = 100
        self.twDueDateRangeMaxNonVehicleB = 4
        self.relativeCostOfNonVehicleB = RandomRange(300, 600) # in percent of the cost for the minimum vehicle type

        self.probabilityRange = RandomRange(0, 100)

    def getAverageAwayPeriodDuration(self):
        shortDurationProbability = 100 - self.longDurationProbability
        shortPart = self.shortDurationRange.getExpectedValue() * shortDurationProbability
        longPart = self.longDurationRange.getExpectedValue() * self.longDurationProbability
        return (shortPart + longPart) / 100

    def getRandomDuration(self):
        if (self.probabilityRange.get() <= self.longDurationProbability):
            return self.longDurationRange.get()
        return self.shortDurationRange.get()

    def getRandomVehicleTypeIndex(self):
        sum = 0
        for v in self.vehicleTypes:
            sum += v.percentageOfFleet
        r = RandomRange(0, sum).get()
        sum = 0
        for i in range(0, len(self.vehicleTypes)):
            sum += self.vehicleTypes[i].percentageOfFleet
            if (sum >= r):
                return i
        raise GeneratorException("Error in getRandomVehicleTypeIndex")

    def generate(self, filename):
        """ Generates a file containing one instance. """

        # compute vehicle indices for vehicle types
        currentVehicleIndex = 0
        for v in self.vehicleTypes:
            v.initialVehicleIndex = currentVehicleIndex
            v.nmbVehicles = math.ceil(self.nmbVehicles * v.percentageOfFleet / 100)
            currentVehicleIndex = currentVehicleIndex + v.nmbVehicles

        f = open(filename, 'w')
        f.write(str(currentVehicleIndex) + " " + str(self.nmbDemands) + "\n")
        for i in range(self.nmbDemands):
            f.write(" ".join(self.createRandomDemand()) + "\n")

    def createRandomDemand(self):
        """ Yields one mobility demand including its mobility offers as
            a sequence of strings to be printed in one line
            according to the file format description.
        """
        offers = []
        demandCreationDate = self.demandCreationRange.get()
        baseDuration = self.getRandomDuration()
        baseCostFactor = self.costPerTimeRange.get()
        self.twStartRange.reset()
        for a in range(self.nmbAwayPeriodsRange.get()):
            baseStartDate = demandCreationDate + self.twStartRange.get()
            for o in self.createRandomOffersForADemand(demandCreationDate, baseStartDate, baseDuration, baseCostFactor):
                offers.append(o)

        yield str(demandCreationDate)
        yield str(len(offers))
        for o in offers:
            for e in o.getElements():
                yield str(int(e))

    def createRandomOffersForADemand(self, demandCreationDate, baseStartDate, baseDuration, baseCostFactor):
        """ Yields offers for given base start dates and durations """

        minVehicleTypeIndex = self.getRandomVehicleTypeIndex()
        for vehicleTypeIndex in range(minVehicleTypeIndex, len(self.vehicleTypes)):
            vehicleType = self.vehicleTypes[vehicleTypeIndex]

            o = self.createRandomOffer(demandCreationDate, baseStartDate, baseDuration, self.twDueDateRangeMaxVehicle)
            o.cost = o.getDuration() * vehicleType.costFactor * baseCostFactor

            usageProbability = self.vehicleUsageProbability
            if (vehicleTypeIndex != minVehicleTypeIndex):
                usageProbability = self.vehicleUsageProbabilityOfNonPreferredVehicleType

            for o.vehicleIndex in vehicleType.getVehicleIndices():
                if (self.probabilityRange.get() <= usageProbability):
                    yield copy.deepcopy(o)

        costFactorOfMinVehicleType = self.vehicleTypes[minVehicleTypeIndex].costFactor

        if (self.probabilityRange.get() <= self.probabilityNonVehicleA):
            o = self.createRandomOffer(demandCreationDate, baseStartDate, baseDuration, self.twDueDateRangeMaxNonVehicleA)
            o.cost = o.getDuration() * costFactorOfMinVehicleType * baseCostFactor * self.relativeCostOfNonVehicleA.get() / 100
            yield copy.deepcopy(o)

        if (self.probabilityRange.get() <= self.probabilityNonVehicleB):
            o = self.createRandomOffer(demandCreationDate, baseStartDate, baseDuration, self.twDueDateRangeMaxNonVehicleB)
            o.cost = o.getDuration() * costFactorOfMinVehicleType * baseCostFactor * self.relativeCostOfNonVehicleB.get() / 100
            yield copy.deepcopy(o)

    def createRandomOffer(self, demandCreationDate, baseStartDate, baseDuration, dueDateRangeMax):
        o = Offer()
        o.twStart = baseStartDate - self.extraDurationRange.get()
        if (o.twStart < demandCreationDate):
            o.twStart = demandCreationDate

        o.dueDate = RandomRange(o.twStart - dueDateRangeMax, o.twStart).get()
        if (o.dueDate < demandCreationDate):
            o.dueDate = demandCreationDate

        o.twEnd = baseStartDate + baseDuration + self.extraDurationRange.get()
        return o

def ensurePathExistsAndEmpty(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
    for dirpath, dirnames, files in os.walk(dir):
        if files:
            raise GeneratorException("Directory '" + dir + "' must be empty")

class VehicleType():
    """ Specifies a vehicle type """
    def __init__(self):
        self.costFactor = 0
        self.percentageOfFleet = 0
        self.nmbVehicles = 0
        self.initialVehicleIndex = 0
    def withCostFactor(self, c):
        self.costFactor = c
        return self
    def withPercentageOfFleet(self, p):
        self.percentageOfFleet = p
        return self
    def getVehicleIndices(self):
        return range(self.initialVehicleIndex, self.initialVehicleIndex + self.nmbVehicles)

class Offer:
    """ Specifies a mobility offer """
    def __init__(self):
        self.cost = 0
        self.twStart = 0
        self.twEnd = 0
        self.dueDate = 0
        self.vehicleIndex = -1
    def getDuration(self):
        return self.twEnd - self.twStart
    def getElements(self):
        yield self.cost
        yield self.twStart
        yield self.twEnd
        yield self.dueDate
        yield self.vehicleIndex

class RandomRange:
    """ Defines a range of integers in order to generate uniformly distributed random integers within that range (inclusive) """
    def __init__(self, min, max):
        self.min = min
        self.max = max
    def getExpectedValue(self):
        return (self.min + self.max) / 2
    def __str__(self):
        return "U[" + str(self.min) + "," + str(self.max) + "]"
    def get(self):
        return randint(self.min, self.max)

class UniqueRandomRange:
    """ RandomRange where no number is drawn twice """
    def __init__(self, min, max):
        self.min = min
        self.max = max
        self.usedNumbers = set()
    def remaining(self):
        return self.size() - len(self.usedNumbers)
    def size(self):
        return self.max - self.min + 1
    def reset(self):
        self.usedNumbers = set()
    def get(self):
        if self.remaining() <= 0:
            raise AttributeError("No unused numbers left in unique random range [" + str(self.min) + ", " + str(self.max) + "] (" + str(len(self.usedNumbers)) + " already used).")
        result = randint(self.min, self.max)
        if result in self.usedNumbers:
            return self.get()
        self.usedNumbers.add(result)
        return result

class GeneratorException (BaseException):
    """ An exception that can be thrown by the instance generator """
    pass

try:
    run()
except GeneratorException as e:
    print ("\nError: " + str(e) + "\n")

