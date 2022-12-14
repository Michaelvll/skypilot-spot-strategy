import argparse
import math

from sky_spot.strategies import strategy
from sky_spot.utils import ClusterType


class StrawmanStrategy(strategy.Strategy):
    NAME = 'strawman'

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        # Make decision for the gap starting from env.tick
        remaining_time = self.deadline - env.elapsed_seconds
        remaining_task_time = self.task_duration - sum(self.task_done_time)
        if has_spot:
            request_type = ClusterType.SPOT
        else:
            request_type = ClusterType.NONE

        current_cluster_type = env.cluster_type
        total_task_remaining = math.ceil((remaining_task_time + self.restart_overhead) / self.env.gap_seconds) * self.env.gap_seconds
        if total_task_remaining >= remaining_time:
            if current_cluster_type == ClusterType.SPOT:
                # Keep the spot VM until preemption
                print(f'{env.tick}: Deadline reached, keep spot until preemption')
                request_type = ClusterType.SPOT
            else:
                print(f'{env.tick}: Deadline reached, switch to on-demand')
                # We need to finish it on time by switch to on-demand
                request_type = ClusterType.ON_DEMAND
            if self.restart_overhead == 0 and has_spot:
                # We can switch to spot without cost.
                request_type = ClusterType.SPOT
        
        return request_type


    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'StrawmanStrategy':
        group = parser.add_argument_group('StrawmanStrategy')
        args, _ = parser.parse_known_args()
        return cls(args)
    

