#!/bin/bash
export LC_NUMERIC=C  # Ensures decimal numbers use a dot instead of a comma
INPDIR="../_inp"
OUTDIR="_output"
TRASH="_trash"
JOBID="mhc"

run_US()
{
	# run the eq and equilibration
	sbatch --job-name=${JOBID}_eq run_rmd-seq_alex.sh 0 1 4
	
	# Run the Pull equilibration for first range (5-20, step 0.5) in parallel
	for rep in $(seq 5 0.5 19.5)
	do
		sbatch --job-name=${JOBID}_pull$rep run_md_alex.sh 4 5.rep$rep
		sbatch --job-name=${JOBID}_us$rep us.sh $rep
	done
	
	# Run the Pull equilibration for second range (20.5-35, step 1.0) in parallel
	for rep in $(seq 20 1 35)
	do
		sbatch --job-name=${JOBID}_pull$rep run_md_alex.sh 4 5.rep$rep
		sbatch --job-name=${JOBID}_us$rep us.sh $rep
	done
}

run_US
