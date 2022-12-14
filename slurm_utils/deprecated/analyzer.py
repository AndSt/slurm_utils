from typing import List

import os
import shutil

import pandas as pd

from slurm_utils.deprecated.connection import SLURMConnector
from slurm_utils.deprecated.experiment_results import ExperimentResult


class ResultAnalyzer:
    def __init__(self,
                 hostname=None,
                 proj_name: str = "test_project",
                 local_experiment_dir: str = None,
                 remote_experiment_dir: str = None,
                 ssh_config_file=os.path.join(os.path.expanduser("~"), ".ssh", "config"),  # defaults to ~/.ssh/config
                 ):
        # set connection settings
        self.shell = SLURMConnector(
            hostname=hostname,
            ssh_config_file=ssh_config_file
        )
        self.shell.connect()
        self.username = self.shell.username

        # set naming
        self.proj_name = proj_name
        self.local_experiment_dir = local_experiment_dir
        self.remote_experiment_dir = remote_experiment_dir

    def download_experiments(self, filter_fn=None, skip_existing: bool = True):
        # filter_fn is a function taking a list of files and returning a list of files
        self.shell.download_folder(self.remote_experiment_dir, self.local_experiment_dir, skip_existing=True)

    def download_result_dfs(self):
        self.shell.download_extension(self.remote_experiment_dir, self.local_experiment_dir, ".json")

    def download_test_metrics(self, skip_existing: bool = False):
        self.shell.download_test_metrics(
            self.remote_experiment_dir, self.local_experiment_dir, skip_existing=skip_existing
        )

    def clean_local(self):
        if os.path.isdir(self.local_experiment_dir):
            shutil.rmtree(self.local_experiment_dir)

        # os.makedirs(self.local_experiment_dir, exist_ok=True)

    def merge_experiments(self, old_names: List[str], new_name):
        """Merge experiments. For example one type per

        :param old_names:
        :param new_name:
        :return:
        """

    def result_df(self, by=None):
        dfs = []

        for exp in os.listdir(self.local_experiment_dir):
            e = ExperimentResult(os.path.join(self.local_experiment_dir, exp))
            exp_df = e.run_df(by=by)
            if exp_df is None:
                continue
            exp_df["experiment"] = exp

            dfs.append(exp_df)

        return pd.concat(dfs)
