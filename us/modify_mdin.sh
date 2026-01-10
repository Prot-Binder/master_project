#!/bin/bash

job_id="$1"
min="$2"
step="$3"
max="$4"

path="./${job_id}/"
mkdir -p "${path}_pmd_results"

echo "Starting modification in: $(pwd)"

input_file="${path}mdin4"
tmp_file="${path}tmp"

echo "Modifying $input_file (pre-pull)"
sed "s|^\([[:space:]]*\)output_file[[:space:]]*=.*|\1output_file = '${path}_pmd_results/pmd_pre_pull.txt'|" \
    "$input_file" > "$tmp_file"
mv "$tmp_file" "$input_file"

# Pulling stage files

echo "min: $min, max: $max, step: $step"
echo "path is: $path"

for j in $(seq "$min" "$step" "$max"); do
# for j in $(seq -f "%.1f" "$min" "$step" "$max"); do
    input_file="${path}mdin5.rep${j}"
    tmp_file="${path}tmp"

    echo "Modifying $input_file"

    sed -e "s|^\([[:space:]]*\)output_file[[:space:]]*=.*|\1output_file = '${path}_pmd_results/pmd_pull_us${j}.txt'|" \
        -e "s|^\([[:space:]]*\)DUMPAVE[[:space:]]*=.*|\1DUMPAVE=${path}_pmd_results/com_pull_${j}.txt|" \
        "$input_file" > "$tmp_file"

    mv "$tmp_file" "$input_file"
done

# Production stage files
for j in $(seq "$min" "$step" "$max"); do 
    input_file="${path}mdin6.rep${j}"
    tmp_file="${path}tmp"

    echo "Modifying $input_file"

    sed "s|^\([[:space:]]*\)output_file[[:space:]]*=.*|\1output_file = '${path}_pmd_results/pmd_prod_us${j}.txt'|" \
        "$input_file" > "$tmp_file"

    mv "$tmp_file" "$input_file"
done

