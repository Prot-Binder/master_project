#!/bin/bash

module load pmemd

MIN=$1
MAX=$2
STEP=$3

MDINDIR=$4
OUTDIR=$5
TOPDIR=$6
CPU_USAGE=$7
RUN_EXTRA_EQ=$8

echo "Job ID: $SLURM_JOB_ID"
echo "SLURM local node: $SLURMD_NODENAME"
echo "Node list: $SLURM_JOB_NODELIST"
echo "Running on node: $(hostname)"

for n in $(seq $MIN $STEP $MAX)
do
	# initialize N as the next step
	N=$((n+$STEP))

	if (( n < CPU_USAGE ))
	then
		printf "sander minimization started... "
		pmemd -O -i $MDINDIR/mdin$n -ref $MDINDIR/refc -c $MDINDIR/inpcrd$n -p $TOPDIR/prmtop1 -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -inf $OUTDIR/mdinfo$n
		echo "done"
	else
		# all files are id'ed by the d-variables (except prmtop)
		printf "Running for $n... "
		pmemd.cuda -O -i $MDINDIR/mdin$n -ref $MDINDIR/refc -c $MDINDIR/inpcrd$n -p $TOPDIR/prmtop1 -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -x $OUTDIR/traj$n.nc -inf $OUTDIR/mdinfo$n
		echo "done"
	fi

	# copy the restart file to inp coord for the next step
	cp $OUTDIR/restrt$n $MDINDIR/inpcrd$N
done

FINAL_INPUT=$((MAX+STEP))
FINAL_HANDOFF=$MDINDIR/inpcrd_eq

if (( RUN_EXTRA_EQ == 1 ))
then
	pmemd.cuda -O -i $MDINDIR/mdin_eq -c $MDINDIR/inpcrd$FINAL_INPUT -p $TOPDIR/prmtop1 -r $OUTDIR/restrt_eq -o $OUTDIR/mdout_eq -x $OUTDIR/traj_eq.nc -inf $OUTDIR/mdinfo_eq
	cp $OUTDIR/restrt_eq $FINAL_HANDOFF
else
	cp $MDINDIR/inpcrd$FINAL_INPUT $FINAL_HANDOFF
fi
