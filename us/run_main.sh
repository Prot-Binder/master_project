#!/bin/bash

# initial notes: specify all paths relative to the folder where this script is located

#protein="tryp"
protein="5h5r"
ligand="res0"
MIN=5
MAX=35
STEP=1
echo "running main"
# input: pdb file; clean structure and create solvation box around it
# TODO: skipped for now

# generate constraints with jupyter notebook code
# TODO: skipped for now

# run the setup script and copy all files to the corresponding folders
# TODO: skipped for now

# generate the topology files
# TODO: tbd

# create all replicas and run the simulations (equilibration, pull, us)
# TODO: tbd
#TOPDIR="." # TODO
TOPDIR="./top"

#replicas=(4 8 12 16)
replicas=(0 16)

for replica in "${replicas[@]}"; do
    echo "Processing replica $replica"

    job_id="rep${replica}_${protein}_${ligand}"

    # generate output directory strucutre
    mkdir -p ${job_id}
    # cd ${job_id}
    mkdir -p ${job_id}/_slurm
    mkdir -p ${job_id}/_pmd_results # TODO: need to adjust mdin generation files to write to this path
    mkdir -p ${job_id}/_run_output
    mkdir -p ${job_id}/_data

    cp *mdin* ./${job_id}/
    #cp ../*inpcrd* TODO: inprcrd may stay in "root" folder
    # TODO: maybe adjust mdin files here to write to ./_pmd_results
    bash modify_mdin.sh ${job_id} ${MIN} ${STEP} ${MAX}
    outdir="${job_id}/_run_output"
    slurm_outdir="${job_id}/_slurm"
    bash run_simulation.sh ${replica} ${TOPDIR} ${job_id} ${MIN} ${STEP} ${MAX} ${outdir} ${slurm_outdir}

    # rm *mdin*
 #cd ..
done

# analyze the results (plot PMF and histogram)
# TODO: tbd; analyse after all jobs are done
