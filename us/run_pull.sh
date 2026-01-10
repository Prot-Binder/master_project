#!/bin/bash

module load pmemd

n=$1
sffx=$2

MDINDIR=$3
OUTDIR=$4
TOPDIR=$5
REPLICA=$6

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Pull Simulation for Replica $REPLICA: Window $sffx... "
pmemd.cuda -O -i $MDINDIR/mdin$sffx -c inpcrd$n -p $TOPDIR/prmtop$REPLICA -r $OUTDIR/restrt$sffx -o $OUTDIR/mdout$sffx -x $OUTDIR/traj$sffx.nc -inf $OUTDIR/mdinfo$sffx
echo "done"

