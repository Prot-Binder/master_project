#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../load_amber_modules.sh"
load_amber_modules

NUM_REPS=$1
INPUT_FILE=$2

echo "===INFORMATION==="
echo "Script dir:  $(dirname "$0")"
echo "Current dir: $PWD"
echo "Replicas:    $NUM_REPS"
echo "Amberhome:   $AMBERHOME"
echo "Python:      $(type python)"
echo "CUDA home:   $CUDA_HOME"
echo "GPU Info:    $(nvidia-smi -L)"
echo "Nodes:       $SLURM_JOB_NODELIST"
echo "Modules:     $MODULE_SETUP_LABEL"
echo "======"

mpirun --oversubscribe -n "$NUM_REPS" pmemd.cuda_SPFP.MPI -O -ng "$NUM_REPS" -groupfile "$INPUT_FILE" -rem 3

echo "Done"
