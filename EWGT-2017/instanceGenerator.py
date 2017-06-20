from enum import Enum
from random import randint
import copy
import locale
import math
import os


# An instance generator for creating random problem instances for the paper
# "Planning Shared Corporate Mobility Services"
# submitted to the EURO Working Group on Transportation Meeting (EWGT) 2017.
# Authors: Miriam Enzi, Benjamin Biesinger, Sebastian Knopp, Sophie Parragh, Matthias Prandtstetter


# An empty existing directory to store generated instances
INSTANCE_DIRECTORY = "C:\\work\\seamless\\Codes\\instances"

# The following units are assumened:
# - Distance: meters
# - Cost: Euro cents
# - Time: Seconds
# - Energy: kwH
# - Emissions: g CO_2


# For clarity, some functions converting units are introduced in the following

def euroPerHour2CentsPerSecond(value):
    return value * 100 / 3600

def kilometerPerHour2MeterPerSecond(value):
    return value / 3.6

def days2Seconds(days):
    return days * 3600 * 24

def minutes2Seconds(days):
    return days * 60

def euroPerKm2centsPerMeter(value):
    return value * 100 / 1000

def kwHPerKm2kwHPerMeter(value):
    return value / 1000

salaryInCentsPerSecond = euroPerHour2CentsPerSecond(19.42)
durationOfPlanningHorizonInSeconds = days2Seconds(7)
fixedCostReferenceDuration = days2Seconds(265)
fixedCostCorrectionFactor = durationOfPlanningHorizonInSeconds / fixedCostReferenceDuration
unlimitedNumber = 1000000 # used where a number (e.g. of vehicles) should be unlimited

def run():
    g = Generator()
    g.modesOfTransport = createModeOfTransportList()
    for i in range(5):
        inst = g.generate()    
        inst.name = "instance " + str(i)
        inst.store(INSTANCE_DIRECTORY)

class Generator ():
    def __init__(self):
        self.nmbUsers = 10
        self.nmbStartDepots = 2
        self.nmbEndDepots = 2
        self.nmbCustomers = 11
        self.nmbRechargingStations = 5
        self.modesOfTransport = []
        self.coordinateRangeX = RandomRange(0, 20000)
        self.coordinateRangeY = RandomRange(0, 20000)
        self.planningHorizon = durationOfPlanningHorizonInSeconds
        self.timeWindowDurationRange = RandomRange(minutes2Seconds(10), minutes2Seconds(300))
        self.serviceDurationRange = RandomRange(minutes2Seconds(10), minutes2Seconds(120))
        self.allowedVisitingPercentage = 70
        self.costPerUnitOfEmission = 500 / (1000 * 1000) # 5€ per tonne -> cents per gram

    def generate (self):
        inst = Instance()
        
        inst.modesOfTransport = self.modesOfTransport
        nmbRechargingStationDuplications = self.nmbCustomers

        # generate nodes with start depots being identical to end depots
        endDepots = []
        for i in range(self.nmbStartDepots):
            startDepot = self.__createRandomNode(NodeType.StartDepot)
            inst.nodes.append(startDepot)

            endDepot = copy.deepcopy(startDepot)
            endDepot.type = NodeType.EndDepot
            endDepots.append(endDepot)
        for i in range(self.nmbCustomers):
            inst.nodes.append(self.__createRandomNode(NodeType.Customer))
        for i in range(self.nmbRechargingStations):
            rechargingStationNode = self.__createRandomNode(NodeType.RechargingStation)
            for i in range(nmbRechargingStationDuplications):
                inst.nodes.append(rechargingStationNode)
        inst.nodes.extend(endDepots)

        # generate move options (i.e. edges in the graph underlying the VRP - the distance and cost matrix)
        for fromIndex, fromNode in enumerate(inst.nodes):
            for toIndex, toNode in enumerate(inst.nodes):
                for motIndex, mot in enumerate(inst.modesOfTransport):
                    option = MoveOption()

                    option.fromNode = fromIndex
                    option.toNode = toIndex
                    option.modeOfTransport = motIndex

                    d = fromNode.getFlightDistance(toNode) * mot.slopingFactor
                    emissions = d * mot.emissionsPerDistance

                    option.distance = d
                    option.duration = d * mot.durationPerDistance + mot.overheadDuration
                    option.cost = d * mot.costPerDistance + option.duration * mot.costPerTime + emissions * self.costPerUnitOfEmission

                    inst.moveOptions.append(option)

        probabilityRangeInPercent = RandomRange(1, 100)

        # generate mode of transport dependent node information
        for motIndex, mot in enumerate(inst.modesOfTransport):
            nmbVehicles = mot.nmbVehicles // self.nmbStartDepots # integer division
            nmbVehiclesFirstDepot = nmbVehicles + (mot.nmbVehicles % self.nmbStartDepots)
            foundFirstDepot = False

            for nodeIndex, node in enumerate(inst.nodes):
                mdni = MotDependentNodeInfo();

                mdni.nmbVehicles = 0
                if (node.type == NodeType.StartDepot):
                    if foundFirstDepot:
                        mdni.nmbVehicles = nmbVehicles
                    else:
                        mdni.nmbVehicles = nmbVehiclesFirstDepot
                    foundFirstDepot = True

                mdni.nodeIndex = nodeIndex
                mdni.motIndex = motIndex
                mdni.rechargingCost = mot.rechargingCostRange.get()
                mdni.isReachable = probabilityRangeInPercent.get() <= mot.reachabilityProbability 
                inst.motDependentNodeInfos.append(mdni)

        # generate user dependent node information
        for nodeIndex, node in enumerate(inst.nodes):
            for userIndex in range(self.nmbUsers):
                udni = UserDependentNodeInfo()
                udni.userIndex = userIndex
                udni.nodeIndex = nodeIndex

                udni.isVisitingAllowed = 1
                if (node.type == NodeType.Customer and probabilityRangeInPercent.get() > self.allowedVisitingPercentage):
                    udni.isVisitingAllowed = 0

                inst.userDependentNodeInfos.append(udni)

        # summarizing general information on the instance
        gi = GeneralInstanceInformation()
        gi.nmbUsers = self.nmbUsers
        gi.nmbCustomers = self.nmbCustomers
        gi.nmbStartDepots = self.nmbStartDepots
        gi.nmbEndDepots = self.nmbEndDepots
        gi.nmbRechargingStations = self.nmbRechargingStations
        gi.nmbModesOfTransport = len(self.modesOfTransport)
        inst.general.append(gi)

        return inst


    def __createRandomNode(self, type):
        """ Creates a random node of a given type with coordinates, a time window and a serive time. """
        n = Node()
        n.type = type
        n.coordinateX = self.coordinateRangeX.get()
        n.coordinateY = self.coordinateRangeY.get()
        if (type == NodeType.Customer):
            twDuration = self.timeWindowDurationRange.get()
            n.twBeginning = RandomRange(0, self.planningHorizon - twDuration - n.serviceDuration).get()
            n.twEnd = n.twBeginning + twDuration
            n.serviceDuration = self.serviceDurationRange.get()
        else:
            n.twBeginning = 0
            n.twEnd = self.planningHorizon
            n.serviceDuration = 0
        return n

class RandomRange:
    """ Defines a range of integers in order to generate uniformly distributed random integers within that range (inclusive) """
    def __init__(self, min, max):
        self.min = min
        self.max = max
    def __str__(self):
        return "U[" + str(self.min) + "," + str(self.max) + "]"
    def get(self):
        return randint(self.min, self.max)

class CSVSerializable:
    """Provides a base class for classes that represent lines in csv files """

    def getCSVHeader(self):
        return ";".join(self.__getMembers())
    def getCSVLine(self):
        return ";".join(str(getattr(self, m)) for m in self.__getMembers())
    def __getMembers(self):
        """ Returns the list of members of this object """
        return [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("__")]

def getCSV(listOfSerializables):
    """ Returns a string containing a csv file that represents a list of csv-serializable objects. """
    if len(listOfSerializables) == 0:
        return ""
    return listOfSerializables[0].getCSVHeader() + "\n" + "\n".join([e.getCSVLine() for e in listOfSerializables])

def writeFile(filename, string):
    """ Writes the given string to a file. """
    open(filename, 'w').write(string)
    print("wrote: " + filename)

class NodeType(Enum):
    StartDepot = 1
    EndDepot = 2
    RechargingStation = 3
    Customer = 4

class Node (CSVSerializable):
    def __init__(self):
        self.coordinateX = -1
        self.coordinateY = -1
        self.twBeginning = -1
        self.twEnd = -1
        self.serviceDuration = -1
        self.type = NodeType.StartDepot

    def getFlightDistance(self, other):
        diffX = self.coordinateX - other.coordinateX
        diffY = self.coordinateY - other.coordinateY
        return math.sqrt(diffX*diffX + diffY*diffY)

class MoveOption (CSVSerializable):
    """ Represents a matrix entry which specifies a possibility to move from fromLocation to toLocation. """
    def __init__(self):
        self.fromNode = 1
        self.toNode = 2
        self.modeOfTransport = 0
        self.distance = 0
        self.duration = 0
        self.cost = 0

class ModeOfTransport (CSVSerializable):
    def __init__(self):
        self.name = "default"
        self.type = "unknown"
        self.nmbVehicles = -1
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

class MotDependentNodeInfo (CSVSerializable):
    def __init__(self):
        self.nmbVehicles = 1
        self.nodeIndex = 0
        self.motIndex = 0
        self.rechargingCost = 0 # per energy unit
        self.isReachable = False

class UserDependentNodeInfo (CSVSerializable):
    def __init__(self):
        self.userIndex = 0
        self.nodeIndex = 0
        self.isVisitingAllowed = True

class GeneralInstanceInformation (CSVSerializable):
    def __init__(self):
        self.nmbUsers = 0
        self.nmbCustomers = 0
        self.nmbStartDepots = 0
        self.nmbEndDepots = 0
        self.nmbRechargingStations = 0
        self.nmbModesOfTransport = 0

class ModeOfTransportTypeSummary (CSVSerializable):
    def __init__(self):
        self.motType = "unknown"
        self.nmbModesOfTransport = 0

class Instance ():
    def __init__(self):
        self.name = "default-instance"
        self.nodes = []
        self.modesOfTransport = []
        self.moveOptions = []
        self.motDependentNodeInfos = []
        self.userDependentNodeInfos = []
        self.general = []

    def store(self, basedir):
        """ Stores the instances under the given directory """

        dir = basedir + "\\" + self.name
        if not os.path.exists(dir):
            os.makedirs(dir)
        for dirpath, dirnames, files in os.walk(dir):
            if files:
                raise GeneratorException("Directory '" + dir + "' must be empty")

        motTypes = {}
        for mot in self.modesOfTransport:
            motTypes[mot.type] = 0
        for mot in self.modesOfTransport:
            motTypes[mot.type] += 1
        motTypeSummary = []
        for key, value in motTypes.items():
            s = ModeOfTransportTypeSummary()
            s.motType = key
            s.nmbModesOfTransport = value
            motTypeSummary.append(s)

        nmbMots = len(self.modesOfTransport)
        nmbNodes = len(self.nodes)
        nmbUsers = self.general[0].nmbUsers

        writeFile(dir + "\\nodes.csv", getCSV(self.nodes))
        writeFile(dir + "\\modesOfTransport.csv", getCSV(self.modesOfTransport))
        writeFile(dir + "\\moveOptions.csv", getCSV(self.moveOptions))
        writeFile(dir + "\\motDependentNodeInfos.csv", getCSV(self.motDependentNodeInfos))
        writeFile(dir + "\\motDependentNodeInfos-isReachable.csv", getMatrixCSV(nmbMots, nmbNodes, lambda r, c: self.motDependentNodeInfos[r*nmbNodes+c].isReachable))
        writeFile(dir + "\\motDependentNodeInfos-nmbVehicles.csv", getMatrixCSV(nmbMots, nmbNodes, lambda r, c: self.motDependentNodeInfos[r*nmbNodes+c].nmbVehicles))
        writeFile(dir + "\\motDependentNodeInfos-rechargingCost.csv", getMatrixCSV(nmbMots, nmbNodes, lambda r, c: self.motDependentNodeInfos[r*nmbNodes+c].rechargingCost))
        writeFile(dir + "\\userDependentNodeInfos.csv", getCSV(self.userDependentNodeInfos))
        writeFile(dir + "\\userDependentNodeInfos-isVisitingAllowed.csv", getMatrixCSV(nmbNodes, nmbUsers, lambda r, c: self.userDependentNodeInfos[r*nmbUsers+c].isVisitingAllowed))
        writeFile(dir + "\\modeOfTransportTypeSummary.csv", getCSV(motTypeSummary))
        writeFile(dir + "\\general.csv", getCSV(self.general))

def getMatrixCSV(nmbRows, nmbColumns, matrix):
    """ Returns a string representing a given matrix using a csv format (comma separated values) """
    result = ""
    for r in range(nmbRows):
        result += ';'.join([str(matrix(r, c)) for c in range(nmbColumns)]) + "\n"
    return result

def createModeOfTransportList():
    """ Creates a list of ModeOfTransport objects including
        pedestrians, bikes, electric vehicles, combustions vehicles,
        public transport and taxis
    """
    motList = []

    m = ModeOfTransport()
    m.name = "Pedestrian"
    m.type = "Pedestrian"
    m.nmbVehicles = unlimitedNumber
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "Bike"
    m.type = "Bike"
    m.nmbVehicles = 10
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "CarSmall"
    m.type = "ICEV"
    m.nmbVehicles = 10
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "CarMedium"
    m.type = "ICEV"
    m.nmbVehicles = 4
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "Van"
    m.type = "ICEV"
    m.nmbVehicles = 1
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "SmartED"
    m.type = "BEV"
    m.nmbVehicles = 2
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "NissanLeaf"
    m.type = "BEV"
    m.overheadDuration = minutes2Seconds(10)
    m.nmbVehicles = 4
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "Mitsubishi-iMIEV"
    m.type = "BEV"
    m.nmbVehicles = 2
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "PublicTransport"
    m.type = "PublicTransport"
    m.nmbVehicles = unlimitedNumber
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
    motList.append(m)

    m = ModeOfTransport()
    m.name = "Taxi"
    m.type = "Taxi"
    m.nmbVehicles = unlimitedNumber
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
    motList.append(m)
    return motList

class GeneratorException (BaseException):
    """ An exception that can be thrown by the instance generator """
    pass

try:
    run()
except GeneratorException as e:
    print ("\nError: " + str(e) + "\n")

