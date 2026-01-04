#!/bin/bash

module load pmemd

n=$1
sffx=$2
OUTDIR="_output"
mkdir -p $OUTDIR


printf "Running for $sffx... "
pmemd.cuda -O -i mdin$sffx -c inpcrd$n -p prmtop -r $OUTDIR/restrt$sffx -o $OUTDIR/mdout$sffx -x $OUTDIR/traj$sffx.nc -inf $OUTDIR/mdinfo$sffx
echo "done"
