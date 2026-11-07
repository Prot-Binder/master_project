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
    module purge

    if module load pmemd 2>/dev/null; then
        echo "Loaded module: pmemd"
        MODULE_SETUP_LABEL="pmemd module"
    else
        echo "Could not load module: pmemd"
        echo "Trying module: amber"

        if module load amber 2>/dev/null; then
            echo "Loaded module: amber"
            MODULE_SETUP_LABEL="amber module"
        else
            echo "ERROR: Could not load either pmemd or amber module"
            exit 1
        fi
    fi
fi

# usage: run_usremd_prod.sh NUM_REPS GROUPFILE [NUM_CPUS] [USE_MPS]
NUM_REPS=$1
INPUT_FILE=$2
NUM_CPUS=${3:-$NUM_REPS}
USE_MPS=${4:-0}

echo "===INFORMATION==="
echo "Script dir:  $(dirname "$0")"
echo "Current dir: $PWD"
echo "Replicas:    $NUM_REPS"
echo "CPU cores:   $NUM_CPUS"
echo "Amberhome:   $AMBERHOME"
echo "Python:      $(type python)"
echo "CUDA home:   $CUDA_HOME"
echo "GPU Info:    $(nvidia-smi -L)"
echo "Nodes:       $SLURM_JOB_NODELIST"
echo "Modules:     $MODULE_SETUP_LABEL"
echo "======"
echo "=== NVIDIA-SMI ==="
nvidia-smi
echo "=================="

if [[ "$USE_MPS" == 1 ]]; then
    # per-job directories, so jobs on the same node (or sharing $HOME) do not interfere;
    # CUDA_VISIBLE_DEVICES is left as set by slurm, one daemon serves all GPUs of the job
    MPS_DIR="${TMPDIR:-/tmp}/mps_${SLURM_JOB_ID:-$$}"
    export CUDA_MPS_PIPE_DIRECTORY="$MPS_DIR/pipe"
    export CUDA_MPS_LOG_DIRECTORY="$MPS_DIR/log"
    mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"

    if ! nvidia-cuda-mps-control -d; then
        echo "ERROR: could not start CUDA MPS daemon"
        exit 1
    fi
    echo "MPS:         started (pipe: $CUDA_MPS_PIPE_DIRECTORY)"

    # stop the daemon however the job ends (normal exit, failure, scancel, time limit)
    stop_mps() {
        echo quit | nvidia-cuda-mps-control
        rm -rf "$MPS_DIR"
        echo "MPS:         stopped"
    }
    trap stop_mps EXIT
    trap 'exit 143' TERM INT
else
    echo "MPS:         off"
fi

MPI_ARGS=(--oversubscribe -n "$NUM_REPS")
if (( NUM_REPS > NUM_CPUS )); then
    # more ranks than cores: do not pin ranks to single cores (the OS spreads them over
    # the cores of the job) and let idle ranks yield the core instead of busy-polling
    echo "CPU oversubscription: $NUM_REPS ranks on $NUM_CPUS cores"
    MPI_ARGS+=(--bind-to none)
    export OMPI_MCA_mpi_yield_when_idle=1
fi

mpirun "${MPI_ARGS[@]}" pmemd.cuda_SPFP.MPI -O -ng "$NUM_REPS" -groupfile "$INPUT_FILE" -rem 3
status=$?

echo "Done (exit $status)"
exit $status
