from typing import Dict
import os

import logging


class FullFolderConfig:
    def __init__(self, experiment_config: Dict, local_proj_dir: str = None, remote_proj_dir: str = None):
        self.proj_name = experiment_config.get("project_name")
        self.experiment_name = experiment_config.get("experiment_name")

        if local_proj_dir is not None:
            # set local file system variables
            self.local_proj_dir = local_proj_dir
            self.local_experiment_dir = os.path.join(self.local_proj_dir, "experiments", self.experiment_name)
            self.local_script_dir = os.path.join(self.local_experiment_dir, "scripts")
            self.local_study_dir = os.path.join(self.local_experiment_dir, "study")

        # set remote fily system variables
        self.remote_storage_dir = remote_proj_dir
        self.remote_proj_dir = os.path.join(self.remote_storage_dir, "projects", self.proj_name)
        self.remote_experiment_dir = os.path.join(self.remote_proj_dir, "experiments", self.experiment_name)
        self.remote_script_dir = os.path.join(self.remote_experiment_dir, "scripts")
        self.remote_study_dir = os.path.join(self.remote_experiment_dir, "study")
        self.output_file = os.path.join(self.remote_experiment_dir, f"{self.experiment_name}_log.out")

        # set data dirs
        data_config = experiment_config.get("data")
        self.local_data_dir = data_config.get("local_data_dir")
        self.remote_data_dir = data_config.get("remote_data_dir")

        # run_file
        self.run_file = experiment_config.get("run_settings", {}).get("train_file").replace(".py", "")

    def create_local_directories(self):
        logging.info("Create local directories.")

        logging.debug(f"1) Experiment directory: {self.local_experiment_dir}")
        os.makedirs(self.local_experiment_dir, exist_ok=True)

        logging.debug(f"2) Scripts directory: {self.local_script_dir}")
        os.makedirs(self.local_script_dir, exist_ok=True)

    def create_remote_dirs(self, connection):
        logging.info("Create remote directories:")

        logging.debug(f"1) Experiment directory: {self.remote_experiment_dir}")
        connection.execute(f"mkdir -p {self.remote_experiment_dir}")

        logging.debug(f"1) Script directory: {self.remote_experiment_dir}")
        connection.execute(f"mkdir -p {self.remote_script_dir}")


class FolderConfig:
    def __init__(self, experiment_config: Dict, storage_dir: str = None, data_dir: str = None):
        self.proj_name = experiment_config.get("project_name")
        self.experiment_name = experiment_config.get("experiment_name")

        # set remote fily system variables
        self.storage_dir = storage_dir
        print(storage_dir, self.proj_name)
        self.proj_dir = os.path.join(self.storage_dir, "projects", self.proj_name)
        self.experiment_dir = os.path.join(self.proj_dir, "experiments", self.experiment_name)
        self.script_dir = os.path.join(self.experiment_dir, "scripts")
        self.study_dir = os.path.join(self.experiment_dir, "study")
        self.output_file = os.path.join(self.experiment_dir, f"{self.experiment_name}_log.out")

        # set data dirs
        self.data_dir = data_dir

        # run_file
        self.run_file = experiment_config.get("run_settings", {}).get("train_file").replace(".py", "")

    def create_directories(self):
        logging.info("Create directories.")

        logging.debug(f"1) Experiment directory: {self.experiment_dir}")
        os.makedirs(self.experiment_dir, exist_ok=True)

        logging.debug(f"2) Scripts directory: {self.script_dir}")
        os.makedirs(self.script_dir, exist_ok=True)
