import typing

if typing.TYPE_CHECKING:
    import configargparse
    


class Strategy:
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self):
        pass

    def __init_subclass__(cls):
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

    def __repr__(self) -> str:
        return f'{self.NAME}({self.config_str})'

    @property
    def config_str(self):
        return ''

    @classmethod
    def from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Strategy':
        parser.add_argument(f'--strategy-config', type=str, default=None, is_config_file=True, required=False)
        parser.add_argument(f'--strategy', type=str, default='strawman', choices=cls.SUBCLASSES.keys())
        args, _ = parser.parse_known_args()
        cls = cls.SUBCLASSES[args.strategy]
        return cls._from_args(parser)

    @classmethod
    def _from_args(cls, parser: 'configargparse.ArgumentParser') -> 'Strategy':
        raise NotImplementedError
