import argparse
from typing import Tuple


from sky_spot import env as env_lib
from sky_spot.strategies import strategy as strategy_lib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', default='strawman', choices=strategy_lib.Strategy.SUBCLASSES.keys())
    parser.add_argument('--env', default='trace', choices=env_lib.Env.SUBCLASSES.keys())
    args, _ = parser.parse_known_args()

    env = env_lib.Env.from_args(parser, args.env)
    strategy = strategy_lib.Strategy.from_args(parser, args.strategy)

    print(env)
    print(strategy)



if __name__ == '__main__':
    main()
