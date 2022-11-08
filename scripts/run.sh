python ./main.py --strategy=ideal_no_overhead \
                --env trace \
                --trace-file data/real/ping_based/us-west-2a_v100_1.txt \
                --deadline-hours=56 \
                --task-duration-hours=48



                # --pair-interval-hours=8 \
                # --use-avg-gain \
                # --restart-overhead-hours=0.5 \
                # --trace-file data/poisson/gap_1200-hourly_rate_0.1/1.json \
                # --trace-file data/real/analysis/1k80us-east-1c.txt \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
