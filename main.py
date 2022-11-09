import configargparse

import wandb

from sky_spot import env as env_lib
from sky_spot.strategies import strategy as strategy_lib
from sky_spot.utils import ClusterType

wandb.init(project='sky-spot')

def simulate(env: env_lib.Env, strategy: strategy_lib.Strategy):
    history = []
    last_request_type = ClusterType.NONE
    while not strategy.task_done:
        request_type = strategy.step()
        env.step(request_type)
        info = {
            'RequestType': last_request_type.value,
            **env.info(),
            **strategy.info(),
        }
        last_request_type = request_type
        history.append(info)
        wandb.log(info)
        if env.tick % 100 == 0:
            print(f'==> Timestamp: {env.tick}')

    strategy.step() # realize the last step
    env.step(ClusterType.NONE)
    info = {
            'RequestType': ClusterType.NONE,
            **env.info(),
            **strategy.info(),
        }
    

def main():
    parser = configargparse.ArgumentParser('Skypilot spot simulator')
    parser.add_argument('--config', type=str, default=None, is_config_file=True, required=False)
    group = parser.add_argument_group('Global options')
    group.add_argument('--deadline-hours', type=float, default=10, help='Deadline of the task in hours')
    group.add_argument('--task-duration-hours', type=float, default=10, help='Duration of the task in hours')
    group.add_argument('--restart-overhead-hours', type=float, default=0.2, help='Overhead of restarting a task in hours')
    args, _ = parser.parse_known_args()

    env = env_lib.Env.from_args(parser)
    strategy = strategy_lib.Strategy.from_args(parser)
    strategy.register_env(env)

    args, _ = parser.parse_known_args()

    print(args)
    print(env)
    print(strategy)

    trace_file = args.trace_file.split('/')[-1].split('.')[0]
    wandb.run.name = f'{strategy.name}-{env.NAME}-{trace_file}-ddl={args.deadline_hours}-dur={args.task_duration_hours}-over={args.restart_overhead_hours}'
    wandb.run.save()
    wandb.config.update(args)
    wandb.config.update({'env_metadata': env.config})
    wandb.config.update({'strategy_metadata': strategy.config})

    simulate(env, strategy)




if __name__ == '__main__':
    main()
