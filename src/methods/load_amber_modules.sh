#!/bin/bash

load_amber_modules() {
    local use_special_module_stack=false
    local special_nodes=("t38cn053" "t38cn054" "t38cn055")

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
        export MODULE_SETUP_LABEL="special stack"
    else
        module load pmemd
        export MODULE_SETUP_LABEL="default pmemd module"
    fi
}
