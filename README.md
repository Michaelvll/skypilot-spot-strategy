# SkyPilot Spot Strategy Simulator
Experiments for SkyPilot Spot Strategy

```
python ./main.py --env-config configs/env/trace/default.yaml \
    --strategy-config configs/strategy/strawman/default.yaml \
    --config configs/exp.yaml
```

## Spot / On-demand

### Strawman
Use spot until there is no enough time to finish the job before deadline. Switch to on-demand in that case.

#### Preliminary Figures
![cluster_type](figures/strawman/trace-1-cluster-type.png)
![cost](figures/strawman/trace-1-cost.png)
![duration](figures/strawman/trace-1-duration.png)
