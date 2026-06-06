#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: $0 [--dry-run] <system>"
    echo "Example: $0 5h5q"
    echo "Example: $0 --dry-run 1sfi"
}

dry_run=false

if [[ "${1:-}" == "--dry-run" ]]; then
    dry_run=true
    shift
fi

if [[ $# -ne 1 ]]; then
    usage
    exit 1
fi

system_name=$1
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd "$script_dir/.." && pwd)
yaml_dir="$project_root/input/yaml_input/$system_name"
pattern="${system_name}_eq_scaled_d*_e*.yaml"

if [[ ! -d "$yaml_dir" ]]; then
    echo "YAML directory does not exist: $yaml_dir" >&2
    exit 1
fi

shopt -s nullglob
configs=("$yaml_dir"/$pattern)
shopt -u nullglob

if [[ ${#configs[@]} -eq 0 ]]; then
    echo "No matching scaled eq YAML files found in $yaml_dir with pattern $pattern" >&2
    exit 1
fi

cd "$project_root"

echo "Submitting ${#configs[@]} scaled eq config(s) for system $system_name"
for config in "${configs[@]}"; do
    echo "[submit_scaled_eq_batch] $(basename "$config")"
    if [[ "$dry_run" == true ]]; then
        python3 scripts/run.py "$config" --dry-run
    else
        python3 scripts/run.py "$config"
    fi
done

echo "Finished processing ${#configs[@]} config(s) for system $system_name"
