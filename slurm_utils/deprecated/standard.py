import logging
import os
import time

import json

import subprocess

from sherpa import Study

from slurm_utils.deprecated.postprocessing import write_run_output_stream, log_best_results
from slurm_utils.deprecated.parameter_config import write_absl_config, write_test_absl_config, RunConfig


def run_hyp_opt(executable: str, run_file: str, work_dir: str, data_dir: str, config_file: str):
    logging.debug(f"Start hyperparameter optimization with")
    logging.debug(f"executable: {executable}")
    logging.debug(f"run_file: {run_file}")
    logging.debug(f"work_dir: {work_dir}")
    logging.debug(f"data_dir: {data_dir}")
    logging.debug(f"config_file: {config_file}")

    config = RunConfig(config_file)

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

    for trial in study:
        logging.info(f"Start Trial {trial.id}, with parameters {trial.parameters}")

        config_file, run_work_dir = write_absl_config(data_dir, work_dir, config.objective, trial.parameters)

        params = [executable, run_file, f"--flagfile={config_file}"]
        with open(os.path.join(run_work_dir, "sh_command.txt"), "w") as f:
            f.write(" ".join(params))

        start_time = time.time()
        output = subprocess.run(params, capture_output=config.capture_output)
        end_time = time.time() - start_time

        process_stats = {"time_in_secs": end_time}
        with open(os.path.join(run_work_dir, "process_stats.json"), "w") as f:
            json.dump(process_stats, f)

        if config.capture_output:
            write_run_output_stream(output, work_dir=run_work_dir)

        with open(os.path.join(run_work_dir, "test_metrics.json"), "r") as f:
            metrics = json.load(f)
            if config.objective not in metrics:
                raise RuntimeError(
                    f"You have to write a file called test_metrics.json which holds a key {config.objective}"
                )
            result = metrics.get(config.objective)

        logging.info(f"{config.objective}: {result}")

        study.add_observation(trial, iteration=1, objective=result, context=metrics)
        study.finalize(trial)

        study.save()

        # time.sleep(2)

    log_best_results(study=study, config=config)

    parameter_names = [parameter.name for parameter in config.parameters]
    with open(os.path.join(work_dir, "parameters.json"), "w") as f:
        json.dump(parameter_names, f)


def run_dummy_hyp_opt(executable: str, train_file: str, work_dir: str, data_dir: str, config_file: str):
    config = RunConfig(config_file)

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

    trial = study.get_suggestion()

    logging.info(f"Start Trial {trial.id}, with parameters {trial.parameters}")

    config_file, run_work_dir = write_test_absl_config(data_dir, work_dir, config.objective, trial.parameters)

    params = [executable, train_file, f"--flagfile={config_file}"]
    with open(os.path.join(run_work_dir, "sh_command.txt"), "w") as f:
        f.write(" ".join(params))

    subprocess.run(params)

    with open(os.path.join(run_work_dir, "test_metrics.json"), "r") as f:
        metrics = json.load(f)
        if config.objective not in metrics:
            raise RuntimeError(
                f"You have to write a file called test_metrics.json which holds a key {config.objective}"
            )
        result = metrics.get(config.objective)

    logging.info(f"{config.objective}: {result}")

    study.add_observation(trial, iteration=1, objective=result, context=metrics)
    study.finalize(trial)
    study.save()
