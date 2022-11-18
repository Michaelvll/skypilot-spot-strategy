for i in 48.2 48.5 49 50 51 52 56 60 64 68 72 76; do
# for i in 1000; do
python ./main.py --strategy=strawman \
                --env trace \
                --restart-overhead-hours=0.1 \
                --trace-file data/real/ping_based/us-west-2a_v100_1.txt \
                --env-start-hours=72 \
                --deadline-hours=$i \
                --task-duration-hours=48
done


                # --pair-interval-hours=8 \
                # --use-avg-gain \
                # --restart-overhead-hours=0.5 \
                # --trace-file data/poisson/gap_1200-hourly_rate_0.1/1.json \
                # --trace-file data/real/analysis/1k80us-east-1c.txt \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
