import json


def load_config(file_path: str, experiment_name: str):
    with open(file_path, "r") as f:
        config = json.load(f)
    if experiment_name is not None:
        config["experiment_name"] = experiment_name
    return config