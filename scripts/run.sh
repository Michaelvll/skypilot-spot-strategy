python ./main.py --strategy=pair_amortize \
                --pair-interval-hours=8 \
                --use-avg-gain \
                --env trace \
                --trace-file data/poisson/gap_1200-hourly_rate_0.5/1.json \
                --restart-overhead-hours=0.2 \
                --deadline-hours=104 \
                --task-duration-hours=96



                # --pair-interval-hours=8 \
                # --use-avg-gain \
