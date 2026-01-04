#!/bin/bash

module load pmemd

OUTDIR="_output"
mkdir -p $OUTDIR

MIN=$1
STEP=$2
MAX=$3

# start for loop over distances (d) as specified in the GLOBAL VARIABLES in script.sh
for n in $(seq $MIN $STEP $MAX)
do
	# initialize N as the next step
	N=$((n+$STEP))
	
	if (( n < 1 ))
	then 
		printf "sander minimization started... "
		pmemd.cuda -O -i mdin$n -ref refc$n -c inpcrd$n -p prmtop -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -inf $OUTDIR/mdinfo$n
		echo "done"
	else	
		# all files are id'ed by the d-variables (except prmtop)
		printf "Running for $n... "
		pmemd.cuda -O -i mdin$n -ref refc$n -c inpcrd$n -p prmtop -r $OUTDIR/restrt$n -o $OUTDIR/mdout$n -x $OUTDIR/traj$n.nc -inf $OUTDIR/mdinfo$n
		echo "done"
	fi

	# copy the restart file to inp coord for the next step
	cp $OUTDIR/restrt$n inpcrd$N
done
