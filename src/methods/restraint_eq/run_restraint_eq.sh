#!/bin/bash

set -euo pipefail

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

OUTDIR=$1
PRMTOP=$2
INPUT_COORD=$3
REF_COORD=$4
CASE_INDEX=$5
shift 5

STAGE_FILES=("$@")

if (( ${#STAGE_FILES[@]} == 0 ))
then
    echo "No restraint-equilibration stages provided."
    exit 1
fi

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"
echo "Modules: $MODULE_SETUP_LABEL"

CURRENT_COORD=$INPUT_COORD

for STAGE_MDIN in "${STAGE_FILES[@]}"
do
    STAGE_FILE=$(basename "$STAGE_MDIN")
    STAGE_NAME=${STAGE_FILE%%.*}
    STAGE_PREFIX=$OUTDIR/${CASE_INDEX}_${STAGE_NAME}

    case "$STAGE_NAME" in
        min0)
            pmemd -O \
                -i "$STAGE_MDIN" \
                -ref "$REF_COORD" \
                -c "$CURRENT_COORD" \
                -p "$PRMTOP" \
                -r "${STAGE_PREFIX}.restrt" \
                -o "${STAGE_PREFIX}.mdout" \
                -inf "${STAGE_PREFIX}.mdinfo"
            ;;
        *)
            PMEMD_ARGS=(
                -O
                -i "$STAGE_MDIN"
                -c "$CURRENT_COORD"
                -p "$PRMTOP"
                -r "${STAGE_PREFIX}.restrt"
                -o "${STAGE_PREFIX}.mdout"
                -x "${STAGE_PREFIX}.nc"
                -inf "${STAGE_PREFIX}.mdinfo"
            )

            if [[ "$STAGE_NAME" != "prod" ]]
            then
                PMEMD_ARGS=(-ref "$REF_COORD" "${PMEMD_ARGS[@]}")
            fi

            pmemd.cuda "${PMEMD_ARGS[@]}"
            ;;
    esac

    CURRENT_COORD="${STAGE_PREFIX}.restrt"
done
