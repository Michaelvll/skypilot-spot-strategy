import ray
import boto3
from datetime import datetime
import time
import json

import logging
logging.basicConfig(level=logging.INFO)

SPOT_REQUEST_WAIT_TIME = 30
SPOT_CHECKIN_WAIT_TIME = 180


AMI_ID_MAP = {
    "us-west-2": "ami-0c09c7eb16d3e8e70",
    "us-east-1": "ami-0149b2da6ceec4bb0",
    "us-east-2": "ami-0d5bf08bc8017c83b",
}

ZONE_ID_MAP = {
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


@ray.remote
class SpotInstance:
    def __init__(self, instance_type, zone):
        self.instance_type = instance_type
        self.zone = zone

        self.region = zone[:-1]

        self.boto_client = boto3.client("ec2", region_name=self.region)
        self.spot_request_id = None
        self.ins_id = None

        self.is_alive = False
        self.end_request = False

        logging.basicConfig(level=logging.INFO)

    def get_is_alive(self):
        return self.is_alive

    def get_zone(self):
        return self.zone

    def get_ins_id(self):
        return self.ins_id

    def spot_request(self):
        response = self.boto_client.request_spot_instances(
            InstanceCount=1,
            LaunchSpecification={
                "ImageId": AMI_ID_MAP[self.region],
                "InstanceType": self.instance_type,
                "Placement": {
                    "AvailabilityZone": self.zone,
                },
            },
            Type="one-time",
        )

        try:
            spot_request_id = response["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
            logging.info(f"Spot request id: {spot_request_id}")
        except Exception as e:
            logging.info("request_spot_instances failed")
            logging.info(response)
            return None
        return spot_request_id

    def cancel_spot_request(self, spot_request_id):
        status, ins_id, _ = self.check_request_status(spot_request_id)
        if status is None:
            return

        if ins_id is not None:
            logging.info(f'Terminating spot instance {ins_id}...')
            self.boto_client.terminate_instances(InstanceIds=[ins_id])

        logging.info(f'Cleaning up spot request {spot_request_id}...')
        self.boto_client.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[spot_request_id])

    def check_request_status(self, spot_request_id):
        response = self.boto_client.describe_spot_instance_requests(
            SpotInstanceRequestIds=[spot_request_id])

        ins_id = None
        try:
            # example: {'Code': 'fulfilled', 'Message': 'Your spot request is fulfilled.'...)}
            status = response['SpotInstanceRequests'][0]['Status']
            ins_id = response['SpotInstanceRequests'][0].get(
                'InstanceId', None)
        except Exception as e:
            logging.info("describe_spot_instance_requests failed")
            logging.info(response)
            return None, None, None

        return status, ins_id, response

    def launch(self):
        """Return True if spot instance is launched successfully, False if it fails"""
        logging.info(
            f"Launching spot instance {self.instance_type} in {self.zone}")

        self.spot_request_id = self.spot_request()
        if self.spot_request_id is None:
            return False

        # Wait for the request to be handled
        time.sleep(SPOT_REQUEST_WAIT_TIME)

        status, ins_id, _ = self.check_request_status(
            self.spot_request_id)
        if status is None:
            self.cancel_spot_request(self.spot_request_id)
            self.spot_request_id = None
            return False

        if status['Code'] != 'fulfilled':
            logging.info(f"Spot request failed with {status}")

            self.cancel_spot_request(self.spot_request_id)
            self.spot_request_id = None
            return False

        self.ins_id = ins_id

        return True

    def is_spot_alive(self):
        """Return True if spot instance is alive, False if it is preempted, None if network error happens"""
        assert self.spot_request_id is not None

        status, ins_id, response = self.check_request_status(
            self.spot_request_id)
        if status is None:
            return None

        if status['Code'] != 'fulfilled':
            logging.info(f'Spot instance is preempted {response}')

            self.cancel_spot_request(self.spot_request_id)
            self.spot_request_id = None
            return False

        return True

    def terminate(self):
        if self.spot_request_id is None:
            return

        self.cancel_spot_request(self.spot_request_id)

    def send_terminate_sig(self):
        self.end_request = True

    def main_loop(self):
        self.is_alive = False
        while True:
            if self.end_request:
                logging.info('End request received, terminating all...')
                self.terminate()
                break

            # is_alive can be None when network error happens
            if self.is_alive is None or self.is_alive:
                self.is_alive = self.is_spot_alive()
            else:
                self.is_alive = self.launch()

            if self.is_alive is None:
                logging.info(
                    "Failed to get spot instance status due to network error")
            elif self.is_alive:
                logging.info(
                    f"Spot instance {self.ins_id} in {self.zone} is alive: {self.is_alive}")
            else:
                logging.info("Spot instance is not alive")

            time.sleep(SPOT_CHECKIN_WAIT_TIME)


def get_placement_score(instance_type, zone, capacity):
    region = zone[:-1]
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.get_spot_placement_scores(InstanceTypes=[
        instance_type], TargetCapacity=capacity, SingleAvailabilityZone=True, RegionNames=[region])

    try:
        for score in response["SpotPlacementScores"]:
            if score["AvailabilityZoneId"] == ZONE_ID_MAP[zone]:
                return score["Score"]
    except Exception as e:
        logging.info("get_spot_placement_scores failed")
        logging.info(response)
        return None

    return None


def get_placement_score_list(instance_type, zone, capacity_list):
    score_list = []
    for capacity in capacity_list:
        score = get_placement_score(instance_type, zone, capacity)
        score_list.append(score)
    return score_list


def get_spot_price(instance_type, zone):
    region = zone[:-1]
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_spot_price_history(
        InstanceTypes=[instance_type], ProductDescriptions=["Linux/UNIX (Amazon VPC)"], AvailabilityZone=zone)
    try:
        return response["SpotPriceHistory"][0]["SpotPrice"]
    except Exception as e:
        logging.info("describe_spot_price_history failed")
        logging.info(response)
        return None


def main():

    ray.init()

    # g5.4xlarge
    # instance_type = "g5.4xlarge"
    # zones = ["us-west-2a", "us-east-1b"]
    # ins_count = 2

    # p2.xlarge
    # instance_type = "p2.xlarge"
    # zones = ["us-west-2a", "us-east-1b", "us-east-2a"]
    # ins_count = 4

    # p3.2xlarge
    instance_type = "p3.2xlarge"
    zones = ["us-west-2a", "us-east-2a"]
    ins_count = 2

    inss = []
    handles = []
    # Test launch
    for i in range(ins_count):
        for zone in zones:
            ins = SpotInstance.options(
                max_concurrency=2).remote(instance_type, zone)
            h = ins.main_loop.remote()

            inss.append(ins)
            handles.append(h)

    for i in range(3000):
        time.sleep(SPOT_CHECKIN_WAIT_TIME)
        date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        stats = {"date": date}

        for zone in zones:
            stats[zone] = {}
            stats[zone]["ins_ids"] = []
            stats[zone]["pool_size"] = 0
            stats[zone]["score"] = get_placement_score_list(
                instance_type, zone, [1, 3, 10, 50])
            stats[zone]["price"] = get_spot_price(instance_type, zone)
        for ins in inss:
            zone = ray.get(ins.get_zone.remote())
            alive = ray.get(ins.get_is_alive.remote())
            ins_id = ray.get(ins.get_ins_id.remote())
            if alive == True:
                stats[zone]["pool_size"] += 1
                stats[zone]["ins_ids"].append(ins_id)

        logging.info("==========")

        with open(f"stats-{instance_type}-{ins_count}.json", "a") as f:
            f.write(json.dumps(stats)+"\n")

        logging.info(stats)
        logging.info("==========")

    for ins in inss:
        ins.send_terminate_sig.remote()

    ray.get(handles)


if __name__ == "__main__":
    main()
