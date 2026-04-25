#!/bin/bash

module load pmemd

NUM_REPS=$1
INPUT_FILE=$2
NUM_GPUS=$3

if [ -z "${CUDA_VISIBLE_DEVICES:-}" ] && [ "$NUM_GPUS" -gt 0 ]; then
  export CUDA_VISIBLE_DEVICES=$(seq -s, 0 $((NUM_GPUS-1)))
fi


echo "===INFORMATION==="
echo "Script dir:  $(dirname $0)"
echo "Current dir: $PWD"
echo "Argument:    $1"
echo "Num GPUs:    $NUM_GPUS"
echo "Amberhome:   $AMBERHOME"
echo "Python:      `type python`"
echo "CUDA home:   $CUDA_HOME"
echo "Visible GPU: ${CUDA_VISIBLE_DEVICES:-<unset>}"
echo "GPU Info:    $(nvidia-smi -L)"
echo "Nodes:       $SLURM_JOB_NODELIST"
echo "======"

        mpirun --oversubscribe -n $NUM_REPS pmemd.cuda_SPFP.MPI -O -ng $NUM_REPS -groupfile $INPUT_FILE -rem 3


echo "Done"
