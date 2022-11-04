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
        super().__init__(args)

        self.pair_interval = args.pair_interval_hours * 3600
        self.num_pairs = math.ceil(self.deadline / self.pair_interval)

        self.use_avg_gain = args.use_avg_gain

        self.pair_task_duration = 1.0 * self.task_duration / self.num_pairs
        self.pair_gap_counts = None
        self.pair_index = 0

        self.previous_gain_seconds = 0
        self.avg_gain = 0
        
    def register_env(self, env: 'env.Env'):
        super().register_env(env)

        self.pair_gap_counts =  int(round(self.pair_interval / env.gap_seconds, 0))
        assert abs(self.pair_gap_counts * env.gap_seconds - self.pair_interval) < 1e-4, (self.pair_gap_counts, env.gap_seconds)
        

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        # Make decision for the gap starting from env.tick
        pair_end_seconds = (self.pair_index + 1) * self.pair_interval
        if pair_end_seconds - self.env.elapsed_seconds < 1e-2:
            self.pair_index += 1
            last_pair_gain = sum(self.task_done_time[-self.pair_gap_counts:]) - self.pair_task_duration
            self.previous_gain_seconds += last_pair_gain
            print(f'==> {self.env.tick}: Pair {self.pair_index} starts (last gain: {last_pair_gain/3600:.2f}, previous_gain: {self.previous_gain_seconds/3600:.2f})')
            print(f'==> Task done time: {sum(self.task_done_time)/3600:.2f}')
            self.avg_gain = self.previous_gain_seconds / (self.num_pairs - self.pair_index)

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


        switch_task_remaining = (remaining_task_time + self.restart_overhead)
        if self.pair_index == self.num_pairs - 1:
            switch_task_remaining = math.ceil(switch_task_remaining / self.env.gap_seconds) * self.env.gap_seconds
        if self.use_avg_gain:
            pair_available_time = pair_remaining_time + self.avg_gain
        else:
            pair_available_time = pair_remaining_time + self.previous_gain_seconds
        current_cluster_type = env.cluster_type
        total_task_remaining = math.ceil((self.task_duration - sum(self.task_done_time) + self.restart_overhead) / self.env.gap_seconds) * self.env.gap_seconds
        if switch_task_remaining >= pair_available_time or total_task_remaining >= self.deadline - env.elapsed_seconds:
            if current_cluster_type == ClusterType.SPOT:
                # Keep the spot VM until preemption
                request_type = ClusterType.SPOT
            else:
                print(f'{env.tick}: Deadline reached, switch to on-demand '
                    f'(task remaining: {switch_task_remaining/3600:.2f}, pair avilable: {pair_available_time/3600:.2f})')
                # We need to finish it on time by switch to on-demand
                request_type = ClusterType.ON_DEMAND
        
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
        group.add_argument('--use-avg-gain', action='store_true')
        args, _ = parser.parse_known_args()
        return cls(args)
    
    @property
    def name(self):
        use_avg_str = '_avg' if self.use_avg_gain else ''
        return f'{self.NAME}{use_avg_str}_{self.pair_interval/3600}h'

    @property
    def config(self):
        return dict(
            super().config,
            num_pairs=self.num_pairs,
            pair_interval=self.pair_interval,
            pair_task_duration=self.pair_task_duration,
            pair_gap_counts=self.pair_gap_counts,
            use_avg_gain=self.use_avg_gain,
        )


