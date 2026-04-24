#!/bin/bash

module load pmemd

MIN=$1
MAX=$2
STEP=$3

MDINDIR=$4
OUTDIR=$5
TOPDIR=$6
CPU_USAGE=$7

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

pmemd.cuda -O -i $MDINDIR/mdin_eq -c $MDINDIR/inpcrd$MAX -p $TOPDIR/prmtop1 -r $OUTDIR/restrt$MAX -o $OUTDIR/mdout_eq -x $OUTDIR/traj_eq.nc -inf $OUTDIR/mdinfo_eq
cp $OUTDIR/restrt_eq $MDINDIR/inpcrd$MAX


