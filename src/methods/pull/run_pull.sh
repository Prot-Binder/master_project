#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../load_amber_modules.sh"
load_amber_modules

window=$1

MDINDIR=$2
OUTDIR=$3
TOPDIR=$4
INPUT_COORD=$5

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"
echo "Modules: $MODULE_SETUP_LABEL"

printf "Running Pull Simulation for Window $window... "
pmemd.cuda -O -i $MDINDIR/mdin5.w$window -c $INPUT_COORD -p $TOPDIR/prmtop1 -r $OUTDIR/restrt5.w$window -o $OUTDIR/mdout5.w$window -x $OUTDIR/traj5.w$window.nc -inf $OUTDIR/mdinfo5.w$window
echo "done"
