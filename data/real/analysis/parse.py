# %%
import copy
import json
import os
import re
from datetime import datetime, timedelta

TIME_PATTERN = re.compile(r'\[(?P<datetime>.*?)\] ')
CREATE_PATTERN = re.compile(r'\[(?P<datetime>.*?)\] Created instance (?P<instance_id>.*?) with (?P<num_gpu>1|8) GPU\(s\) of type (?P<gpu_type>.*?) in zone (?P<zone>.*?)$')
NOT_RUNNING_PATTERN = re.compile(r'\[(?P<datetime>.*?)\] Instance (?P<instance_id>.*?) not running in zone (?P<zone>.*?)')

NUM_GPUS = ['1', '8']
GPU_TYPES = ['k80', 'v100']
ZONES = ['us-east-1b', 'us-east-1c']

GAP_SECONDS = 600

with open(f'{os.path.dirname(__file__)}/log.txt', 'r') as f:
    lines = f.readlines()

instance2resource = {}
resource_create_time = {num_gpus+gpu_type+zone: [] for num_gpus in NUM_GPUS for gpu_type in GPU_TYPES for zone in ZONES}
resource_preempted_time = {num_gpus+gpu_type+zone: [] for num_gpus in NUM_GPUS for gpu_type in GPU_TYPES for zone in ZONES}
preemption_history = {num_gpus+gpu_type+zone: [] for num_gpus in NUM_GPUS for gpu_type in GPU_TYPES for zone in ZONES}

prev_datetime = None

for line in lines:
    dt = TIME_PATTERN.search(line).group('datetime')
    dt = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%fZ')
    match = CREATE_PATTERN.match(line)
    if match:
        _, instance_id, num_gpu, gpu_type, zone = match.groups()
        resource_id = num_gpu+gpu_type+zone
        print('Created', dt, resource_id)
        resource_create_time[resource_id].append(dt)
        instance2resource[instance_id] = resource_id

    match = NOT_RUNNING_PATTERN.match(line)
    if match:
        _, instance_id, zone = match.groups()
        resource_id = instance2resource.pop(instance_id)
        print('Preempted', dt, resource_id)
        resource_preempted_time[resource_id].append(dt)



# %%
for resource_id in resource_create_time:
    print(f'==> Get history for {resource_id}')
    print('create count', len(resource_create_time[resource_id]))
    print('preempted count', len(resource_preempted_time[resource_id]))
    dt = resource_create_time[resource_id][0]
    create_pt = 0
    preempt_pt = 0
    create_times = resource_create_time[resource_id]
    preempt_times = resource_preempted_time[resource_id]
    while create_pt < len(create_times) or preempt_pt < len(preempt_times) or dt < datetime.strptime('2020-03-17T15:36:55.000Z', '%Y-%m-%dT%H:%M:%S.%fZ'):
        # print(f'{resource_id} at {dt}')
        create_in_range, preempt_in_range = False, False
        next_create_time = create_times[create_pt] if create_pt < len(create_times) else None
        next_preempt_time = preempt_times[preempt_pt] if preempt_pt < len(preempt_times) else None

        if next_create_time is not None and dt <= next_create_time < dt + timedelta(seconds=GAP_SECONDS):
            create_in_range = True
            after_create = create_times[create_pt+1] if create_pt+1 < len(create_times) else dt + timedelta(seconds=GAP_SECONDS)
            assert after_create >= dt + timedelta(seconds=GAP_SECONDS), after_create
            create_pt += 1
        if next_preempt_time is not None and dt <= next_preempt_time < dt + timedelta(seconds=GAP_SECONDS):
            preempt_in_range = True
            after_preempt = preempt_times[preempt_pt+1] if preempt_pt+1 < len(preempt_times) else dt + timedelta(seconds=GAP_SECONDS)
            assert after_preempt >= dt + timedelta(seconds=GAP_SECONDS), after_preempt
            preempt_pt += 1
        if create_in_range and preempt_in_range:
            if next_create_time < next_preempt_time:
                preemption_history[resource_id].append(1)
            else:
                preemption_history[resource_id].append(0)
        elif create_in_range:
            preemption_history[resource_id].append(0)
        elif preempt_in_range:
            preemption_history[resource_id].append(1)
        else:
            last_state = preemption_history[resource_id][-1] if len(preemption_history[resource_id]) > 0 else 1
            preemption_history[resource_id].append(last_state)
        dt += timedelta(seconds=GAP_SECONDS)

    data = {
        'metadata': {
            'gap_seconds': GAP_SECONDS,
        },
        'data': preemption_history[resource_id],
    }
    with open(f'{os.path.dirname(__file__)}/{resource_id}.txt', 'w') as f:
        json.dump(data, f)

# %%
