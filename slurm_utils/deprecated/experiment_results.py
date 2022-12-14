from typing import Optional, List

import json
import os

import pandas as pd


class ExperimentResult:
    def __init__(self, local_dir: str):
        # TODO check if scripts, config, runs exist

        self.local_dir = local_dir
        self.script_dir = os.path.join(self.local_dir, "scripts")

        with open(os.path.join(self.script_dir, "config.json"), "r") as f:
            self.exp_config = json.load(f)
            
        self.objective = self.exp_config.get("run_settings").get("objective")

    def standard_result_df(self):
        return pd.read_csv(os.path.join(self.local_dir, "result_df.csv"), sep=";")

    def run_df(self, by: Optional[List[List[str]]] = None):
        # Either uses standard objective (used hyp. param opt.) or dives into test_metrics.json by "by" value

        df = []
        runs = [run_dir for run_dir in os.listdir(self.local_dir) if run_dir.startswith("run_")]
        if len(runs) == 0:
            return None
        
        for run in runs:
            run_dir = os.path.join(self.local_dir, run)
            try:
                with open(os.path.join(run_dir, "config.json"), "r") as f:
                    config = json.load(f)

                with open(os.path.join(run_dir, "test_metrics.json"), "r") as f:
                    metrics = json.load(f)
            except:
                continue
                
            row = config
            if by is None:
                if self.objective == "accuracy":
                    row[self.objective] = metrics.get("y_metrics").get("accuracy")
                else:
                    row[self.objective] = metrics.get("y_metrics").get("1").get("f1-score")
            else:
                for chain in by:
                    key = chain[1]
                    val = metrics.copy()
                    for elt in chain:
                        val = val.get(elt)
                    row[key] = val
            df.append(row)
        if len(df) == 0:
            return None
        df = pd.DataFrame(df, columns=df[0].keys())

        return df
        