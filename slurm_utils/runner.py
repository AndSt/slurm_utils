import logging
import os

import json

import subprocess

import sherpa
from sherpa.algorithms import GridSearch
from sherpa.algorithms import bayesian_optimization

from slurm_utils.postprocessing import write_run_output_stream, log_best_results
from slurm_utils.result_analysis import get_results_df
from slurm_utils.config import write_run_config, RunConfig


def run_hyp_opt(executable: str, train_file: str, work_dir: str, data_dir: str, config_file: str):
    logging.debug(f"Start hyperparameter optimization with")
    logging.debug(f"executable: {executable}")
    logging.debug(f"train_file: {train_file}")
    logging.debug(f"work_dir: {work_dir}")
    logging.debug(f"data_dir: {data_dir}")
    logging.debug(f"config_file: {config_file}")

    config = RunConfig(config_file)
    if config.algorithm == "grid":
        algorithm = GridSearch(num_grid_points=2)
    else:
        algorithm = bayesian_optimization.GPyOpt(
            max_concurrent=1, model_type='GP_MCMC', acquisition_type='EI_MCMC', max_num_trials=10
        )

    # initialize Study
    study_dir = os.path.join(work_dir, "study")
    os.makedirs(study_dir, exist_ok=True)
    study = sherpa.Study(
        parameters=config.parameters,
        algorithm=algorithm,
        lower_is_better=False,
        disable_dashboard=True,
        output_dir=study_dir
    )

    for trial in study:
        logging.info(f"Start Trial {trial.id}, with parameters {trial.parameters}")

        config_file, run_work_dir = write_run_config(data_dir, work_dir, trial.parameters)

        params = [executable, train_file, f"--flagfile={config_file}"]
        output = subprocess.run(params, capture_output=config.capture_output)

        if config.capture_output:
            write_run_output_stream(output, work_dir=run_work_dir)

        with open(os.path.join(run_work_dir, "test_metrics.json"), "r") as f:
            metrics = json.load(f)
            result = metrics.get("macro avg").get("f1-score") if config.metric == "f1" else metrics.get("accuracy")

        logging.info(f"{config.metric}: {result}")

        study.add_observation(trial, iteration=1, objective=result, context=metrics)
        study.finalize(trial)

        study.save()

        # time.sleep(2)

    log_best_results(study=study, config=config)

    parameter_names = [parameter.name for parameter in config.parameters]
    result_df = get_results_df(experiment_dir=work_dir, metric=config.metric, parameters=parameter_names)
    result_df.to_csv(os.path.join(work_dir, "result_df.csv"), sep=";", index=None)
