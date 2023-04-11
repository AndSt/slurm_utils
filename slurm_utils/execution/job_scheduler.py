import logging
import os

import time
import json

import subprocess
import invoke

from sherpa import Study
from slurm_utils.config.resources import ResourceConfig

from slurm_utils.execution.parameters import RunConfig


class JobScheduler:
    def __init__(
            self,
            study: Study,
            config: RunConfig,
            executable: str,
            work_dir: str,
            data_dir: str,
            resource_config: ResourceConfig
    ):

        self.study = study
        self.config = config

        self.work_dir = work_dir
        self.data_dir = data_dir

        self.resource_config = resource_config
        self.max_processes = resource_config.ntasks

        self.executable = executable  # either local, or otherwise accelerate is used

        self.processes = {}

    def write_job_config(self, run_id: int, trial):
        work_dir = os.path.join(self.work_dir, f"run_{run_id}")

        config = trial.parameters
        config["data_dir"] = self.data_dir
        config["work_dir"] = work_dir
        config["objective"] = self.config.objective

        config["log_dir"] = work_dir
        config["verbosity"] = 0

        config_file = os.path.join(work_dir, "config.cfg")
        with open(config_file, "w") as f:
            for k, v in config.items():
                f.write(f"--{k}={v} \n")

        config_json = os.path.join(work_dir, "config.json")
        with open(config_json, "w") as f:
            json.dump(config, f)

        return config_file

    def write_run_command(self, run_id, executable):
        file = f"""
MAIN_FILE={os.path.join(self.work_dir, "scripts", "main.py")}
FLAG_FILE={os.path.join(self.work_dir, f"run_{run_id}", "config.cfg")}

{executable} $MAIN_FILE --flagfile=$FLAG_FILE
"""
        return file

    def save_single_run_file(self, run_id, file):
        single_run_path = os.path.join(self.work_dir, f"run_{run_id}", "single_run.sh")
        with open(single_run_path, "w") as f:
            f.write(file)
        invoke.run(f"chmod 700 {single_run_path}")

    def write_trial_run_file(self, run_id):
        raise NotImplementedError("Please Implement this method.")

    def num_processes_running(self):
        nr = sum([1 for proc in self.processes.values() if proc["is_active"] == "is_running"])
        return nr

    def num_finished_running(self):
        nr = sum([1 for proc in self.processes.values() if proc["is_active"] == "is_finished"])
        return nr

    def wait_until_resources_available(self):
        while self.num_processes_running() >= self.max_processes:
            self.poll_processes()
            time.sleep(1)

    def wait_until_all_finished(self):
        logging.info("Waiting until processes are finished.")
        while not all([proc["is_active"] == "is_finished" for proc in self.processes.values()]):
            self.poll_processes()
            time.sleep(1)
        logging.info("All processes are finished.")

    def create_run_command(self, run_id):
        raise NotImplementedError("Please Implement this method.")

    def submit_process(self, run_id, trial):
        logging.info(f"Start Trial {trial.id}, with parameters {trial.parameters}")

        # write command
        execution_sh_command = self.create_run_command(run_id)

        # save command to file
        work_dir = os.path.join(self.work_dir, f"run_{run_id}")
        execution_sh_file = os.path.join(work_dir, "run_command.sh")
        with open(execution_sh_file, "w") as f:
            f.write(" ".join(execution_sh_command))
        invoke.run(f"chmod 700 {execution_sh_file}")

        # open process
        f = open(os.path.join(work_dir, 'output.out'), 'w')
        process = subprocess.Popen(execution_sh_command, stderr=f, stdout=f)

        # set statistics
        self.processes[run_id] = {
            "process": process,
            "file": f,
            "start_time": time.time(),
            "trial": trial,
            "is_active": "is_running"
        }

    def poll_processes(self):
        for run_id, process_dict in self.processes.items():
            process = process_dict["process"]
            is_finished = process.poll()

            if is_finished is not None and self.processes[run_id]["is_active"] == "is_running":
                self.processes[run_id]["is_active"] = "stopped_running"
                self.finish_process(run_id)

    def finish_process(self, run_id: str):
        if run_id not in self.processes:
            return

        work_dir = os.path.join(self.work_dir, f"run_{run_id}")

        process_dict = self.processes[run_id]
        process_dict["file"].close()

        returncode = process_dict["process"].returncode
        process_stats = {
            "time_in_secs": time.time() - process_dict["start_time"],
            "returncode": returncode
        }
        with open(os.path.join(work_dir, "process_stats.json"), "w") as f:
            json.dump(process_stats, f)

        test_metrics_file = os.path.join(work_dir, "test_metrics.json")
        if returncode == 0 and os.path.isfile(test_metrics_file):
            with open(test_metrics_file, "r") as f:
                metrics = json.load(f)
                if self.config.objective not in metrics:
                    raise RuntimeError(
                        f"You have to write a file called test_metrics.json which holds a key {self.config.objective}"
                    )
                result = metrics.get(self.config.objective)

            self.study.add_observation(process_dict["trial"], iteration=1, objective=result, context=metrics)
        elif returncode == 0:
            self.study.add_observation(
                process_dict["trial"], iteration=1, objective=0, context={"help": "No metrics provided"}
            )
            result = "No result"
        else:
            self.study.add_observation(process_dict["trial"], iteration=1, objective=0, context={"error": returncode})
            result = "No result"

        logging.info(f"Finalize trial {process_dict['trial'].id}, {self.config.objective}: {result}")

        self.study.finalize(process_dict["trial"])
        self.study.save()

        self.processes[run_id]["is_active"] = "is_finished"

    def finish_processes(self):
        for run_id, process_dict in self.processes.items():
            if process_dict["is_active"] == "stopped_running":
                self.finish_process(run_id=run_id)

    def loop_hyperparams(self):
        for trial in self.study:
            # wait for free resources
            self.wait_until_resources_available()

            # run clean up routines for finished jobs
            self.finish_processes()

            run_id = trial.id
            os.makedirs(os.path.join(self.work_dir, f"run_{run_id}"), exist_ok=True)
            self.write_job_config(run_id=run_id, trial=trial)
            self.write_trial_run_file(run_id=run_id)
            self.submit_process(run_id=run_id, trial=trial)

        logging.info("Started all trials")
