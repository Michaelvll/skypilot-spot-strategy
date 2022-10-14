import enum

class ClusterType(enum.Enum):
    ON_DEMAND = 'on-demand'
    SPOT = 'spot'
    NONE = 'none'


COSTS = {
    ClusterType.ON_DEMAND: 3,
    ClusterType.SPOT: 1,
    ClusterType.NONE: 0,
}
