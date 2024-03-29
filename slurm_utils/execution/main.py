import logging
import os

import time

import json

from slurm_utils.config.load import load_config
from slurm_utils.execution.server_scheduler import SlurmJobScheduler
from slurm_utils.execution.local_scheduler import LocalJobScheduler

from sherpa import Study

from slurm_utils.config.resources import ResourceConfig
from slurm_utils.execution.parameters import RunConfig


def log_best_results(study, config):
    best = study.get_best_result()
    logging.info(f"Best trial run - ID: {best.get('Trial-ID')}, {config.objective}: {best.get('Objective')} ")
    logging.info(f"Find all related data at {best.get('work_dir')}")


def schedule_and_run_jobs(executable: str, run_file: str, work_dir: str, data_dir: str, config_file: str):

    logging.debug(f"Start hyperparameter optimization with")
    logging.debug(f"executable: {executable}")
    logging.debug(f"train_file: {run_file}")
    logging.debug(f"work_dir: {work_dir}")
    logging.debug(f"data_dir: {data_dir}")
    logging.debug(f"config_file: {config_file}")

    experiment_config = load_config(config_file)

    config = RunConfig(experiment_config=experiment_config)
    resource_config = ResourceConfig(experiment_config=experiment_config)

    parameter_names = [parameter.name for parameter in config.parameters]
    with open(os.path.join(work_dir, "parameters.json"), "w") as f:
        json.dump(parameter_names, f)

    # initialize Study
    study_dir = os.path.join(work_dir, "study")
    os.makedirs(study_dir, exist_ok=True)
    study = Study(
        parameters=config.parameters,
        algorithm=config.algorithm,
        lower_is_better=False,
        disable_dashboard=True,
        output_dir=study_dir
    )
    if executable == "local":
        process_manager = LocalJobScheduler(
            study=study,
            config=config,
            executable=executable,
            work_dir=work_dir,
            data_dir=data_dir,
            resource_config=resource_config
        )
    else:
        process_manager = SlurmJobScheduler(
            study=study,
            config=config,
            executable=executable,
            work_dir=work_dir,
            data_dir=data_dir,
            resource_config=resource_config
        )

    start_time = time.time()
    process_manager.loop_hyperparams()
    process_manager.wait_until_all_finished()
    end_time = time.time()

    # TODO - summary write
    # writer pandas frame and JOSN of time / objective per run, sort py objective

    log_best_results(study=process_manager.study, config=config)
