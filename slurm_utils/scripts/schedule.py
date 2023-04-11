import click
import logging

from slurm_utils.convenience.log import init_logging
from slurm_utils.execution.main import schedule_and_run_jobs


@click.command()
@click.option('--executable', 'executable', help='Executable of the current project.')
@click.option('--run_file', 'run_file', help='File that starts the training procedure.')
@click.option('--data_dir', 'data_dir', help='Data directory.')
@click.option('--work_dir', 'work_dir', help='Working directory.')
@click.option('--config_file', 'config_file', help='Working directory.')
def schedule_jobs_command(executable, run_file, data_dir, work_dir, config_file):
    """Run code on SLURM.

    """
    if executable == "local":
        init_logging(logging.INFO)
    else:
        init_logging(logging.INFO)

    schedule_and_run_jobs(
        executable=executable,
        run_file=run_file,
        work_dir=work_dir,
        data_dir=data_dir,
        config_file=config_file
    )

