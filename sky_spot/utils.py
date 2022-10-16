import enum

class ClusterType(enum.Enum):
    NONE = enum.auto()
    SPOT = enum.auto()
    ON_DEMAND = enum.auto()


# Price for p3.2xlarge (single V100) on us-west-2
COSTS = {
    ClusterType.ON_DEMAND: 3.06,
    ClusterType.SPOT: 0.9731,
    ClusterType.NONE: 0,
}
