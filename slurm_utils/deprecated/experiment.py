import json
import os

import shutil

import logging
import sys
import time

import pandas as pd

import invoke
from twine.settings import Settings
from twine.commands import upload

from slurm_utils.connection import SLURMConnector
from slurm_utils.runner import run_dummy_hyp_opt
from slurm_utils.deprecated.python_environment import PythonEnvironment


class SLURMExperiment:
    def __init__(
            self,
            proj_name="test_project",
            local_proj_dir=None,  # local proj dir
            experiment_config=None,
            ssh_config_file=os.path.join(os.path.expanduser("~"), ".ssh", "../config"),  # defaults to ~/.ssh/config
    ):
        # self.username = "stephana93"

        # set naming
        self.proj_name = proj_name

        # set and load experiment config file
        if isinstance(experiment_config, str):
            self.experiment_config_file = experiment_config
            with open(self.experiment_config_file, "r") as f:
                self.experiment_config = json.load(f)
        else:
            self.experiment_config = experiment_config
            self.experiment_config_file = None

        # set run specifix stuff
        self.experiment_name = self.experiment_config.get("experiment_name")
        self.run_file = self.experiment_config.get("run_settings", {}).get("train_file").replace(".py", "")

        # set server variables
        server_settings = self.experiment_config.get("server_settings", {})
        self.remote_gateway_script = server_settings.get("gateway_script", None)
        self.remote_slurm_script = server_settings.get("slurm_script", None)
        self.mem = server_settings.get("mem")
        self.num_cpu = server_settings.get("num_cpu")
        self.num_gpu = server_settings.get("num_gpu")

        # set connection settings
        self.hostname = server_settings.get("hostname", "vda-dgx")
        self.shell = SLURMConnector(
            hostname=self.hostname,
            ssh_config_file=ssh_config_file,
        )
        self.shell.connect()

        self.py_env = PythonEnvironment(proj_name=proj_name, type="conda", shell=self.shell)
        # initialize job_id
        self.job_id = None

        # set local file system variables
        self.local_proj_dir = local_proj_dir
        self.local_experiment_dir = os.path.join(self.local_proj_dir, "experiments", self.experiment_name)
        self.local_script_dir = os.path.join(self.local_experiment_dir, "../scripts")
        self.local_study_dir = os.path.join(self.local_experiment_dir, "study")

        # set remote fily system variables
        _, stout, _ = self.shell.execute(f"echo $STORAGE", check_err=True)
        self.remote_storage_dir = stout[-1]
        self.remote_proj_dir = os.path.join(self.remote_storage_dir, "projects", self.proj_name)
        self.remote_experiment_dir = os.path.join(self.remote_proj_dir, "experiments", self.experiment_name)
        self.remote_script_dir = os.path.join(self.remote_experiment_dir, "../scripts")
        self.remote_study_dir = os.path.join(self.remote_experiment_dir, "study")
        self.output_file = os.path.join(self.remote_experiment_dir, f"{self.experiment_name}_log.out")

        # set data dirs
        data_config = self.experiment_config.get("data")
        self.local_data_dir = data_config.get("local_data_dir")
        self.remote_data_dir = data_config.get("remote_data_dir")

    def connect(self):
        logging.info("Connecting to remote server.")
        self.shell.connect()
        logging.info("Setting up remote environment.")
        if self.remote_gateway_script is not None:
            _, stout, _ = self.shell.execute(f"source {self.remote_gateway_script}", check_err=True)
            logging.debug("\n ".join(stout))

        _, _, sterr = self.shell.execute("workon")
        logging.info(f"Available virtualenv environments: {', '.join(sterr)}")

    def close(self):
        self.shell.close()

    def prepare_local_experiment(self, clean_existing: bool = False):
        """
        :param clean_existing: Deletes old stuff. Should be used carefully.
            Probably most useful for model development.
        """
        if clean_existing and os.path.isdir(self.local_experiment_dir):
            shutil.rmtree(self.local_experiment_dir)

        self.create_local_dirs()
        self.write_config_file()
        self.create_local_scripts()

    def prepare_remote_experiment(self, clean_existing: bool = False, upload_code: bool = True):
        if not self.shell.is_connected():
            self.connect()

        # python setup
        # self.create_venv()
        if upload_code:
            self.pypi_upload()
            self.py_env.pip_install(self.proj_name)

        # local preparations
        self.prepare_local_experiment(clean_existing=clean_existing)

        # delete remote files
        if clean_existing:
            self.shell.execute(f"rm -rf {self.remote_experiment_dir}")

        # file setup
        self.create_remote_proj_dirs()
        self.create_remote_scripts()

    def create_venv(self, python_version: str = "3.8"):
        _, _, sterr = self.shell.execute("workon")
        if self.proj_name in sterr:
            logging.info(f"Env '{self.proj_name}' already installed")
            return

        logging.info(f"Create remote environment: {self.proj_name}")
        _, stout, _ = self.shell.execute(f"mkvirtualenv -p python{python_version} {self.proj_name}", check_err=True)
        logging.info("\n".join(stout))
        _, stout, _ = self.shell.execute("deactivate", check_err=True)

    def pypi_upload(self):
        logging.info(f"Package code for project: {self.proj_name}")
        invoke.run(f"cd {self.local_proj_dir} && python setup.py sdist bdist_wheel")

        logging.info("Uplaod packaged code to PyPI (https://knodle.cc/pypi/)")
        settings = Settings(repository_url="https://knodle.cc/pypi/", username="", password="")
        upload.upload(upload_settings=settings, dists=[f"{self.local_proj_dir}/dist/*"])

    def pip_install(self, uninstall_current: bool = True):
        logging.info(f"Install uploaded package {self.proj_name} remotely")
        # self.shell.execute(f"workon {self.proj_name}", check_err=True)
        self.shell.execute(f"conda activate {self.proj_name}", check_err=True)
        if uninstall_current:
            _, stout, _ = self.shell.execute(f"pip uninstall -y {self.proj_name}", check_err=True)
            logging.debug(stout)
        _, stout, _ = self.shell.execute(f"pip install {self.proj_name}", check_err=True)
        logging.debug(stout)

    def create_remote_proj_dirs(self):
        logging.info("Create remote directories:")

        logging.debug(f"1) Experiment directory: {self.remote_experiment_dir}")
        self.shell.execute(f"mkdir -p {self.remote_experiment_dir}", check_err=True)

        logging.debug(f"1) Script directory: {self.remote_experiment_dir}")
        self.shell.execute(f"mkdir -p {self.remote_script_dir}", check_err=True)

    def create_local_dirs(self):
        logging.info("Create local directories.")

        logging.debug(f"1) Experiment directory: {self.local_experiment_dir}")
        os.makedirs(self.local_experiment_dir, exist_ok=True)

        logging.debug(f"2) Scripts directory: {self.local_script_dir}")
        os.makedirs(self.local_script_dir, exist_ok=True)

    def squeue(self):
        return self.shell.squeue()

    def available_resources(self):
        return self.shell.available_resources()

    def create_local_scripts(self):
        logging.info("Write run files: run_hyperparameter_optimization.py, optimize.py, test.sh, run.sbatch")
        self.write_test_file()
        self.write_main_file()
        self.write_optimize_file()
        self.write_config_file()

        self.write_sbatch()

    def create_remote_scripts(self):
        logging.info("Upload SBATCH and configuration files")

        files = ["run.sbatch", "config.json", "optimize.py", "main.py"]
        for file in files:
            local_file = os.path.join(self.local_script_dir, file)
            remote_file = os.path.join(self.remote_script_dir, file)
            print(file, os.path.isfile(local_file), remote_file)
            self.shell.upload_file(local_file, remote_file)

    def write_config_file(self):
        if self.experiment_config_file:
            with open(self.experiment_config_file, "r") as f:
                self.experiment_config = json.load(f)

        with open(os.path.join(self.local_script_dir, "config.json"), "w") as f:
            json.dump(self.experiment_config, f)

    def write_sbatch(self):
        sbatch_file = "#!/bin/bash \n"
        sbatch_file += "\n"
        sbatch_file += "#SBATCH --nodes=1                          ## always 1 (we have just 1 server)\n"
        sbatch_file += f"#SBATCH --job-name={self.proj_name}_{self.experiment_name}        ## name you give to your job\n"
        sbatch_file += f"#SBATCH --output={self.output_file}       ## sysout and syserr merged together\n"
        sbatch_file += f"#SBATCH --cpus-per-task={self.num_cpu}    ## number of cores for the job - max 80\n"
        sbatch_file += f"#SBATCH --mem={self.mem}G                  ## total memory for the job - max 512G\n"
        if self.num_gpu > 0:
            sbatch_file += f"#SBATCH --gres=gpu:{self.num_gpu}         ## number of GPUs for the job - max :8\n"
        sbatch_file += "\n"
        sbatch_file += "# environment setup\n"
        sbatch_file += f"PROJ_NAME={self.proj_name}\n"
        if self.remote_slurm_script is not None:
            sbatch_file += "# Run environment preparation script\n"
            sbatch_file += f"source {self.remote_slurm_script}\n"
            sbatch_file += f"echo $WORKON_HOME\n"

        sbatch_file += f"EXECUTABLE=$CONDA_ENVS_PATH/{self.proj_name}/bin/python\n"
        sbatch_file += f"RUN_FILE={self.remote_script_dir}/main.py\n"
        sbatch_file += "\n"
        sbatch_file += "# variables\n"
        sbatch_file += f"EXPERIMENT={self.experiment_name}\n"
        sbatch_file += f"DATA_DIR={self.remote_data_dir}\n"
        sbatch_file += f"WORK_DIR={self.remote_experiment_dir}\n"
        sbatch_file += f"CONFIG_FILE={self.remote_script_dir}/config.json\n"
        sbatch_file += "\n"
        sbatch_file += "\n"
        sbatch_file += f"pip freeze > {os.path.join(self.remote_experiment_dir, 'freezed_requirements.txt')}\n"
        sbatch_file += "\n"
        sbatch_file += "\n"
        sbatch_file += "export XLA_FLAGS=--xla_gpu_force_compilation_parallelism=1 \n"
        sbatch_file += "\n"
        sbatch_file += "\n"
        sbatch_file += f"python {self.remote_script_dir}/optimize.py \\\n"
        sbatch_file += "    --executable $EXECUTABLE \\\n"
        sbatch_file += "    --run_file $RUN_FILE \\\n"
        sbatch_file += "    --data_dir $DATA_DIR \\\n"
        sbatch_file += "    --work_dir $WORK_DIR \\\n"
        sbatch_file += "    --config_file $CONFIG_FILE"

        with open(os.path.join(self.local_script_dir, "run.sbatch"), "w") as f:
            f.write(sbatch_file)

    def write_main_file(self):
        run_file = "from absl import app\n"
        run_file += "\n"
        run_file += f"from {self.proj_name}.{self.run_file} import main\n"
        run_file += "\n"
        run_file += "if __name__ == '__main__':\n"
        run_file += "    app.run(main)\n"
        run_file += "\n"

        with open(os.path.join(self.local_script_dir, "main.py"), "w") as f:
            f.write(run_file)

    def write_optimize_file(self):
        py_file = "import argparse\n"
        py_file += "\n"
        py_file += "from slurm_utils.runner import run_hyp_opt\n"
        py_file += "\n"
        py_file += "\n"
        py_file += "if __name__ == '__main__':\n"
        py_file += "    parser = argparse.ArgumentParser()\n"
        py_file += "    parser.add_argument('--executable', help='Executable of the current project.')\n"
        py_file += "    parser.add_argument('--run_file', help='File that starts the training procedure.')\n"
        py_file += "    parser.add_argument('--data_dir', help='Data directory.')\n"
        py_file += "    parser.add_argument('--work_dir', help='Working directory.')\n"
        py_file += "    parser.add_argument('--config_file', help='Working directory.', default='')\n"
        py_file += "\n"
        py_file += "    args = parser.parse_args()\n"
        py_file += "\n"
        py_file += "    run_hyp_opt(\n"
        py_file += "        executable=args.executable,\n"
        py_file += "        run_file=args.run_file,\n"
        py_file += "        work_dir=args.work_dir,\n"
        py_file += "        data_dir=args.data_dir,\n"
        py_file += "        config_file=args.config_file\n"
        py_file += "    )\n"

        with open(os.path.join(self.local_script_dir, "optimize.py"), "w") as f:
            f.write(py_file)

    def write_test_file(self):
        sh_file = "#!/usr/bin/env bash \n"
        sh_file += "\n"
        sh_file += "# project setup\n"
        sh_file += f"PROJ_NAME={self.proj_name}\n"
        sh_file += f"PROJ_DIR={self.local_proj_dir}\n"
        sh_file += f"EXECUTABLE={sys.executable}\n"
        sh_file += f"RUN_FILE={self.local_script_dir}/main.py\n"
        sh_file += "\n"
        sh_file += "\n"
        sh_file += "# experiment variables\n"
        sh_file += f"EXPERIMENT={self.experiment_name}\n"
        sh_file += f"DATA_DIR={self.local_data_dir}\n"
        sh_file += f"WORK_DIR={self.local_experiment_dir}\n"
        sh_file += f"CONFIG_FILE={self.local_script_dir}/'config.json')\n"
        sh_file += "\n"
        sh_file += f"pip freeze > {self.local_experiment_dir}/'freezed_requirements.txt')\n"
        sh_file += "\n"
        sh_file += "\n"
        sh_file += f"PYTHON_PATH={self.local_proj_dir}\n"
        sh_file += f"PYTHONPATH=$PYTHON_PATH python {self.local_script_dir}/optimize.py \\\n"
        sh_file += "    --executable $EXECUTABLE \\\n"
        sh_file += "    --run_file $RUN_FILE \\\n"
        sh_file += "    --data_dir $DATA_DIR \\\n"
        sh_file += "    --work_dir $WORK_DIR \\\n"
        sh_file += "    --config_file $CONFIG_FILE \n"

        test_file = os.path.join(self.local_script_dir, "test.sh")
        with open(test_file, "w") as f:
            f.write(sh_file)
        invoke.run(f"chmod 700 {test_file}")

    def run_locally(self):
        test_file = os.path.join(self.local_script_dir, "test.sh")
        invoke.run(test_file)

    def run_dummy(self):
        run_dummy_hyp_opt(
            executable="python",
            train_file=os.path.join(self.local_script_dir, "main.py"),
            work_dir=self.local_experiment_dir,
            data_dir=self.local_data_dir,
            config_file=os.path.join(self.local_script_dir, 'config.json')
        )

    def run_remote(self, upload_code: bool = True, cancel_running_job: bool = False):

        t = time.time()
        if upload_code:
            self.pypi_upload()
            self.py_env.pip_install()

        self.create_remote_scripts()
        logging.info(f"Preparing run took {time.time() - t} seconds.")
        return self.run_sbatch_file(cancel_running_job=cancel_running_job)

    def scancel(self, job_id: int = None):

        if job_id is not None:
            self.shell.execute(f"scancel {job_id}", check_err=True)
            return self.squeue()

        if self.get_status() in ["PENDING", "RUNNING"]:
            self.shell.execute(f"scancel {self.job_id}", check_err=True)
        self.job_id = None
        return self.squeue()

    def run_sbatch_file(self, cancel_running_job: bool = False):
        if cancel_running_job:
            self.scancel()

        if isinstance(self.job_id, int):
            logging.error(
                f"There is already a job (ID: {self.job_id}) related to this experiment. Cancel first.")
            return

        _, stout, sterr = self.shell.execute(f"sbatch {self.remote_script_dir}/run.sbatch", check_err=True)
        self.job_id = int(stout[0].replace("Submitted batch job ", ''))
        return self.squeue()

    def get_job_info(self):
        if not isinstance(self.job_id, int):
            return {
                "JOBID": None,
                "STATUS": "NOT_SUBMITTED"
            }

        df = self.squeue()
        df = df[df["JOBID"] == str(self.job_id)]
        if len(df) > 0:
            return df.iloc[0].to_dict()
        else:
            return {
                "JOBID": self.job_id,
                "STATUS": "FINISHED"
            }

    def get_status(self):
        return self.get_job_info().get("STATUS")

    def print_current_output(self):
        status = self.get_status()
        if status == "NOT_SUBMITTED":
            logging.info("Job was not started yet. Use run_remote() to do so")
            return

        if status == "PENDING":
            logging.info("Job is currently waiting for resources.")
            return

        local_output_file = os.path.join(self.local_experiment_dir, f"{self.experiment_name}_log.out")
        if os.path.isfile(local_output_file):
            os.remove(local_output_file)

        self.shell.download(self.output_file, local_output_file)

        logging.info(f"Job is currently in status {status}.")
        with open(local_output_file, 'r') as f:
            lines = "".join(f.readlines())
            print(lines)

    def get_results(self):
        local_results = os.path.join(self.local_experiment_dir, "result_df.csv")
        if self.job_id is not None:
            self.shell.download(os.path.join(self.remote_experiment_dir, "result_df.csv"), local_results)

        return pd.read_csv(local_results, sep=";")

    def download_experiment_folder(self):
        self.shell.download_folder(self.remote_experiment_dir, self.local_experiment_dir)
