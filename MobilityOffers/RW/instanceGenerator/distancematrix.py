from mot import MoT, costPerUnitOfEmission
import csv
from geopy import distance, Point
distance.VincentyDistance.ELLIPSOID = 'WGS-84'


def _load_nodes():
    with open("doc/zaehlbezirke.csv") as zb:
        nodes = dict()
        reader = csv.DictReader(zb)
        for row in reader:
            id = int(row["id"])
            nodes[id] = Node(id, lat=float(row["lat"]), lon=float(row["lon"]))
        return nodes


class Node(object):
    def __init__(self, id, lat, lon):
        self.id = id
        self.pos = Point(longitude=lon, latitude=lat)

    def lon(self):
        return self.pos.longitude

    def lat(self):
        return self.pos.latitude

    def aerial_distance_to(self, other):
        return distance.distance(self.pos, other.pos).meters


class MoveOption (object):
    def __init__(self, fn, tn, mot):
        self.fromNode = fn
        self.toNode = tn
        self.modeOfTransport = mot
        self.distance_meters = 0
        self.duration_seconds = 0
        self.cost = 0
        self.geom = None
        self.aerial_distance = 0

    def to_dict(self):
        return vars(self)


class DistanceMatrix(object):
    def __init__(self):
        self.nodes = _load_nodes()

        self.move_options = []
        self.generate_matrix()

    def generate_matrix(self):
        for fromNode in self.nodes.values():
            for toNode in self.nodes.values():
                aerial = fromNode.aerial_distance_to(toNode)

                for mot in MoT.manager.to_list():
                    option = MoveOption(fn=fromNode.id, tn=toNode.id, mot=mot.id)
                    option.geom = "LINESTRING({:} {:}, {:} {:})".format(fromNode.lon(), fromNode.lat(), toNode.lon(),
                                                                 toNode.lat())
                    option.aerial_distance = aerial

                    sloped_dist = aerial * mot.slopingFactor
                    emissions = sloped_dist * mot.emissionsPerDistance

                    option.distance_meters = sloped_dist
                    option.duration_seconds = sloped_dist * mot.durationPerDistance + mot.overheadDuration
                    option.cost = sloped_dist * mot.costPerDistance + option.duration_seconds * mot.costPerTime + emissions * costPerUnitOfEmission

                    self.move_options.append(option)

    def get_node(self, nid):
        assert nid in self.nodes.keys()

        return self.nodes.get(nid)
