# for i in 56 64 72; do
# for i in 66; do
python ./main.py --strategy=strawman \
                --env trace \
                --trace-file data/poisson/gap_600-hourly_rate_0.25 \
                --restart-overhead-hours=0.1 \
                --deadline-hours=52 \
                --task-duration-hours=48
# done

                # --trace-file data/real/ping_based/us-west-2a_v100_1.txt \
                # --env-start-hours=72 \
                # --pair-interval-hours=8 \
                # --use-avg-gain \

                # --restart-overhead-hours=0.5 \
                # --trace-file data/poisson/gap_1200-hourly_rate_0.1/1.json \
                # --trace-file data/real/analysis/1k80us-east-1c.txt \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
