#!/bin/bash

module load pmemd

i=$1
MDINDIR=$2
OUTDIR=$3
TOPDIR=$4
REPLICA=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Umbrella Sampling for Replica $REPLICA: Window $i... "

pmemd.cuda -O -i $MDINDIR/mdin6.rep$i -o $OUTDIR/mdout6.rep$i -p $TOPDIR/prmtop$REPLICA -c $OUTDIR/restrt5.rep$i -r $OUTDIR/restrt6.rep$i -x $OUTDIR/traj6.rep$i.nc -inf $OUTDIR/mdinfo6.rep$i

echo "done"



