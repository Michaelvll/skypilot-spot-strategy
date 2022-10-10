import typing

if typing.TYPE_CHECKING:
    import argparse

class ArgsParser:

    @classmethod
    def from_args(cls, parser: 'argparse.ArgumentParser', name: str):
        cls = cls.SUBCLASSES[name]
        return cls._from_args(parser)

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser'):
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{self.NAME}({self.config_str})'

    @property
    def config_str(self):
        return ''
