import json
import typing

from sky_spot.utils import ClusterType

if typing.TYPE_CHECKING:
    import configargparse
    from sky_spot import env
    


class Strategy:
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self, deadline_hours: float, task_duration_hours: float, restart_overhead_hours: float):
        self.deadline = deadline_hours * 3600
        self.task_duration = task_duration_hours * 3600

        self.restart_overhead = restart_overhead_hours * 3600

        self.remaining_restart_overhead = 0
        self.task_done_time = []

        self.env = None

    def register_env(self, env):
        self.env = env

    def __init_subclass__(cls):
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

    def __repr__(self) -> str:
        return f'{self.NAME}({json.dumps(self.config)})'

    def step(self) -> ClusterType:
        raise NotImplemented        
    
    @property
    def task_done(self):
        return sum(self.task_done_time) >= self.task_duration

    @property
    def config(self):
        return {'name': self.NAME, 'deadline': self.deadline, 'task_duration': self.task_duration, 'restart_overhead': self.restart_overhead, 'env': self.env.config}

    @classmethod
    def from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Strategy':
        # parser.add_argument(f'--strategy-config', type=str, default=None, is_config_file=True, required=False)
        parser.add_argument(f'--strategy', type=str, default='strawman', choices=cls.SUBCLASSES.keys())
        args, _ = parser.parse_known_args()
        cls = cls.SUBCLASSES[args.strategy]
        return cls._from_args(parser)

    @property
    def name(self):
        return self.NAME

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Strategy':
        raise NotImplementedError
