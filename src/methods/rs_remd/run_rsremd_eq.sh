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
