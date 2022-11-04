import enum

class ClusterType(enum.Enum):
    NONE = enum.auto()
    SPOT = enum.auto()
    ON_DEMAND = enum.auto()


# Price for p3.2xlarge (single V100) on us-west-2
# https://aws.amazon.com/ec2/instance-types/p3/
COSTS = {
    ClusterType.ON_DEMAND: 3.06,
    ClusterType.SPOT: 0.9731,
    ClusterType.NONE: 0,
}

# Price for p2.xlarge (single K80) on us-east-1
# COSTS = {
#     ClusterType.ON_DEMAND: 0.9,
#     ClusterType.SPOT: 0.3384,
#     ClusterType.NONE: 0,
# }
