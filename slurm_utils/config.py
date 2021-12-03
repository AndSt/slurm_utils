from typing import Dict
import os

import logging

import random
import json

from sherpa import Parameter


def write_run_config(data_dir: str, base_work_dir: str, config: Dict) -> [str, str]:
    run_id = random.randint(0, 1000)
    work_dir = os.path.join(base_work_dir, f"run_{run_id}")
    while os.path.isdir(work_dir):
        run_id = random.randint(0, 1000)
        work_dir = os.path.join(base_work_dir, f"run_{run_id}")

    config["data_dir"] = data_dir
    config["work_dir"] = work_dir

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
    def __init__(self, file: str):
        self.file = file

        with open(self.file, "r") as f:
            content = json.load(f)

        self.dataset = content.get("dataset", "")
        self.metric = content.get("metric")
        self.capture_output = not content.get("print_training_output", False)

        hyperparameter = content.get("hyperparameters", {})
        self.algorithm = hyperparameter.get("algorithm")

        self.parameters = []
        for parameter in content.get("parameters", []):
            self.parameters.append(Parameter.from_dict(parameter))
