from typing import Dict, List

import os
import json

# def get_fu
import pandas as pd


def get_results_df(experiment_dir: str, metric: str, parameters: List[str] = []):
    runs = [
        (int(run_dir.replace("run_", "")), os.path.join(experiment_dir, run_dir))
        for run_dir in os.listdir(experiment_dir) if run_dir.startswith("run_")
    ]

    df = []

    for run_id, run_dir in runs:
        with open(os.path.join(run_dir, "config.json"), "r") as f:
            config = json.load(f)

        with open(os.path.join(run_dir, "test_metrics.json"), "r") as f:
            metrics_file = json.load(f)

        acc = metrics_file.get(metric)
        row = [run_id, acc]

        for parameter in parameters:
            row.append(config.get(parameter))

        df.append(row)

    df = pd.DataFrame(df, columns=["run_id", "accuracy"] + parameters)
    df = df.sort_values(by="accuracy", ascending=False)

    return df
