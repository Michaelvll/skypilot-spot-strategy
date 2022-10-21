import argparse

from sky_spot.strategies import strategy
from sky_spot.utils import ClusterType


class StrawmanStrategy(strategy.Strategy):
    NAME = 'strawman'

    def __init__(self, args):
        super().__init__(args.deadline_hours, args.task_duration_hours, args.restart_overhead_hours)

    def step(self) -> ClusterType:
        assert self.env is not None, 'Environment not registered'
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
        remaining_time = self.deadline - env.elapsed_seconds
        remaining_task_time = self.task_duration - sum(self.task_done_time)
        if has_spot:
            request_type = ClusterType.SPOT
        else:
            request_type = ClusterType.NONE

        current_cluster_type = env.cluster_type
        if remaining_task_time + self.restart_overhead >= remaining_time:
            if current_cluster_type == ClusterType.SPOT:
                # Keep the spot VM until preemption
                print(f'{env.tick}: Deadline reached, keep spot until preemption')
                request_type = ClusterType.SPOT
            else:
                print(f'{env.tick}: Deadline reached, switch to on-demand')
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
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'StrawmanStrategy':
        group = parser.add_argument_group('StrawmanStrategy')
        args, _ = parser.parse_known_args()
        return cls(args)
    

