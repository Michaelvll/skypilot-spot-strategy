import ray
import boto3
import time
import logging

SPOT_REQUEST_WAIT_TIME = 30
SPOT_CHECKIN_WAIT_TIME = 100


AMI_ID_MAP = {
    "us-west-2": "ami-0c09c7eb16d3e8e70",
    "us-east-1": "ami-0149b2da6ceec4bb0",
    "us-east-2": "ami-0d5bf08bc8017c83b",
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

        self.end_request = False

        logging.basicConfig(level=logging.INFO)

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
        status, ins_id, response = self.check_request_status(spot_request_id)
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
        logging.info(
            f"Launching spot instance {self.instance_type} in {self.zone}")

        self.spot_request_id = self.spot_request()
        if self.spot_request_id is None:
            return False

        # Wait for the request to be handled
        time.sleep(SPOT_REQUEST_WAIT_TIME)

        status, ins_id, response = self.check_request_status(
            self.spot_request_id)
        if status is None:
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

        assert self.spot_request_id is not None

        status, ins_id, response = self.check_request_status(
            self.spot_request_id)
        if status is None:
            return False

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
        is_alive = False
        while True:
            if self.end_request:
                logging.info('End request received, terminating all...')
                self.terminate()
                break

            if is_alive:
                is_alive = self.is_spot_alive()
            else:
                is_alive = self.launch()

            if is_alive:
                logging.info(
                    f"Spot instance {self.ins_id} in {self.zone} is alive: {is_alive}")
            else:
                logging.info("No spot instance is alive")

            time.sleep(SPOT_CHECKIN_WAIT_TIME)


def main():

    ray.init()

    instance_type = "p2.xlarge"
    zones = ["us-west-2a", "us-east-1a"]

    inss = []
    handles = []
    # Test launch
    for zone in zones:
        ins = SpotInstance.options(
            max_concurrency=2).remote(instance_type, zone)
        h = ins.main_loop.remote()

        inss.append(ins)
        handles.append(h)

    time.sleep(600)

    for ins in inss:
        ins.send_terminate_sig.remote()

    ray.get(handles)


if __name__ == "__main__":
    main()
