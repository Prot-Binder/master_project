#!/bin/bash

export LC_NUMERIC=C  # Ensures decimal numbers use a dot instead of a comma

REPLICA=$1
TOPDIR=$2
JOBID=$3

MIN=$4
STEP=$5
MAX=$6

OUTDIR=$7
SLURM_OUT=$8

MDINDIR="./${JOBID}"
exclude_ranks=t38cn030,t38cn038,t38cn028,t38cn015,t38cn024,t38cn027,t38cn016,t38cn018,t38cn031,t38cn020,t38cn021,t38cn032,t38cn019,t38cn022,t38cn055,t38cn026,t38cn053,t38cn045,t38cn042
run_US()
{
	# run the em and equilibration
#	eq_jobid=$(sbatch \
#		--job-name=${JOBID}_eq \
#		--gres=gpu:1 \
# 		--nodes=1 \
#		--time=1-00:00:00 \
#		--ntasks=1 \
#		--cpus-per-task=1 \
#		--exclude=$exclude_ranks \
#		--output="$SLURM_OUT/slurm-%j.out" \
#		run_eq.sh 0 1 4 $MDINDIR $OUTDIR $TOPDIR $REPLICA)
#	eq_jobid=$(echo $eq_jobid | awk '{print $NF}')

  # --dependency=afterok:$eq_jobid \
	# Run the Pull equilibration for every window in parallel
	for rep in $(seq $MIN $STEP $MAX)
	do
		pull_jobid=$(sbatch \
			--job-name=${JOBID}_pull$rep \
			--gres=gpu:1 \
			--nodes=1 \
      		--time=1-00:00:00 \
      		--ntasks=1 \
      		--cpus-per-task=1 \
      		--exclude=$exclude_ranks \
			--output="$SLURM_OUT/slurm-%j.out" \
   		run_pull.sh 4 5.rep$rep $MDINDIR $OUTDIR $TOPDIR $REPLICA | awk '{print $4}' )

  #--dependency=afterok:$pull_jobid \
  # Submit us.sh only after pull_jobid finishes successfully
		sbatch \
			--dependency=afterok:$pull_jobid \
		  --job-name=${JOBID}_us$rep \
     		--gres=gpu:1 \
			--nodes=1 \
			--time=1-00:00:00 \
			--ntasks=1 \
			--cpus-per-task=1 \
			--exclude=$exclude_ranks \
			--output="$SLURM_OUT/slurm-%j.out" \
   run_us.sh $rep $MDINDIR $OUTDIR $TOPDIR $REPLICA
  done
}


run_US

