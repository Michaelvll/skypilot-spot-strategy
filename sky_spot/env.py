import json
import typing
from typing import Tuple

from sky_spot import trace
from sky_spot.utils import ClusterType, COSTS

if typing.TYPE_CHECKING:
    import configargparse


class Env:
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self, gap_seconds: float):
        # dones not include the cluster_type for the current timestamp - 1 -> timestamp, until observed on timestamp
        self.cluster_type_histroy = []
        self.cluster_type = ClusterType.NONE
        self.gap_seconds = gap_seconds
        self.timestamp = 0
        self.observed_timestamp = -1
    
    def __init_subclass__(cls) -> None:
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

    def spot_available(self) -> bool:
        """
        Returns True if spot is available at the current timestamp -> timestamp + 1
        """
        raise NotImplementedError

    def observe(self) -> Tuple[ClusterType, bool]:
        """
        Returns the cluster type (at last time gap) and whether spot is available
        """
        assert self.observed_timestamp == self.timestamp - 1, (self.observed_timestamp, self.timestamp)
        self.observed_timestamp = self.timestamp
        has_spot = self.spot_available()
        last_cluster_type = self.cluster_type
        self.cluster_type_histroy.append(last_cluster_type)

        if self.cluster_type == ClusterType.SPOT and not has_spot:
            print('Preempted at', self.timestamp)
            self.cluster_type = ClusterType.NONE
        return last_cluster_type, has_spot

    def step(self, request_type: ClusterType):
        if self.observed_timestamp != self.timestamp:
            self.observe()
        if request_type == ClusterType.SPOT and not self.spot_available():
            raise ValueError('Spot not available')
        new_cluster_type = self._step(request_type)
        self.timestamp += 1
        return new_cluster_type


    def _step(self, request_type: ClusterType):
        self.cluster_type = request_type
        return self.cluster_type

    @property
    def elapsed_seconds(self) -> float:
        return self.timestamp * self.gap_seconds

    @property
    def accumulated_cost(self) -> float:
        """Accumulated cost of the environment"""
        return sum(COSTS[cluster_type] for cluster_type in self.cluster_type_histroy)
    
    def info(self) -> dict:
        # Step should have been called
        assert self.timestamp == self.observed_timestamp + 1
        return {
                'Timestamp': self.timestamp - 1,
                'Elapsed': (self.timestamp - 1) * self.gap_seconds,
                'Cost': self.accumulated_cost,
                'ClusterType': self.cluster_type.value,
            }

    def __repr__(self) -> str:
        return f'{self.NAME}({json.dumps(self.config)})'

    @property
    def config(self):
        return dict()

    @classmethod
    def from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Env':
        parser.add_argument(f'--env-config', type=str, default=None, is_config_file=True, required=False)
        parser.add_argument(f'--env', type=str, default='trace', choices=cls.SUBCLASSES.keys())
        args, _ = parser.parse_known_args()
        cls = cls.SUBCLASSES[args.env]
        return cls._from_args(parser)

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Env':
        raise NotImplementedError



class TraceEnv(Env):
    NAME = 'trace'

    def __init__(self, trace_file: str):
        self._trace_file = trace_file
        self.trace = trace.Trace.from_file(trace_file)
        
        super().__init__(self.trace.gap_seconds)

    def spot_available(self) -> bool:
        if self.timestamp >= len(self.trace):
            raise ValueError('Timestamp out of range')
        return not self.trace[self.timestamp]

    @property
    def config(self) -> dict:
        return {'name': self.NAME, 'trace_file': self._trace_file, 'metadata': self.trace.metadata}

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> 'TraceEnv':
        group = parser.add_argument_group('TraceEnv')
        group.add_argument('--trace-file', type=str, help='Folder containing the trace')
        args, _ = parser.parse_known_args()
        return cls(args.trace_file)
    