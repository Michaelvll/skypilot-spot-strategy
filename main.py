import configargparse
import copy
import json
import os

import numpy as np
import tqdm
import wandb

import sky_spot
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
    return info['Cost']
    

def main():
    parser = configargparse.ArgumentParser('Skypilot spot simulator')
    parser.add_argument('--config', type=str, default=None, is_config_file=True, required=False)
    group = parser.add_argument_group('Global options')
    group.add_argument('--deadline-hours', type=float, default=10, help='Deadline of the task in hours')
    group.add_argument('--task-duration-hours', type=float, default=10, help='Duration of the task in hours')
    group.add_argument('--restart-overhead-hours', type=float, default=0.2, help='Overhead of restarting a task in hours')
    args, _ = parser.parse_known_args()

    envs = env_lib.Env.from_args(parser)
    strategy = strategy_lib.Strategy.from_args(parser)
    args, _ = parser.parse_known_args()
    costs = []
    spot_costs = []
    cost_ratio = []

    trace_file = args.trace_file.split('/')[-2].split('.')[0]
    env_name = envs[0].NAME
    env_config = envs[0].config
    run_name = f'{strategy.name}-{env_name}-{trace_file}-ddl={args.deadline_hours}-dur={args.task_duration_hours}-over={args.restart_overhead_hours}'
    if args.env_start_hours > 0:
        run_name += f'-start={args.env_start_hours}h'
    wandb.run.name = run_name
    wandb.run.save()
    wandb.config.update(args)
    wandb.config.update({'env_metadata': env_config})
    wandb.config.update({'strategy_metadata': strategy.config})
    pbar = tqdm.tqdm(envs)
    for env in pbar:
        env.reset()
        strategy.reset()
        strategy.register_env(env)

        print(args)
        print(env)
        print(strategy)

        costs.append(simulate(env, strategy))
    
        # if len(envs) > 1:
        #     env.reset()
        #     new_args = copy.deepcopy(args)
        #     new_args.deadline_hours = 1000
        #     spot_strategy = sky_spot.strategies.only_spot.OnlySpotStrategy(new_args)
        #     spot_strategy.register_env(env)
        #     spot_costs.append(simulate(env, spot_strategy))
        #     cost_ratio.append(costs[-1] / spot_costs[-1])
        
        

        # mean_strategy_cost = np.mean(costs)
        # std_strategy_cost = np.std(costs)
        # mean_spot_cost = np.mean(spot_costs)
        # std_spot_cost = np.std(spot_costs)
        # mean_cost_ratio = np.mean(cost_ratio)
        # std_cost_ratio = np.std(cost_ratio)
        # msg = f'cost: {mean_strategy_cost:.2f}±{std_strategy_cost:.2f}; spot cost: {mean_spot_cost:.2f}±{std_spot_cost:.2f}; cost ratio: {mean_cost_ratio:.2f}±{std_cost_ratio:.2f}'
        # print('=== ' + msg + ' ===')
        # pbar.set_description(msg)
        # wandb.log({'MeanCost': mean_strategy_cost, 'StdCost': std_strategy_cost, 'MeanSpotCost': mean_spot_cost, 'StdSpotCost': std_spot_cost, 'MeanCostRatio': mean_cost_ratio, 'StdCostRatio': std_cost_ratio})

    os.makedirs('exp/', exist_ok=True)
    with open(f'exp/{run_name}', 'w') as f:
        json.dump({
            'args': args,
            'costs': costs,
        }, f)
    print('mean: ', np.mean(costs), '; std: ', np.std(costs), '; worst 1%: ', np.percentile(costs, 99), '; worst 10%: ', np.percentile(costs, 90))


if __name__ == '__main__':
    main()
