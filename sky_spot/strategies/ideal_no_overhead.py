import argparse
import typing

from sky_spot.strategies import strategy
from sky_spot.utils import ClusterType

if typing.TYPE_CHECKING:
    from sky_spot import env

class IdealNoOverheadStrategy(strategy.Strategy):
    NAME = 'ideal_no_overhead'
    def register_env(self, env):
        super().register_env(env)

        self.trace = env.get_trace_before_end(self.deadline)
        total_spot_gaps = sum(preempted == 0 for preempted in self.trace)
        remaining_on_demand_time = self.task_duration - total_spot_gaps * env.gap_seconds
        self.remaining_on_demand_time = max(0, remaining_on_demand_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.task_done:
            return ClusterType.NONE
        
        if has_spot:
            return ClusterType.SPOT
        
        if self.remaining_on_demand_time > 0:
            self.remaining_on_demand_time -= self.env.gap_seconds
            return ClusterType.ON_DEMAND
        
        return ClusterType.NONE

    def info(self):
        return {
            'Task/Done(seconds)': self.task_done_time[-1],
            'Task/Remaining(seconds)': self.task_duration - sum(self.task_done_time),
        }

    @classmethod
    def _from_args(cls, parser: 'argparse.ArgumentParser') -> 'IdealNoOverheadStrategy':
        group = parser.add_argument_group('OnDemandStrategy')
        args, _ = parser.parse_known_args()
        return cls(args)

