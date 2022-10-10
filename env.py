import enum

from trace import Trace


class ClusterType(enum.Enum):
    ON_DEMAND = 'on-demand'
    SPOT = 'spot'
    NONE = 'none'

class Env:
    def __init__(self):
        self.cluster_type = ClusterType.NONE
        self.timestamp = 0
        self.observed_timestamp = -1

    def observe(self):
        self.observed_timestamp = self.timestamp
        return self._observe()

    def step(self, cluster_type: ClusterType):
        if self.observed_timestamp != self.timestamp:
            self.observe()
        new_cluster_type = self._step(cluster_type)
        self.timestamp += 1
        return new_cluster_type


    def _observe(self):
        return self.cluster_type

    def _step(self, cluster_type: ClusterType):
        self.cluster_type = cluster_type
        return self.cluster_type


class TraceEnv(Env):
    def __init__(self, trace: Trace):
        super().__init__()
        self.trace = trace

    def _observe(self):
        if self.timestamp >= len(self.trace):
            return None
        if self.cluster_type == ClusterType.SPOT:
            if self.trace[self.timestamp]:
                return ClusterType.NONE
            else:
                return ClusterType.SPOT
        return self.cluster_type

    def _step(self, cluster_type: ClusterType):
        return super()._step(cluster_type)
