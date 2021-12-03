# SLURM UTILS

A utility repo to work with a remote SLURM cluster. This is heavily biased towards my personal setup.

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

-----------
## Prerequesites:
- setup .ssh
- install virtualenv wrapper on server
- We use a PyPi server to transfer everything, so make sure your repo is installable.
- write a startup.sh file on server
- write a start_run.sh file (which loads environment for your SLURM run)


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

## [WIP]

- How to ideally observe current training progress?
- Differentiate logging output between Experiment; hyp-param; training run better, All are a dedicated process 
which complicates things
- Summary statistics, i.e. how long did it run, etc.
- Better access to logs (E.g. mle-logging, download + printing)

- test on actual projects, not just dummy code
- see how to document things best
- provide startup.sh and run_file.sh examples