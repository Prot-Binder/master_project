#!/bin/bash

use_special_module_stack=false
special_nodes=("t38cn053" "t38cn054" "t38cn055")

if command -v scontrol >/dev/null 2>&1 && [[ -n "${SLURM_JOB_NODELIST:-}" ]]; then
    while IFS= read -r host; do
        for special_node in "${special_nodes[@]}"; do
            if [[ "$host" == "$special_node" ]]; then
                use_special_module_stack=true
                break 2
            fi
        done
    done < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
fi

if [[ "$use_special_module_stack" == true ]]; then
    module purge
    module load gcc/11.5.0
    module load cuda/12.8.0
    module load openmpi/5.0.7-cuda-12.8.0
    module load pmix/5.0.5-cuda-12.8.0
    module load pmemd/24.1-cuda-12.8.0
    module load ambertools/25.10-cuda-12.8.0
    MODULE_SETUP_LABEL="special stack"
else
    module load pmemd
    MODULE_SETUP_LABEL="default pmemd module"
fi

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
echo "Modules:     $MODULE_SETUP_LABEL"
echo "======"

mpirun --oversubscribe -n $NUM_REPS pmemd.cuda_SPFP.MPI -O -ng $NUM_REPS -groupfile $INPUT_FILE

echo "Done"
