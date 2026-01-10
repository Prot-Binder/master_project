#!/bin/bash

export LC_NUMERIC=C  # keep this if you need it

MDINDIR=.
TOPDIR=./top
OUTDIR=./replica_test
exclude_ranks="t38cn030,t38cn038,t38cn028,t38cn015,t38cn024,t38cn027,t38cn016,t38cn018,t38cn031,t38cn020,t38cn021,t38cn032,t38cn019,t38cn022,t38cn055,t38cn026,t38cn053"

# --cpus-per-task=1
# --gres=gpu:4 \

pull_jobid=$(sbatch \
    --job-name=rsremd \
    --nodes=1 \
    --ntasks=4 \
    --ntasks-per-node=4 \
    --cpus-per-task=1 \
    --time=1-00:00:00 \
    --exclude="$exclude_ranks" \
    --output="$OUTDIR/slurm-%j.out" \
    run_remd.sh | awk '{print $4}')

echo "Submitted REMD job with ID $pull_jobid"

# --exclude="$exclude_ranks" \
