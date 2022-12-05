# Adopted from https://github.com/stanford-futuredata/training_on_a_dime/blob/master/scripts/aws/availability.py
import argparse
from datetime import datetime
import signal
import json
import os
import subprocess
import sys
import time
import json

import ray


configs = {}

CLOCK = 0
SLEEP_TIMEOUT = 600
instance_types = {
    ("v100", 1): "p3.2xlarge",
    ("v100", 4): "p3.8xlarge",
    ("v100", 8): "p3.16xlarge",
    ("k80", 1): "p2.xlarge",
    ("k80", 8): "p2.8xlarge",
    ("k80", 16): "p2.16xlarge",
    ("t4", 1): "g4dn.2xlarge",
    ("t4", 4): "g4dn.12xlarge",
    ("t4", 8): "g4dn.metal",
}

# This mapping is only valid for my account.
zone_id_map = {
    "us-west-2a": "usw2-az1",
    "us-west-2b": "usw2-az2",
    "us-west-2c": "usw2-az3",
    "us-east-1a": "use1-az2",
    "us-east-1b": "use1-az4",
    "us-east-1c": "use1-az6",
    "us-east-1d": "use1-az1",
    "us-east-1e": "use1-az3",
    "us-east-1f": "use1-az5",
    "us-east-2a": "use2-az1",
    "us-east-2b": "use2-az2",
    "us-east-2c": "use2-az3",
}

ami_id_map = {
    "us-west-2": "ami-0c09c7eb16d3e8e70",
    "us-east-1": "ami-0149b2da6ceec4bb0",
    "us-east-2": "ami-0d5bf08bc8017c83b",
}


def signal_handler(sig, frame):
    global configs
    # Clean up all instances when program is interrupted.
    for (zone, gpu_type, num_gpus) in configs:
        [instance_id, _] = configs[(zone, gpu_type, num_gpus)]
        if instance_id is not None:
            delete_spot_instance(zone, instance_id)
    sys.exit(0)


def delete_spot_instance(zone, instance_id):
    region = zone[:-1]
    command = f"aws ec2 terminate-instances --instance-ids {instance_id} --region {region}"
    try:
        output = subprocess.check_output(command, shell=True)
        print("[%s] Successfully deleted instance %s" % (
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'), instance_id))
    except:
        return


def get_placement_score(gpu_type, num_vm, zone_id, region):
    placement_cmd = (
        f"aws ec2 get-spot-placement-scores --target-capacity "
        f"{num_vm} --region-names {region} --cli-input-json "
        f"file://placement-score-{gpu_type}.json")
    score = -1
    for i in range(3):
        try:
            output = subprocess.check_output(
                placement_cmd, shell=True).decode()
            ret = json.loads(output)
            for elem in ret["SpotPlacementScores"]:
                if elem["AvailabilityZoneId"] == zone_id:
                    score = elem["Score"]
            if score != -1:
                break
        except Exception as e:
            print(type(e), e)
        time.sleep(0.5)
    return score


def get_placement_score_list(gpu_type, num_vm_list, zone_id, region):
    score_list = []
    for num_vm in num_vm_list:
        score = get_placement_score(gpu_type, num_vm, zone_id, region)
        score_list.append(score)
    return score_list


def get_spot_price(instance_type, zone, region):
    price = -1
    price_cmd = (
        f"""aws ec2 describe-spot-price-history """
        f"""--instance-types {instance_type} --product-description "Linux/UNIX" """
        f"""--max-items 1 --availability-zone {zone} --region {region}""")
    for i in range(3):
        try:
            output = subprocess.check_output(price_cmd, shell=True).decode()
            ret = json.loads(output)
            price = ret["SpotPriceHistory"][0]["SpotPrice"]
        except Exception as e:
            print(type(e), e)
        time.sleep(0.5)

    return price


def cancel_spot_request(spot_instance_request_id, region):
    for i in range(5):
        try:
            command = (
                f"aws ec2 cancel-spot-instance-requests "
                f"--spot-instance-request-ids {spot_instance_request_id} "
                f"--region {region}")

            subprocess.check_output(command, shell=True)
            print("[%s] Successfully cancelled spot request %s" % (
                datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'), spot_instance_request_id))
            return
        except Exception as e:
            print('Failed to cancel spot request %s' %
                  spot_instance_request_id)
            print(type(e), e)
            continue


@ray.remote(num_cpus=0)
def launch_spot_instance(zone, gpu_type, num_gpus):
    region = zone[:-1]
    zone_id = zone_id_map[zone]
    instance_type = instance_types[(gpu_type, num_gpus)]
    ami_id = ami_id_map[region]

    with open("specification.json.template", 'r') as f1, open(f"specification-{zone}-{gpu_type}-{num_gpus}.json", 'w') as f2:
        template = f1.read()
        specification_file = template % (ami_id, instance_type, zone)
        f2.write(specification_file)

    with open("placement-score.json.template", 'r') as f1, open(f"placement-score-{gpu_type}.json", 'w') as f2:
        template = f1.read()
        specification_file = template % (instance_type)
        f2.write(specification_file)

    num_vm_list = [1, 3, 10, 50]
    scores_list = get_placement_score_list(
        gpu_type, num_vm_list, zone_id, region)

    price = get_spot_price(instance_type, zone, region)

    command = (
        f"""aws ec2 request-spot-instances --instance-count 1 """
        f"""--type one-time  --region {region} --launch-specification """
        f"""file://specification-{zone}-{gpu_type}-{num_gpus}.json""")
    instance_id = None
    spot_instance_request_id = None
    try:
        try:
            print("[%s] Trying to create instance with %d GPU(s) of type %s in zone %s" % (
                datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                num_gpus, gpu_type, zone), file=sys.stderr)
            output = subprocess.check_output(command, shell=True).decode()
            return_obj = json.loads(output)
            spot_instance_request_id = return_obj["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
            command = (
                f"aws ec2 describe-spot-instance-requests "
                f"--spot-instance-request-id {spot_instance_request_id} --region {region}")

            time.sleep(30)
            output = subprocess.check_output(command, shell=True).decode()
            return_obj = json.loads(output)
            print(return_obj)
            instance_id = return_obj["SpotInstanceRequests"][0]["InstanceId"]
            print("[%s] Created instance %s with %d GPU(s) of type %s in zone %s" % (
                datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                instance_id, num_gpus, gpu_type, zone))
            return (True, scores_list, price)
        except Exception as e:
            print(type(e), e)
            pass

        print("[%s] Instance with %d GPU(s) of type %s creation in zone %s failed" % (
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'), num_gpus, gpu_type, zone))
        return (False, scores_list, price)
    finally:
        if instance_id is not None:
            delete_spot_instance(zone, instance_id)
        if spot_instance_request_id is not None:
            cancel_spot_request(spot_instance_request_id, region)
        print('ready')


def main(args):
    global configs
    global CLOCK
    ray.init()

    for zone in args.zones:
        for gpu_type in args.gpu_types:
            for num_gpus in args.all_num_gpus:
                configs[(zone, gpu_type, num_gpus)] = [None, False]

    start_date = datetime.now().strftime('%Y-%m-%dT%H-%M')
    folder = f'traces/{start_date}'
    os.makedirs(folder, exist_ok=True)
    while True:
        print(f"Clock: {CLOCK}")
        # Spin in a loop; try to launch spot instances of particular type if
        # not running already. Check on status of instances, and update to
        # "not running" as needed.
        workers = [launch_spot_instance.remote(*config) for config in configs]
        dt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        time.sleep(SLEEP_TIMEOUT)
        ready, not_ready = ray.wait(
            workers, timeout=0.1, num_returns=len(workers))
        assert len(not_ready) == 0, (ready, not_ready)
        for i, (zone, gpu_type, num_gpus) in enumerate(configs):
            ret = ray.get(ready[i])
            fail, score, price = int(not ret[0]), ret[1], ret[2]
            print(f'{CLOCK};{dt};{fail};{score};{price}')
            with open(f'{folder}/{zone}_{gpu_type}_{num_gpus}.txt', 'a') as f:
                print(f'{CLOCK};{dt};{fail};{score};{price}', file=f)
        CLOCK += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get AWS spot instance availability')
    parser.add_argument('--zones', type=str, nargs='+',
                        # default=["us-west-2a", "us-west-2b", "us-west-2c", "us-east-1a", "us-east-1b", "us-east-1e", "us-east-1f", "us-east-2a", "us-east-2b"],
                        default=["us-west-2a", "us-west-2b", "us-west-2c", "us-east-1a", "us-east-1b",
                                 "us-east-1c", "us-east-1d", "us-east-2a", "us-east-2b", "us-east-2c"],
                        help='AWS availability zones')
    parser.add_argument('--gpu_types', type=str, nargs='+',
                        # default=["v100"],
                        default=["k80"],
                        help='GPU types')
    parser.add_argument('--all_num_gpus', type=int, nargs='+',
                        default=[1],
                        help='Number of GPUs per instance')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    main(args)
