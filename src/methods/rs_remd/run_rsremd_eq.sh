#!/bin/bash

module load pmemd

MDINDIR=$1
OUTDIR=$2
TOPDIR=$3
EQ_DIR=$4
REPLICA=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

printf "Running Equilibrium Simulation for RS-REMD:"
pmemd.cuda -O -i $MDINDIR/eq -c $EQ_DIR/inpcrd4 -p $TOPDIR/prmtop$REPLICA -r $OUTDIR/restrt_rsremd_eq -o $OUTDIR/mdout_rsremd_eq -x $OUTDIR/traj_rsremd_eq.nc -inf $OUTDIR/mdinfo_rsremd_eq
echo "done"