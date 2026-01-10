#!/bin/bash

# module load pmemd
# module load python/3.13.2 
#module load openmpi/5.0.7-cuda-12.8.0


# specify variables
MDINDIR=.
TOPDIR=./top
OUTDIR=./us_remd

mkdir -p $OUTDIR

pwd

#ls -l mdin_rsremd
#ls -l refc0
#ls -l ./top/prmtop0
#ls -l ./replica_test/inpcrd_rep0


# echo "Job ID: $SLURM_JOB_ID"
# echo "SLURM local node: $SLURMD_NODENAME"
# echo "Node list: $SLURM_JOB_NODELIST"
# echo "Running on node: $(hostname)"
# 
# minimize equilibrate etc
# TODO: scipped here because we already have an equilibrated strucutre

# generate group file
#replicas=(5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35)
replicas=(14 15 16 17 18 19 20 21)
#replicas=(0 2 4 6 8 10 12 16)
nrep=${#replicas[@]}
# python generate_groupfile.py -m eq -r ${replicas[@]} -o $OUTDIR -t $TOPDIR

# TODO: MAYBE DELETE? copy initial coordinate file to "new replica files"

# make a short run at individual prmtop file for "equilibration"
# mpirun -np $nrep pmemd.cuda.MPI -ng $nrep -groupfile $OUTDIR/eq.groupfile

# start remd simulation
python generate_groupfile_usre.py -m remd -r ${replicas[@]} -o $OUTDIR -t $TOPDIR

# mpirun --oversubscribe -np $nrep pmemd.MPI -ng $nrep -groupfile $OUTDIR/rsremd.groupfile
