#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: $0 [--dry-run] <system> [yaml_file1 yaml_file2 ...]"
    echo
    echo "Examples:"
    echo "  $0 5h5q"
    echo "  $0 --dry-run 1sfi"
    echo "  $0 1sfi 1sfi_eq_scaled_d0p029_e0p986.yaml 1sfi_eq_scaled_d0p057_e0p971.yaml"
    echo
    echo "If no YAML files are given, all matching scaled eq YAML files are submitted."
    echo "If YAML files are given, only those files are submitted."
}

dry_run=false

if [[ "${1:-}" == "--dry-run" ]]; then
    dry_run=true
    shift
fi

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

system_name=$1
shift

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd "$script_dir/.." && pwd)
yaml_dir="$project_root/input/yaml_input/$system_name"
pattern="${system_name}_eq_scaled_d*_e*.yaml"

if [[ ! -d "$yaml_dir" ]]; then
    echo "YAML directory does not exist: $yaml_dir" >&2
    exit 1
fi

configs=()

if [[ $# -gt 0 ]]; then
    # Only use explicitly provided files.
    for file in "$@"; do
        # Allow either full paths or only basenames.
        if [[ -f "$file" ]]; then
            configs+=("$file")
        elif [[ -f "$yaml_dir/$file" ]]; then
            configs+=("$yaml_dir/$file")
        else
            echo "Requested YAML file does not exist: $file" >&2
            echo "Also checked: $yaml_dir/$file" >&2
            exit 1
        fi
    done
else
    # Default behavior: use all matching files.
    shopt -s nullglob
    configs=("$yaml_dir"/$pattern)
    shopt -u nullglob
fi

if [[ ${#configs[@]} -eq 0 ]]; then
    echo "No YAML files selected." >&2
    exit 1
fi

cd "$project_root"

echo "Submitting ${#configs[@]} scaled eq config(s) for system $system_name"

for config in "${configs[@]}"; do
    echo "[submit_scaled_eq_batch] $(basename "$config")"

    if [[ "$dry_run" == true ]]; then
        python3 -m scripts.run "$config" --dry-run
    else
        python3 -m scripts.run "$config"
    fi
done

echo "Finished processing ${#configs[@]} config(s) for system $system_name"