import copy
import json
import os
from typing import List

class Trace:
    def __init__(self, gap_seconds: int, data: List[int]):
        self.gap_seconds = gap_seconds
        self._data = copy.copy(data)

    @classmethod
    def from_file(cls, trace_file: str):
        with open(trace_file, 'r') as f:
            trace_data = json.load(f)
        trace = Trace(trace_data['metadata']['gap_seconds'], trace_data['data'])
        return trace
    
    def __getitem__(self, index: int):
        return self._data[index]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        for item in self._data:
            yield item
    


class TraceDataset:
    def __init__(self, trace_folder: str):
        self.trace_folder = trace_folder

        for trace_file in os.listdir(self.trace_folder):
            trace = Trace.from_file(os.path.join(self.trace_folder, trace_file))
            self.traces.append(trace)
        assert all(trace.gap_seconds == self.traces[0].gap_seconds for trace in self.traces), 'All traces must have the same time gap'
        self.gap_seconds = self.traces[0].gap_seconds


    def __len__(self):
        return len(self.traces)

    def __getitem__(self, index: int):
        return self.traces[index]

    def __iter__(self):
        for trace in self.traces:
            yield trace
