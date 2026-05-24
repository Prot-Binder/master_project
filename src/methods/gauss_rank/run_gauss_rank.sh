#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../load_amber_modules.sh"
load_amber_modules

MDIN=$1
OUTDIR=$2
TOPFILE=$3
COORD_FILE=$4
REF_FILE=$5
REP=$6

mkdir -p "$OUTDIR"

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"
echo "Modules: $MODULE_SETUP_LABEL"
echo "MDIN: $MDIN"
echo "Coordinate file: $COORD_FILE"

pmemd.cuda -O \
  -i "$MDIN" \
  -o "$OUTDIR/mdout_gr_rep${REP}" \
  -p "$TOPFILE" \
  -c "$COORD_FILE" \
  -r "$OUTDIR/restrt_gr_rep${REP}" \
  -x "$OUTDIR/traj_gr_rep${REP}.nc" \
  -inf "$OUTDIR/mdinfo_gr_rep${REP}" \
  -ref "$REF_FILE"
