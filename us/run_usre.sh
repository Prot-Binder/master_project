#!/bin/bash
#SBATCH --job-name=us_remd_5h5r
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --partition=barracuda
#SBATCH --gres=gpu:1
# BATCH -w cuda-node020
# BATCH --exclusive
#SBATCH --exclude='t38cn030,t38cn038,t38cn028,t38cn015,t38cn024,t38cn027,t38cn016,t38cn018,t38cn031,t38cn020,t38cn021,t38cn032,t38cn019,t38cn022,t38cn055,t38cn026,t38cn053,t38cn045,t38cn042'
#SBATCH --constraint='rtx4090|rtxa5000'
#SBATCH --time=2-00:00:00

module load pmemd


export CUDA_VISIBLE_DEVICES=0


echo "===INFORMATION==="
echo "Script dir:  $(dirname $0)"
echo "Current dir: $PWD"
echo "Argument:    $1"
echo "Amberhome:   $AMBERHOME"
echo "Python:      `type python`"
echo "CUDA home:   $CUDA_HOME"
echo "GPU Info:    $(nvidia-smi -L)"
echo "Nodes:       $SLURM_JOB_NODELIST"
echo "======"

        mpirun --oversubscribe -n 8 pmemd.cuda_SPFP.MPI -O -ng 8 -groupfile ./us_remd/usremd.groupfile -rem 3


echo "Done"
