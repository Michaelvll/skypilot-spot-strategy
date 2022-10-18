import argparse
import math
import typing

from sky_spot.strategies import strategy
from sky_spot.utils import ClusterType

if typing.TYPE_CHECKING:
    from sky_spot import env

class PairAmortizeStrategy(strategy.Strategy):
    NAME = 'pair_amortize'

    def __init__(self, args):
        super().__init__(args.deadline_hours, args.task_duration_hours, args.restart_overhead_hours)

        self.pair_interval = args.pair_interval_hours * 3600
        self.num_pairs = math.ceil(self.deadline / self.pair_interval)

        self.pair_task_duration = 1.0 * self.task_duration / self.num_pairs
        self.pair_gap_counts = None
        self.pair_index = 0
        self.previous_gain_seconds = 0
        
    def register_env(self, env: 'env.Env'):
        super().register_env(env)

        self.pair_gap_counts =  int(round(self.pair_interval / env.gap_seconds, 0))
        assert abs(self.pair_gap_counts * env.gap_seconds - self.pair_interval) < 1e-4, (self.pair_gap_counts, env.gap_seconds)
        

    def step(self) -> ClusterType:
        # Realize the information of the last gap
        env = self.env
        last_cluster_type, has_spot = env.observe()
        if last_cluster_type == ClusterType.NONE:
            self.task_done_time.append(0)
        else:
            task_done_time = max(env.gap_seconds - self.remaining_restart_overhead, 0)
            self.remaining_restart_overhead -= (env.gap_seconds - task_done_time)
            
            remaining_task_time = self.task_duration - sum(self.task_done_time)
            task_done_time = min(task_done_time, remaining_task_time)
            self.task_done_time.append(task_done_time)


        # Make decision for the gap starting from env.tick
        pair_end_seconds = (self.pair_index + 1) * self.pair_interval
        if pair_end_seconds - self.env.elapsed_seconds < 1e-2:
            self.pair_index += 1
            last_pair_gain = sum(self.task_done_time[-self.pair_gap_counts:]) - self.pair_task_duration
            print(f'==> {self.env.tick}: Pair {self.pair_index} starts (last gain: {last_pair_gain})')
            self.previous_gain_seconds += last_pair_gain

        assert self.pair_index < self.num_pairs, ('Pair index out of range', self.pair_index, self.num_pairs)

        pair_start_gap_index = self.pair_index * self.pair_gap_counts
        pair_end_gap_index = (self.pair_index + 1) * self.pair_gap_counts
        pair_end_seconds = pair_end_gap_index * self.env.gap_seconds


        pair_remaining_time = pair_end_seconds - env.elapsed_seconds
        remaining_task_time = self.pair_task_duration - sum(self.task_done_time[pair_start_gap_index:])
        if has_spot:
            request_type = ClusterType.SPOT
        else:
            request_type = ClusterType.NONE


        switch_task_remaining = remaining_task_time + self.restart_overhead
        pair_available_time = pair_remaining_time + self.previous_gain_seconds
        if switch_task_remaining >= pair_available_time:
            print(f'{env.tick}: Deadline reached, switch to on-demand '
                f'(task remaining: {switch_task_remaining/3600:.2f}, pair avilable: {pair_available_time/3600:.2f})')
            # We need to finish it on time by switch to on-demand
            request_type = ClusterType.ON_DEMAND
        
        current_cluster_type = last_cluster_type
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            current_cluster_type = ClusterType.NONE
        if current_cluster_type != request_type and request_type != ClusterType.NONE:
            self.remaining_restart_overhead = self.restart_overhead

        return request_type

    def info(self):
        return {
            'Task/Done(seconds)': self.task_done_time[-1],
            'Task/Remaining(seconds)': self.task_duration - sum(self.task_done_time),
        }

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'PairAmortizeStrategy':
        group = parser.add_argument_group('PairAmortizeStrategy')
        group.add_argument('--pair-interval-hours', type=int, default=1)
        args, _ = parser.parse_known_args()
        return cls(args)
    
    @property
    def name(self):
        return f'{self.NAME}_{self.pair_interval/3600}h'

    @property
    def config(self):
        return dict(
            super().config,
            num_pairs=self.num_pairs,
            pair_interval=self.pair_interval,
            pair_task_duration=self.pair_task_duration,
            pair_gap_counts=self.pair_gap_counts,
        )


