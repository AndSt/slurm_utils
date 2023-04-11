import click
import logging

from slurm_utils.convenience.log import init_logging

from slurm_utils.experiment_manager import LocalExperimentManager, RemoteExperimentManager, ServerExperimentManager


@click.command()
@click.argument('config')
def su_local(config):
    """Run code on SLURM.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)
    exp = LocalExperimentManager(config)
    exp.run_experiment(clean_existing=True)


@click.command()
@click.argument('config')
def su_sbatch(config):
    """Run code, ready for SLURM, locally.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)

    exp = ServerExperimentManager(config)
    exp.run_experiment(clean_existing=True)


@click.command()
@click.argument('config')
@click.option('-u', '--upload', "upload", is_flag=True, show_default=True, default=True, help="Whether to upload code")
def su_remote(config, upload):
    """Run code on SLURM.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)
    exp = RemoteExperimentManager(config)
    exp.run_remote(upload_code=upload)
    exp.close()