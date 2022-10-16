import configargparse

import plotly
import wandb

from sky_spot import env as env_lib
from sky_spot.strategies import strategy as strategy_lib

wandb.init(project='sky-spot')

def plot_step(env, history, name='RequestType'):
    request_types = [h[name] for h in history]
    plot_trace = {
        "x": [env.gap_seconds * i / 3600.0 for i in range(len(request_types))],
        "y": request_types,
        "line": {"shape": 'hv'},
        "mode": 'lines',
        "name": 'value',
        "type": 'scatter'
        }
    div = plotly.offline.plot({'data': [plot_trace]}, output_type='div', auto_open=False)
    wandb.log({f'Type/{name}': wandb.Html(div)})


def simulate(env: env_lib.Env, strategy: strategy_lib.Strategy):
    history = []
    while not strategy.task_done:
        request_type = strategy.step(env)
        env.step(request_type)
        info = {
            'RequestType': request_type.value,
            **env.info(),
            **strategy.info(),
        }
        history.append(info)
        wandb.log(info)
        if env.timestamp % 100 == 0:
            print(f'==> Timestamp: {env.timestamp}')
    # plot_step(env, history, name='ClusterType')
    

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

    trace_file = args.trace_file.split('/')[-1].split('.')[0]
    wandb.run.name = f'{strategy.NAME}-{env.NAME}-{trace_file}-ddl={args.deadline_hours}-dur={args.task_duration_hours}-over={args.restart_overhead_hours}'
    wandb.run.save()
    wandb.config.update(args)
    wandb.config.update({'env_metadata': env.config})
    wandb.config.update({'strategy_metadata': strategy.config})

    simulate(env, strategy)




if __name__ == '__main__':
    main()
