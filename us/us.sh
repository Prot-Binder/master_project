#!/bin/bash

module load pmemd

i=$1
OUTDIR="_output"
mkdir -p $OUTDIR


printf "Running for Window $i... "

pmemd.cuda -O -i mdin6.rep$i -o $OUTDIR/mdout6.rep$i -p prmtop -c $OUTDIR/restrt5.rep$i -r $OUTDIR/restrt6.rep$i -x $OUTDIR/traj6.rep$i.nc -inf $OUTDIR/mdinfo6.rep$i

echo "done"


