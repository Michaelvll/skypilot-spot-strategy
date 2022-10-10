import argparse
import typing

from sky_spot.utils import args_parser

if typing.TYPE_CHECKING:
    import argparse
    


class Strategy(args_parser.ArgsParser):
    NAME = 'abstract'
    SUBCLASSES = {}

    def __init__(self):
        pass

    def __init_subclass__(cls):
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

