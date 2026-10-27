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

# usage: run_us.sh MDINDIR OUTDIR TOPDIR USE_MPS window1 coord1 [window2 coord2 ...]
# all given windows run concurrently on the GPU of this job;
# with USE_MPS=1 they share the GPU through a per-job CUDA MPS daemon
MDINDIR=$1
OUTDIR=$2
TOPDIR=$3
USE_MPS=$4
shift 4

if (( $# == 0 || $# % 2 != 0 )); then
    echo "ERROR: expected pairs of <window> <coordinate file>, got: $*"
    exit 1
fi

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"
echo "Modules: $MODULE_SETUP_LABEL"
echo "GPU Info: $(nvidia-smi -L)"
echo "Compute mode: $(nvidia-smi --query-gpu=compute_mode --format=csv,noheader)"

if [[ "$USE_MPS" == 1 ]]; then
    # per-job directories, so jobs on the same node (or sharing $HOME) do not interfere;
    # CUDA_VISIBLE_DEVICES is left as set by slurm
    MPS_DIR="${TMPDIR:-/tmp}/mps_${SLURM_JOB_ID:-$$}"
    export CUDA_MPS_PIPE_DIRECTORY="$MPS_DIR/pipe"
    export CUDA_MPS_LOG_DIRECTORY="$MPS_DIR/log"
    mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"

    if ! nvidia-cuda-mps-control -d; then
        echo "ERROR: could not start CUDA MPS daemon"
        exit 1
    fi
    echo "MPS: started (pipe: $CUDA_MPS_PIPE_DIRECTORY)"

    # stop the daemon however the job ends (normal exit, failure, scancel, time limit)
    stop_mps() {
        echo quit | nvidia-cuda-mps-control
        rm -rf "$MPS_DIR"
        echo "MPS: stopped"
    }
    trap stop_mps EXIT
    trap 'exit 143' TERM INT
else
    echo "MPS: off"
fi

windows=()
pids=()
while (( $# > 0 )); do
    window=$1
    COORD_FILE=$2
    shift 2

    echo "Starting Umbrella Sampling for Window $window (input: $COORD_FILE)"
    pmemd.cuda -O -i $MDINDIR/mdin6.w$window -o $OUTDIR/mdout6.w$window -p $TOPDIR/prmtop1 -c $COORD_FILE -r $OUTDIR/restrt6.w$window -x $OUTDIR/traj6.w$window.nc -inf $OUTDIR/mdinfo6.w$window &
    windows+=("$window")
    pids+=("$!")
done

status=0
for i in "${!pids[@]}"; do
    if wait "${pids[$i]}"; then
        echo "Window ${windows[$i]} done"
    else
        echo "ERROR: Window ${windows[$i]} failed"
        status=1
    fi
done

exit $status
