#!/bin/bash

module load pmemd

n=$1
window=$2

MDINDIR=$3
OUTDIR=$4
TOPDIR=$5
REPLICA_SCALING=$6
EQ_DIR=$7

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Pull Simulation for Replica $REPLICA_SCALING: Window $window... "
pmemd.cuda -O -i $MDINDIR/mdin5.rep$window -c $EQ_DIR/inpcrd$n -p $TOPDIR/prmtop$REPLICA_SCALING -r $OUTDIR/restrt5.rep$window -o $OUTDIR/mdout5.rep$window -x $OUTDIR/traj5.rep$window.nc -inf $OUTDIR/mdinfo5.rep$window
echo "done"

