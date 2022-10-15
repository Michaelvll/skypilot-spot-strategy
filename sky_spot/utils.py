import enum

class ClusterType(enum.Enum):
    NONE = enum.auto()
    SPOT = enum.auto()
    ON_DEMAND = enum.auto()


COSTS = {
    ClusterType.ON_DEMAND: 3,
    ClusterType.SPOT: 1,
    ClusterType.NONE: 0,
}
