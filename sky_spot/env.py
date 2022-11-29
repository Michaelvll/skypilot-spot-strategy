import math
import json
import os
import typing
from typing import List, Tuple, Union

from sky_spot import trace
from sky_spot.utils import ClusterType, COSTS

if typing.TYPE_CHECKING:
    import configargparse


class Env:
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self, gap_seconds: float):
        self.gap_seconds = gap_seconds
        self.reset()

    def reset(self):
        # dones not include the cluster_type for the current timestamp - 1 -> timestamp, until observed on timestamp
        self.cluster_type_histroy = []
        self.cluster_type = ClusterType.NONE
        self.tick = 0
        self.observed_tick = -1
    
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
        assert self.observed_tick == self.tick - 1, (self.observed_tick, self.tick)
        self.observed_tick = self.tick
        has_spot = self.spot_available()
        last_cluster_type = self.cluster_type
        self.cluster_type_histroy.append(last_cluster_type)

        if self.cluster_type == ClusterType.SPOT and not has_spot:
            print('Preempted at', self.tick)
            self.cluster_type = ClusterType.NONE
        return last_cluster_type, has_spot

    def step(self, request_type: ClusterType):
        if self.observed_tick != self.tick:
            self.observe()
        if request_type == ClusterType.SPOT and not self.spot_available():
            raise ValueError('Spot not available')
        new_cluster_type = self._step(request_type)
        self.tick += 1
        return new_cluster_type


    def _step(self, request_type: ClusterType):
        self.cluster_type = request_type
        return self.cluster_type

    def get_trace_before_end(self, end: float) -> trace.Trace:
        # Used for ideal strategy
        raise NotImplementedError

    @property
    def elapsed_seconds(self) -> float:
        return self.tick * self.gap_seconds

    @property
    def accumulated_cost(self) -> float:
        """Accumulated cost of the environment"""
        return sum(COSTS[cluster_type] * self.gap_seconds / 3600 for cluster_type in self.cluster_type_histroy)
    
    def info(self) -> dict:
        # Step should have been called
        assert self.tick == self.observed_tick + 1
        return {
                'Timestamp': self.tick - 1,
                'Elapsed': (self.tick - 1) * self.gap_seconds,
                'Cost': self.accumulated_cost,
                'ClusterType': self.cluster_type_histroy[-1].value if self.cluster_type_histroy else ClusterType.NONE.value,
            }

    def __repr__(self) -> str:
        return f'{self.NAME}({json.dumps(self.config)})'

    @property
    def config(self):
        return dict()

    @classmethod
    def from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Env':
        # parser.add_argument(f'--env-config', type=str, default=None, is_config_file=True, required=False)
        parser.add_argument(f'--env', type=str, default='trace', choices=cls.SUBCLASSES.keys())
        args, _ = parser.parse_known_args()
        cls = cls.SUBCLASSES[args.env]
        return cls._from_args(parser)

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Env':
        raise NotImplementedError



class TraceEnv(Env):
    NAME = 'trace'

    def __init__(self, trace_file: str, env_start_hours: float):
        
        self._trace_file = trace_file
        self.trace = trace.Trace.from_file(trace_file)

        self._start_index = 0
        if env_start_hours > 0:
            self._start_index = int(math.ceil(env_start_hours * 3600 / self.trace.gap_seconds))
        
        super().__init__(self.trace.gap_seconds)

    def spot_available(self) -> bool:
        tick = self.tick + self._start_index
        if tick >= len(self.trace):
            raise ValueError('Timestamp out of range')
        return not self.trace[tick]
    
    def get_trace_before_end(self, end_seconds: float) -> trace.Trace:
        end_index = int(math.ceil(end_seconds / self.gap_seconds))
        return self.trace[self._start_index:end_index+self._start_index]

    @property
    def config(self) -> dict:
        return {'name': self.NAME, 'trace_file': self._trace_file, 'start_index': self._start_index, 'metadata': self.trace.metadata}

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> List['TraceEnv']:
        group = parser.add_argument_group('TraceEnv')
        group.add_argument('--trace-file', type=str, help='File/folder containing the trace')
        group.add_argument('--env-start-hours', type=float, default=0, help='Start hours of the trace')
        args, _ = parser.parse_known_args()
        if os.path.isdir(args.trace_file):
            trace_files = []
            for file in os.listdir(args.trace_file):
                if file.endswith('.json'):
                    trace_files.append(os.path.join(args.trace_file, file))
            return [cls(trace_file, args.env_start_hours) for trace_file in trace_files]
        return [cls(args.trace_file, args.env_start_hours)]
    