import argparse
import json

from sky_spot.strategies import strategy

class StrawmanStrategy(strategy.Strategy):
    NAME = 'strawman'

    def __init__(self, deadline: int, task_duration: int):
        super().__init__()
        self.deadline = deadline
        self.task_duration = task_duration

    @property
    def config_str(self):
        return ''

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'StrawmanStrategy':
        group = parser.add_argument_group('StrawmanStrategy')
        group.add_argument('--deadline', type=int, default=10)
        group.add_argument('--task-duration', type=int, default=10)
        args, _ = parser.parse_known_args()
        return cls(args.deadline, args.task_duration)

    @property
    def config_str(self):
        return json.dumps({'deadline': self.deadline, 'task_duration': self.task_duration})
