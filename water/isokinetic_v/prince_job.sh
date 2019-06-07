#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:4
#SBATCH --time=6:00:00
#SBATCH --mem=10GB
#SBATCH --job-name=ISOK
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ca2356@nyu.edu
#SBATCH --output=slurm_%j.out

module purge
module load cuda/10.0.130
parallel ./run.sh ::: 0 1 2 3
parallel ./run.sh ::: 4 5 6 7
