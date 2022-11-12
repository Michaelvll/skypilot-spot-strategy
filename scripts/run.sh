for i in `seq 52 4 92`; do
python ./main.py --strategy=pair_amortize \
                --pair-interval-hours=8 \
                --use-avg-gain \
                --env trace \
                --restart-overhead-hours=0.1 \
                --trace-file data/real/ping_based/us-west-2a_v100_1.txt \
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
