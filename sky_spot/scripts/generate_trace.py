import argparse
import json
import pathlib
import random

import numpy as np


GENERATORS = {}

class TraceGenerator:
    NAME = 'abstract'
    def __init__(self, trace_folder: str):
        self.trace_folder = pathlib.Path(trace_folder)
        self.trace_folder.mkdir(parents=True, exist_ok=True)

    def metadata(self):
        raise NotImplementedError

    def __init_subclass__(cls) -> None:
        GENERATORS[cls.NAME] = cls

class PoissonTraceGenerator(TraceGenerator):
    NAME = 'poisson'

    def __init__(self, trace_folder: str, gap_seconds: int, hourly_rate: float, length: int):
        super().__init__(trace_folder)
        self.gap_seconds = gap_seconds
        self.hourly_rate = hourly_rate

        # Calculate the rate per gap seconds based on poisson distribution
        # https://math.stackexchange.com/questions/2480542/probability-of-an-event-occurring-within-a-smaller-time-interval-if-one-knows-th
        occurence_per_hour = -np.log(1 - self.hourly_rate) # lambda
        self.gap_rate = 1 - np.exp(-occurence_per_hour * gap_seconds / 3600) # 1 - e^(-lambda * gap_seconds / 3600)
        print(f'hourly_rate: {self.hourly_rate:.2f}, gap_rate ({gap_seconds/3600:.2f} hours): {self.gap_rate:.2f}')

        self.length = length
        self.output_folder = self.trace_folder / f'gap_{self.gap_seconds}_hourly-rate_{hourly_rate}'
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def generate(self, num_traces: int):
        for i in range(num_traces):
            random.seed(i)
            file_path = self.output_folder / f'{i}.json'
            if file_path.exists():
                continue
            data = [int(random.random() < self.gap_rate) for _ in range(self.length)]
            trace = {
                'generator': self.NAME,
                'metadata': self.metadata(),
                'data': data
            }
            with file_path.open('w') as f:
                json.dump(trace, f)

    def metadata(self):
        return {
            'gap_seconds': self.gap_seconds,
            'hourly_rate': self.hourly_rate,
            'length': self.length,
        }

if __name__ == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace-folder', type=str, default='traces')
    parser.add_argument('--generator', type=str, default='poisson')
    parser.add_argument('--gap-seconds', type=int, default=20*60)
    parser.add_argument('--rate', type=float, default=0.1)
    parser.add_argument('--length', type=int, default=60*24*7)
    parser.add_argument('--num-traces', type=int, default=100)
    args = parser.parse_args()

    generator = GENERATORS[args.generator](args.trace_folder, args.gap_seconds, args.rate, args.length)
    generator.generate(args.num_traces)
