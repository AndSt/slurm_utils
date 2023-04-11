# SLURM UTILS

A utility repo to work with a remote SLURM cluster, all from within Python. 
The assumption is that you code locally, push your experiments to a gateway server an then submit jobs from there.
This repository allows you to do the whole process locally, e.g. steered from a Jupyter Notebook. See Usage for more details.

Note: This is heavily biased towards my personal setup.

### Motivation

I want to structure my code such that
- There are multiple multiple main functions (e.g. for training / prediction / jax or pytorch version)
- Each file takes arguments only via the [Abseil](https://github.com/abseil/abseil-py) library

I want to be able to 
- Run and test my code locally from a Jupyter Notebook to quickly find bugs, iterate fast
- Run hyperparameter optimization without change to a main() function
- I want to be able to run this on a remote SLURM cluster without complicated manual git push/pull; pip install; .... 
commands which are really tiresome
- I want to stear all this via a simple config dict / JSON file.



--------------
## Features
- Steer local / remote training, all locally from Jupyter
- Up / Download files and results
- Automatic Hyperparameter optimization powered by [Sherpa](https://parameter-sherpa.readthedocs.io/en/latest/).

----------
## Usage

We have an example repo at [https://github.com/AndSt/slurm_utils_test_repo](https://github.com/AndSt/slurm_utils_test_repo).
The best idea would be to look at it, to see how it's structured.
In notebooks/ you will find an example how to run things

In general, you can use Jupyter Notebooks, or the CLI

````bash
slurm config.json  # to push
local_slurm config.json # 
````

## Installation

1. AddGithub / Gitlab SSH key 
   1. Create key 
   2. Generate file .ssh/config, e.g.
````bash
Host github.com
    IdentityFile ~/.ssh/id_ed25519_github
````
2. Add to .bashrc file (change SU_STORAGE variable to wherever you want your data to live). 
Needs to be accesible on gateway server and SLURM compute nodes:

````bash
# User specific aliases and functions

export SU_STORAGE=/path/to/my/home/directory

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# if it is run interactively, initialize gateway
source $SU_STORAGE/server_setup/init_gateway.sh
````
4. Install Anaconda by 
   1. downloading .sh installation file, and 
   2. installing under $SU_STORAGE/conda_installation
   3. run conda init, and delete conda initialization routine in .bashrc
5. Add knodle_pypi by adding or creating this to ~/.pip/pip.conf:
````bash
[global]
	extra-index-url = https://knodle.cc/pypi/simple/
    trusted-host = knode.cc/pypi
````



## [WIP]

- Differentiate logging output between Experiment; hyp-param; training run better, All are a dedicated process 
which complicates things
- Summary statistics, i.e. how long did it run, etc.

- provide startup.sh and run_file.sh examples