import configargparse

import wandb

from sky_spot import env as env_lib
from sky_spot.strategies import strategy as strategy_lib

wandb.init(project='sky-spot')

def simulate(env: env_lib.Env, strategy: strategy_lib.Strategy):
    while not strategy.task_done:
        request_type = strategy.step(env)
        env.step(request_type)
        wandb.log({
            **env.info(),
            **strategy.info(),
        })

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

    args, _ = parser.parse_known_args()

    print(args)
    print(env)
    print(strategy)

    wandb.run.name = f'{strategy.NAME}-{env.NAME}-{wandb.run.id}'
    wandb.run.save()
    wandb.config.update(args)

    simulate(env, strategy)




if __name__ == '__main__':
    main()
