python ./main.py --strategy=pair_amortize \
                --use_avg_gain=True \
                --pair-interval-hours=8 \
                --env=trace
                --trace-file=data/poisson/gap_1200_hourly-rate_0.1/1.json \
                --restart-overhead-hours=0.2 \
                --deadline-hours=24 \
                --task-duration-hours=20

