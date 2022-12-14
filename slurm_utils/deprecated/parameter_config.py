from typing import Dict
import os

import logging

import random
import json
import yaml

from sherpa import Parameter
from sherpa.algorithms import GridSearch, GPyOpt


def write_absl_config(data_dir: str, base_work_dir: str, objective: str, config: Dict) -> [str, str]:
    run_id = random.randint(0, 1000)
    work_dir = os.path.join(base_work_dir, f"run_{run_id}")
    while os.path.isdir(work_dir):
        run_id = random.randint(0, 1000)
        work_dir = os.path.join(base_work_dir, f"run_{run_id}")

    config["data_dir"] = data_dir
    config["work_dir"] = work_dir
    config["objective"] = objective

    config["log_dir"] = work_dir
    config["verbosity"] = 0

    logging.info(f"Initialize workdir: {work_dir}")
    os.makedirs(work_dir, exist_ok=True)

    config_file = os.path.join(work_dir, "config.cfg")
    with open(config_file, "w") as f:
        for k, v in config.items():
            f.write(f"--{k}={v} \n")

    config_json = os.path.join(work_dir, "config.json")
    with open(config_json, "w") as f:
        json.dump(config, f)

    return config_file, run_id


def write_absl_config_new(data_dir: str, work_dir: str, objective: str, config: Dict) -> [str, str]:
    config["data_dir"] = data_dir
    config["work_dir"] = work_dir
    config["objective"] = objective

    config["log_dir"] = work_dir
    config["verbosity"] = 0

    config_file = os.path.join(work_dir, "config.cfg")
    with open(config_file, "w") as f:
        for k, v in config.items():
            f.write(f"--{k}={v} \n")

    config_json = os.path.join(work_dir, "config.json")
    with open(config_json, "w") as f:
        json.dump(config, f)

    return config_file


def write_test_absl_config(data_dir: str, base_work_dir: str, objective: str, config: Dict) -> [str, str]:
    logging.info(config)
    # set debug specific config
    work_dir = os.path.join(base_work_dir, f"test_run")
    config["debug"] = True

    # set normal config
    config["data_dir"] = data_dir
    config["work_dir"] = work_dir
    config["objective"] = objective

    config["log_dir"] = work_dir
    config["verbosity"] = 0

    logging.info(f"Initialize workdir: {work_dir}")
    os.makedirs(work_dir, exist_ok=True)

    config_file = os.path.join(work_dir, "config.cfg")
    with open(config_file, "w") as f:
        for k, v in config.items():
            f.write(f"--{k}={v} \n")

    config_json = os.path.join(work_dir, "config.json")
    with open(config_json, "w") as f:
        json.dump(config, f)

    return config_file, work_dir


class RunConfig:
    def __init__(self, config_file_path: str):
        self.path = config_file_path

        if config_file_path.endswith(".json"):
            with open(self.path, "r") as f:
                content = json.load(f)
        # elif config_file_path.endswith(".yaml"):
        #     with open(self.path, "r") as f:
        #         content = yaml.load(f)
        else:
            raise RuntimeError("Provide a valid config file.")

        run_settings = content.get("run_settings", {})

        self.objective = run_settings.get("objective")
        self.capture_output = not run_settings.get("print_training_output", False)

        self.algorithm_name = run_settings.get("hyperparam_algorithm", "grid")
        self.algorithm_params = run_settings.get("hyperparameter_params")

        if self.algorithm_name == "bayesian":
            self.algorithm = GPyOpt(
                max_concurrent=1, model_type='GP_MCMC', acquisition_type='EI_MCMC', max_num_trials=10
            )
        else:
            self.algorithm = GridSearch(num_grid_points=2)

        self.parameters = [Parameter.from_dict(p) for p in content.get("parameters", [])]
