#!/bin/bash

module load pmemd

window=$1
MDINDIR=$2
OUTDIR=$3
TOPDIR=$4
REPLICA_SCALING=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Umbrella Sampling for Replica $REPLICA_SCALING: Window $window... "

pmemd.cuda -O -i $MDINDIR/mdin6.rep$window -o $OUTDIR/mdout6.rep$window -p $TOPDIR/prmtop$REPLICA_SCALING -c $OUTDIR/restrt5.rep$window -r $OUTDIR/restrt6.rep$window -x $OUTDIR/traj6.rep$window.nc -inf $OUTDIR/mdinfo6.rep$window

echo "done"



