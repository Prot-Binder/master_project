#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../load_amber_modules.sh"
load_amber_modules

MDINDIR=$1
OUTDIR=$2
TOPDIR=$3
INPUT_COORD=$4
REPLICA=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"
echo "Modules: $MODULE_SETUP_LABEL"

printf "Running Equilibrium Simulation for RS-REMD:"
pmemd.cuda -O -i $MDINDIR/eq -c $INPUT_COORD -p $TOPDIR/prmtop$REPLICA -r $OUTDIR/restrt_rsremd_eq -o $OUTDIR/mdout_rsremd_eq -x $OUTDIR/traj_rsremd_eq.nc -inf $OUTDIR/mdinfo_rsremd_eq
echo "done"
