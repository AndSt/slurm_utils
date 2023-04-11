import click
import logging

from slurm_utils.convenience.log import init_logging

from slurm_utils.config.load import load_config
from slurm_utils.experiment_manager import RemoteSlurmExperimentManager


def setup_exp(config_path: str):
    config = load_config(config_path, None)

    proj_name = config.get("project_name")
    proj_dir = f"/Users/andst/projects/{proj_name}"

    exp = RemoteSlurmExperimentManager(
        local_proj_dir=proj_dir,  # local proj dir
        experiment_config=config  # os.path.join(proj_dir, "notebooks", "data", "test_data", "empty_train_config.json")
    )

    exp.prepare_local_experiment(clean_existing=True)
    return exp


@click.command()
@click.argument('config')
@click.option('-u', '--upload', "upload", is_flag=True, show_default=True, default=False, help="Whether to upload code")
def slurm(config, upload):
    """Run code on SLURM.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)

    exp = setup_exp(config)
    exp.prepare_remote_experiment(clean_existing=True, upload_code=upload)
    out = exp.run_remote(upload_code=False)
    exp.close()


@click.command()
@click.argument('config')
def local_slurm(config):
    """Run code, ready for SLURM, locally.

    CONFIG is the name of the configuration file.
    """
    init_logging(logging.INFO)

    exp = setup_exp(config)
    out = exp.run_locally()
    exp.close()
