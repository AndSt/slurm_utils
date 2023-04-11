import os

import invoke
import click
import logging

from slurm_utils.convenience.log import init_logging


def set_pypi_conf():
    command = "pip config set global.extra-index-url 'https://knodle.cc/pypi/simple/'"
    logging.info(command)
    invoke.run(command)

    command = "pip config set global.trusted-host 'knodle.cc/pypi'"
    logging.info(command)
    invoke.run(command)


@click.command()
def local_install():
    """Run code on SLURM.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)
    set_pypi_conf()


@click.command()
@click.argument("--path", "path", help="Path to the slurm utils folder.")
def su_server_install(path):
    init_logging(logging.INFO)

    set_pypi_conf()

    # create folder
    os.makedirs(os.path.join(path, "cache"), exist_ok=True)
    os.makedirs(os.path.join(path, "conda_envs"), exist_ok=True)
    os.makedirs(os.path.join(path, "conda_pkgs"), exist_ok=True)
    os.makedirs(os.path.join(path, "data"), exist_ok=True)
    os.makedirs(os.path.join(path, "projects"), exist_ok=True)

    invoke.run(f"cd {path}; git clone git@github.com:AndSt/server_setup.git", pty=True, warn=True)

    ## append the text "SU_STORAGE" to the file ".bashrc"
    text = f"""
    
# User specific aliases and functions

export SU_STORAGE={path}

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# if it is run interactively, initialize gateway
source $SU_STORAGE/server_setup/init_gateway.sh    
    
    """
    with open("~/.bashrc", "a") as f:
        f.write(text)


