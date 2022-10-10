import argparse

from sky_spot.strategies import strategy

class StrawmanStrategy(strategy.Strategy):
    NAME = 'strawman'

    def __init__(self):
        super().__init__()

    @property
    def config_str(self):
        return ''

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'StrawmanStrategy':
        group = parser.add_argument_group('StrawmanStrategy')
        group.add_argument('--deadline', type=int, default=10)
        group.add_argument('--task_duration', type=int, default=10)
        args, _ = parser.parse_known_args()
        return cls()
