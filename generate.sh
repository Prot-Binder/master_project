#!/bin/bash

# file path to working directory
# base_path="/home/simonhang/cluster/02_auto/us"
#base_path=$1
#mask_receptor=$2
#mask_ligand=$3

base_path=/home/simonhang/cluster/02_setup_4ib5/us

# if [ ! -f "$base_path" ]; then
#     echo "Error: Base Path '$base_path' does not exist." >&2
#     exit 1
# fi

# generate receptor masks

# base coordinate file
coord_file=${base_path}/inpcrd0

# base topology file TODO: need to adjust this also
top_file=${base_path}/prmtop

mkdir -p ${base_path}/top/

# output file path
output=${base_path}/top/prmtop

cp $top_file ${base_path}/top/prmtop0

# python adjust_lj.py $top_file 16 -d 0.00 0.01 0.02 0.04 0.08 0.12 0.16 0.20 0.24 0.28 0.32 0.38 0.44 0.50 0.58 0.68 -e 1.00 0.99 0.98 0.97 0.96 0.94 0.92 0.90 0.88 0.86 0.84 0.82 0.80 0.78 0.76 0.74 -c "+path+"/exp6.rst -r "+r_mask+" -l "+l_mask+" -o "+npath+"/system.top | tee "+npath+"/lj.log"
python adjust_lj.py $top_file 16 -d 0.00 0.01 0.02 0.04 0.08 0.12 0.16 0.20 0.24 0.28 0.32 0.38 0.44 0.50 0.58 0.68 -e 1.00 0.99 0.98 0.97 0.96 0.94 0.92 0.90 0.88 0.86 0.84 0.82 0.80 0.78 0.76 0.74 -c $coord_file -o $output -r ":1-247" -l ":248-257" # | tee "+npath+"/lj.log"
#python adjust_lj.py $top_file 16 -d 0.00 0.01 0.02 0.04 0.08 0.12 0.16 0.20 0.24 0.28 0.32 0.38 0.44 0.50 0.58 0.68 -e 1.00 0.99 0.98 0.97 0.96 0.94 0.92 0.90 0.88 0.86 0.84 0.82 0.80 0.78 0.76 0.74 -c $coord_file -o $output -r ${mask_receptor} -l ${mask_ligand}

# copy top file into prmtop file
