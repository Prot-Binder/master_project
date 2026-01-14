#!/bin/bash

export LC_NUMERIC=C  # Ensures decimal numbers use a dot instead of a comma

set -euo pipefail

# save location of the bash scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# execution context
RUN_DIR="$(pwd)"

WIN=$1
INPUT_DIR=$2
SETUP_DIR=$3

TEMPLATE="${INPUT_DIR}/mdin_templates/us.mdin.in"
RST_SOURCE="${INPUT_DIR}/restraints/window_${WIN}.RST"

MDIN="us_${WIN}.mdin"
RST_LOCAL="disang_${WIN}.RST"

cp "$RST_SOURCE" "$RST_LOCAL"

sed -e "s#__DISANG__#${RST_LOCAL}#g" "$TEMPLATE" > "$MDIN"

pmemd.cuda -O \
  -i "$MDIN" \
  -p "${SETUP_DIR}/system.prmtop" \
  -c "${SETUP_DIR}/system.rst" \
  -ref "${SETUP_DIR}/system.rst" \
  -o "us_${WIN}.out" \
  -r "us_${WIN}.rst" \
  -x "us_${WIN}.nc"
