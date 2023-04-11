import json

import yaml
from yaml import SafeLoader


def load_config(file_path: str, experiment_name: str = None):
    if file_path.endswith(".json"):
        with open(file_path, "r") as f:
            config = json.load(f)
    elif file_path.endswith(".yaml"):
        with open(file_path, "r") as f:
            config = yaml.load(f, Loader=SafeLoader)
    if experiment_name is not None:
        config["experiment_name"] = experiment_name
    return config
