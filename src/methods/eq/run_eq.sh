#!/bin/bash

module load pmemd

MIN=$1
MAX=$2
STEP=$3

MDINDIR=$4
OUTDIR=$5
TOPDIR=$6
REPLICA_SCALING=$7

# start for loop over distances (d) as specified in the GLOBAL VARIABLES in main_script.sh
for n in $(seq $MIN $STEP $MAX)
do
	# initialize N as the next step
	N=$((n+$STEP))

	if (( n < 1 ))
	then
		printf "sander minimization started... "
		pmemd -O -i $MDINDIR/mdin$n -ref refc -c inpcrd$n -p $TOPDIR/prmtop$REPLICA_SCALING -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -inf $OUTDIR/mdinfo$n
		echo "done"
	else
		# all files are id'ed by the d-variables (except prmtop)
		printf "Running for $n... "
		pmemd.cuda -O -i $MDINDIR/mdin$n -ref refc -c inpcrd$n -p $TOPDIR/prmtop$REPLICA_SCALING -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -x $OUTDIR/traj$n.nc -inf $OUTDIR/mdinfo$n
		echo "done"
	fi

	# copy the restart file to inp coord for the next step
	cp $OUTDIR/restrt$n inpcrd$N
done

