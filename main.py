import configargparse


from sky_spot import env as env_lib
from sky_spot.strategies import strategy as strategy_lib

def main():
    parser = configargparse.ArgumentParser('Skypilot spot simulator')
    args, _ = parser.parse_known_args()

    env = env_lib.Env.from_args(parser)
    strategy = strategy_lib.Strategy.from_args(parser)

    print(env)
    print(strategy)



if __name__ == '__main__':
    main()
