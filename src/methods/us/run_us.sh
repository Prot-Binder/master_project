#!/bin/bash

module load pmemd

window=$1
MDINDIR=$2
OUTDIR=$3
TOPDIR=$4
PULL_DIR=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Umbrella Sampling for Window $window... "
pmemd.cuda -O -i $MDINDIR/mdin6.w$window -o $OUTDIR/mdout6.w$window -p $TOPDIR/prmtop1 -c $PULL_DIR/restrt5.w$window -r $OUTDIR/restrt6.w$window -x $OUTDIR/traj6.w$window.nc -inf $OUTDIR/mdinfo6.w$window
echo "done"