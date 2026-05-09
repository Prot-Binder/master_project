#!/bin/bash

set -euo pipefail

module load pmemd

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
