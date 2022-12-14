from typing import Union, Dict
import json

import os
import shutil

import time
import logging

import invoke
from twine.settings import Settings
from twine.commands import upload

from slurm_utils.config.folder import FolderConfig
from slurm_utils.config.resources import ResourceConfig

from slurm_utils.connection import RemoteConnector
from slurm_utils.file_writer import FileWriter


class ExperimentManager:
    def __init__(
            self,
            local_proj_dir: str,
            hostname: str = None,
            experiment_config: Union[Dict, str] = None,
    ):
        # set and load experiment config file
        if isinstance(experiment_config, str):
            self.experiment_config_file = experiment_config
            with open(self.experiment_config_file, "r") as f:
                self.experiment_config = json.load(f)
        else:
            self.experiment_config = experiment_config
            self.experiment_config_file = None

        if hostname is None or hostname == "":
            self.hostname = self.experiment_config.get("server_settings").get("hostname")
        else:
            self.hostname = hostname

        self.conn = RemoteConnector(hostname=self.hostname)

        self.proj_name = self.experiment_config.get("project_name")
        self.experiment_name = self.experiment_config.get("experiment_name")

        self.folder_config = FolderConfig(
            self.experiment_config, local_proj_dir, self.conn.get_storage_dir()
        )
        self.resource_config = ResourceConfig(hostname=self.hostname, experiment_config=self.experiment_config)

    def close(self):
        self.conn.close()
        # finishing stuff

    def pypi_upload(self):
        logging.info(f"Package code for project: {self.proj_name}")
        invoke.run(f"cd {self.folder_config.local_proj_dir} && python setup.py sdist bdist_wheel")

        logging.info("Uplaod packaged code to PyPI (https://knodle.cc/pypi/)")
        settings = Settings(repository_url="https://knodle.cc/pypi/", username="", password="")
        upload.upload(upload_settings=settings, dists=[f"{self.folder_config.local_proj_dir}/dist/*"])

    def pip_install(self):
        logging.info(f"Install uploaded package {self.proj_name} remotely")
        install_command = f"""source $SU_STORAGE/server_setup/standard_init.sh; 
        conda activate {self.proj_name};
        pip uninstall -y slurm_utils;
        pip install slurm_utils;
        pip uninstall -y {self.proj_name};
        pip install {self.proj_name}
        """
        self.conn.execute(install_command)

    def prepare_local_experiment(self, clean_existing: bool = False):
        """
        :param clean_existing: Deletes old stuff. Should be used carefully.
            Probably most useful for model development.
        """
        if clean_existing and os.path.isdir(self.folder_config.local_experiment_dir):
            shutil.rmtree(self.folder_config.local_experiment_dir)

        self.folder_config.create_local_directories()

        # write all files
        with open(os.path.join(self.folder_config.local_script_dir, "config.json"), "w") as f:
            json.dump(self.experiment_config, f)

        file_writer = FileWriter(folder_config=self.folder_config, resource_config=self.resource_config)
        file_writer.write_main_file()
        file_writer.write_optimization_file()

        file_writer.write_port_finder_file()

        file_writer.write_test_file()
        file_writer.write_sbatch_file()

    def upload_scripts(self):
        logging.info("Upload SBATCH and configuration files")

        files = ["port_finder.sh", "run.sbatch", "config.json", "optimize.py", "main.py"]
        for file in files:
            local_file = os.path.join(self.folder_config.local_script_dir, file)
            remote_file = os.path.join(self.folder_config.remote_script_dir, file)
            self.conn.upload(local_file, remote_file)

    def prepare_remote_experiment(self, clean_existing: bool = False, upload_code: bool = True):
        # python setup
        if upload_code:
            self.pypi_upload()
            self.pip_install()

        # local preparations
        self.prepare_local_experiment(clean_existing=clean_existing)

        # delete remote files
        if clean_existing:
            self.conn.execute(f"rm -rf {self.folder_config.remote_experiment_dir}")

        # file setup
        self.folder_config.create_remote_dirs(self.conn)
        self.upload_scripts()

    def run_locally(self):
        test_file = os.path.join(self.folder_config.local_script_dir, "test.sh")
        invoke.run(test_file)

    def run_remote(self, upload_code: bool = False):

        t = time.time()
        if upload_code:
            self.pypi_upload()
            self.pip_install()

        logging.info(f"Preparing run took {time.time() - t} seconds.")
        output = self.conn.execute(f"sbatch {self.folder_config.remote_script_dir}/run.sbatch")
        logging.info(output)
        return output.split(" ")[-1]
