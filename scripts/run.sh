# for i in 56 64 72; do
# for i in 66; do
# for rate in 0.1 0.2 0.25 0.3 0.35 0.4 0.45 0.5 0.55 0.6; do
python ./main.py --strategy=only_spot \
                --env trace \
                --trace-file data/real/ping_based/random_start_time/us-west-2a_v100_1 \
                --restart-overhead-hours=0.1 \
                --deadline-hours=1000 \
                --task-duration-hours=48 > ./demand-$rate.out 2>&1 &
# done
# done

                # --trace-file data/poisson/gap_600-hourly_rate_$rate \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
                # --trace-file data/real/ping_based/us-west-2a_v100_1.txt \
                # --env-start-hours=72 \

                # --restart-overhead-hours=0.5 \
                # --trace-file data/poisson/gap_1200-hourly_rate_0.1/1.json \
                # --trace-file data/real/analysis/1k80us-east-1c.txt \
                # --pair-interval-hours=8 \
                # --use-avg-gain \
