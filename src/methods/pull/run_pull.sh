#!/bin/bash

module load pmemd

window=$1

MDINDIR=$2
OUTDIR=$3
TOPDIR=$4
EQ_DIR=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Pull Simulation for Replica $REPLICA_SCALING: Window $window... "
pmemd.cuda -O -i $MDINDIR/mdin5.rep$window -c $EQ_DIR/inpcrd4 -p $TOPDIR/prmtop1 -r $OUTDIR/restrt5.rep$window -o $OUTDIR/mdout5.rep$window -x $OUTDIR/traj5.rep$window.nc -inf $OUTDIR/mdinfo5.rep$window
echo "done"