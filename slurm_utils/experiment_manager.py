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
from slurm_utils.config.load import load_config

from slurm_utils.connection import RemoteConnector
from slurm_utils.file_writer import ServerFileWriter, LocalFileWriter


class ExperimentManager:
    def __init__(self, experiment_config: Union[Dict, str] = None):
        self.experiment_config_file = experiment_config
        self.experiment_config = load_config(self.experiment_config_file)

        # set constants
        self.proj_name = self.experiment_config.get("project_name")
        self.experiment_name = self.experiment_config.get("experiment_name")

        self.storage_dir = invoke.run("echo $SU_STORAGE").stdout.replace("\n", "")

        logging.info("Storage dir: " + self.storage_dir)
        self.folder_config = FolderConfig(
            experiment_config=self.experiment_config,
            storage_dir=self.storage_dir,
            data_dir=self.experiment_config.get("data").get("local_data_dir")
        )


class ServerExperimentManager(ExperimentManager):
    def __init__(self, experiment_config: Union[Dict, str] = None):
        super().__init__(experiment_config=experiment_config)
        self.resource_config = ResourceConfig(hostname=None, experiment_config=self.experiment_config)
        self.folder_config = FolderConfig(
            experiment_config=self.experiment_config,
            storage_dir=self.storage_dir,
            data_dir=self.experiment_config.get("data").get("remote_data_dir")
        )

    def run_experiment(self, clean_existing: bool = True):
        logging.info("Starting experiment.")
        t = time.time()
        # local preparations
        if clean_existing and os.path.isdir(self.folder_config.experiment_dir):
            shutil.rmtree(self.folder_config.experiment_dir)

        self.folder_config.create_directories()

        # write all files
        with open(os.path.join(self.folder_config.script_dir, "config.json"), "w") as f:
            json.dump(self.experiment_config, f)

        file_writer = ServerFileWriter(folder_config=self.folder_config, resource_config=self.resource_config)
        file_writer.write_pyhton_main_file()
        file_writer.write_execution_file()

        # file setup
        logging.info(f"Preparing run took {time.time() - t} seconds.")

        output = invoke.run(f"sbatch {self.folder_config.script_dir}/run.sbatch")
        logging.info("Sbatch run is started.")


class LocalExperimentManager(ExperimentManager):

    def run_experiment(self, clean_existing: bool = True):
        t = time.time()
        # local preparations
        if clean_existing and os.path.isdir(self.folder_config.experiment_dir):
            shutil.rmtree(self.folder_config.experiment_dir)

        self.folder_config.create_directories()

        # write all files
        with open(os.path.join(self.folder_config.script_dir, "config.json"), "w") as f:
            json.dump(self.experiment_config, f)

        file_writer = LocalFileWriter(folder_config=self.folder_config)
        file_writer.write_pyhton_main_file()
        file_writer.write_execution_file()
        # file setup
        logging.info(f"Preparing run took {time.time() - t} seconds.")

        test_file = os.path.join(self.folder_config.script_dir, "test.sh")
        output = invoke.run(test_file)
        logging.info("Sh run is started.")


class RemoteExperimentManager(ExperimentManager):
    def __init__(self, experiment_config: Union[Dict, str] = None):
        super().__init__(experiment_config=experiment_config)

        self.hostname = self.experiment_config.get("server_settings").get("hostname")
        self.conn = RemoteConnector(hostname=self.hostname)

        self.remote_proj_dir = os.path.join(self.conn.get_storage_dir(), "projects", self.proj_name)

    def close(self):
        self.conn.close()

    def pypi_upload(self):
        logging.info(f"Package code for project: {self.proj_name}")
        invoke.run(f"cd {self.folder_config.proj_dir} && python setup.py sdist bdist_wheel")

        pypi_server = os.getenv("PYPI_SERVER")
        pypi_user = os.getenv("PYPI_USER")
        pypi_password = os.getenv("PYPI_PASSWORD")
        print(pypi_server, pypi_user, pypi_password)
        logging.info(f"Upload packaged code to PyPI ({pypi_server})")
        settings = Settings(
            repository_url=pypi_server,
            username=pypi_user,
            password=pypi_password
        )
        upload.upload(upload_settings=settings, dists=[f"{self.folder_config.proj_dir}/dist/*"])

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

    def get_remote_script_file(self):
        script_file_name = os.path.basename(self.experiment_config_file)
        script_file = os.path.join(self.remote_proj_dir, "scripts", "remote", script_file_name)
        return script_file

    def prepare_remote(self, upload_code: bool = False):
        t = time.time()
        if upload_code:
            self.pypi_upload()
            self.pip_install()

        # upload yaml file
        self.conn.execute(f"mkdir -p {self.remote_proj_dir}/scripts/remote")
        self.conn.upload(
            local_path=self.experiment_config_file,
            remote_path=self.get_remote_script_file()
        )
        logging.info(f"Preparing run took {time.time() - t} seconds.")

    def run_remote(self, upload_code: bool = False):
        self.prepare_remote(upload_code=upload_code)

        remote_script_file = self.get_remote_script_file()
        command = f"""source $SU_STORAGE/server_setup/standard_init.sh; 
        conda activate {self.proj_name};
        su_sbatch {remote_script_file}
        """
        output = self.conn.execute(command)
        logging.info(output)
