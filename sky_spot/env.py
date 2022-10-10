import enum
import json
import typing

from sky_spot import trace

if typing.TYPE_CHECKING:
    import configargparse



class ClusterType(enum.Enum):
    ON_DEMAND = 'on-demand'
    SPOT = 'spot'
    NONE = 'none'

class Env:
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self):
        self.cluster_type = ClusterType.NONE
        self.timestamp = 0
        self.observed_timestamp = -1
    
    def __init_subclass__(cls) -> None:
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

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
    
    def __repr__(self) -> str:
        return f'{self.NAME}({self.config_str})'

    @property
    def config_str(self):
        return ''

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
        super().__init__()
        self._trace_file = trace_file
        self.trace = trace.Trace.from_file(trace_file)

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

    @property
    def config_str(self):
        return json.dumps({'trace_file': self._trace_file})

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'TraceEnv':
        group = parser.add_argument_group('TraceEnv')
        group.add_argument('--trace-file', type=str, help='Folder containing the trace')
        args, _ = parser.parse_known_args()
        return cls(args.trace_file)
