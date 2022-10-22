python ./main.py --strategy=on_demand \
                --env trace \
                --trace-file data/poisson/gap_1200-hourly_rate_0.1/1.json \
                --restart-overhead-hours=0.2 \
                --deadline-hours=52 \
                --task-duration-hours=48


                # --pair-interval-hours=4 \
                # --use-avg-gain \

                # --trace-file data/real/analysis/1k80us-east-1c.txt \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
