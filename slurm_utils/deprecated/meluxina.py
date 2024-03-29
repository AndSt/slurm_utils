import logging
import os
import sys
import time

import random
import json

import subprocess
import invoke

from sherpa import Study
from slurm_utils.config.resources import ResourceConfig

from slurm_utils.deprecated.postprocessing import log_best_results
from slurm_utils.deprecated.parameter_config import RunConfig


# def _port_finder(start: int = 27000, end: int = 28000):
#     """
#     Helper function to find free port in range.
#
#     Args:
#         start (int): start point of port range.
#         end (int): end point of port range.
#     """
#
#     def check_socket(host, port):
#         with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
#             if sock.connect_ex((host, port)) == 0:
#                 return False
#             else:
#                 return True
#
#     try:
#         hostname = socket.gethostname()
#         for port in range(start, end):
#             if check_socket(hostname, port):
#                 return port
#
#     except socket.gaierror:
#         raise BaseException('Hostname could not be resolved. Exiting')
#
#     except socket.error:
#         raise BaseException("Couldn't connect to execution")


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

        self.executable = executable
        # if executable == "local":
        # self.command = ["sh"]
        # else:
        # port_cmd = os.path.join(self.work_dir, 'scripts', 'port_finder.sh')
        # self.command = [
        #     "env",
        #     f"RUN_PORT=`{port_cmd}`",
        #     "srun",
        #     "-v",
        #     "-v",
        #     "--nodes=1",
        #     f"--ntasks=1",
        #     f"--gpus-per-task={resource_config.host_specific.get('gpus-per-task', 2)}",
        #     f"--cpus-per-task={resource_config.host_specific.get('cpus-per-task', 1)}",
        #     "--exact"
        # ]  # , "--gpus-per-task=2", "--cpus-per-task=8"]

        self.processes = {}

    def generate_run_id(self):
        run_id = random.randint(0, 1000)
        work_dir = os.path.join(self.work_dir, f"run_{run_id}")
        while os.path.isdir(work_dir):
            run_id = random.randint(0, 1000)
            work_dir = os.path.join(self.work_dir, f"run_{run_id}")

        os.makedirs(work_dir, exist_ok=True)
        return run_id

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

    # accelerate launch --num_processes $((8 * $COUNT_NODE)) --num_machines $COUNT_NODE --multi_gpu
    # --machine_rank $THEID --main_process_ip $MASTER_ADDR - -main_process_port $MASTER_PORT
    # / fsx / dalle2 / DALLE2 - pytorch / train_decoder.py - -config_file / fsx / dalle2 / testing_config.json

    def write_trial_run_file(self, run_id):

        if self.executable == "local":
            executable = sys.executable
        else:
            # gpus_per_task = self.resource_config.host_specific.get("gpus-per-task")
            # if gpus_per_task == 1:
            #     executable = "python"  # "accelerate launch --multi_gpu "
            # else:
            #     executable = f"accelerate launch --multi_gpu --num_processes {gpus_per_task} --num_machines 1 --main_process_ip $HOSTNAME --main_process_port $RUN_PORT "
            # executable = f"accelerate launch --mixed_precision fp16 --multi_gpu --num_processes {self.resource_config.host_specific.get('gpus-per-task', 2)} --num_machines 1 --main_process_port $RUN_PORT"
            executable = f"accelerate launch --mixed_precision fp16 --multi_gpu --num_processes 1 --num_machines 1 --main_process_port $RUN_PORT"
        file = f"""#!/bin/bash

# environment setup
PROJ_NAME={self.resource_config.proj_name}

# Prepare environment
"""
        if self.executable != "local":
            file += f"source $SU_STORAGE/server_setup/init_slurm.sh"
        else:
            file += f"workon $PROJ_NAME"

        file += f"""
        
# sent to sub script
export HOSTNAMES=`scontrol show hostnames "$SLURM_JOB_NODELIST"`
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export COUNT_NODE=`scontrol show hostnames "$SLURM_JOB_NODELIST" | wc -l`

echo HOSTNAMES=$HOSTNAMES
echo HOSTNAME=$HOSTNAME
echo MASTER_ADDR=$MASTER_ADDR
echo COUNT_NODE=$COUNT_NODE
echo ""

echo SLURM_TASK_PID=$SLURM_TASK_PID
echo SLURM_STEP_ID=$SLURM_STEP_ID
echo SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
echo RUN_PORT=$RUN_PORT
echo ""

MAIN_FILE={os.path.join(self.work_dir, "scripts", "../execution/main.py")} 
FLAG_FILE={os.path.join(self.work_dir, f"run_{run_id}", "config.cfg")} 
        
{executable} $MAIN_FILE --flagfile=$FLAG_FILE
"""
        single_run_path = os.path.join(self.work_dir, f"run_{run_id}", "single_run.sh")
        with open(single_run_path, "w") as f:
            f.write(file)
        invoke.run(f"chmod 700 {single_run_path}")

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

    def submit_process(self, run_id, trial):
        logging.info(f"Start Trial {trial.id}, with parameters {trial.parameters}")

        work_dir = os.path.join(self.work_dir, f"run_{run_id}")

        # write command
        sh_run_file = os.path.join(work_dir, "single_run.sh")

        if self.executable == "local":
            command = ["sh"]
        else:
            run_port = 27100 + run_id
            self.command = [
                "srun",
                f"--export=ALL,RUN_PORT={run_port}",
                "--nodes=1",
                f"--ntasks=1",
                f"--gres=gpu:{self.resource_config.host_specific.get('gpus-per-task', 1)}",
                f"--cpus-per-task={self.resource_config.host_specific.get('cpus-per-task', 1)}",
            ]  # , "--gpus-per-task=2", "--cpus-per-task=8"]

        command = self.command + [sh_run_file]
        srun_command_file = os.path.join(work_dir, "srun_command.sh")
        with open(srun_command_file, "w") as f:
            f.write(" ".join(command))
        invoke.run(f"chmod 700 {srun_command_file}")

        # open process
        f = open(os.path.join(work_dir, 'stdout.out'), 'w')
        process = subprocess.Popen(command, stderr=f, stdout=f)

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
            with open(os.path.join(work_dir, "test_metrics.json"), "r") as f:
                metrics = json.load(f)
                if self.config.objective not in metrics:
                    raise RuntimeError(
                        f"You have to write a file called test_metrics.json which holds a key {self.config.objective}"
                    )
                result = metrics.get(self.config.objective)

            logging.info(f"Finalize trial {process_dict['trial'].id}, {self.config.objective}: {result}")

            self.study.add_observation(process_dict["trial"], iteration=1, objective=result, context=metrics)
        else:
            self.study.add_observation(process_dict["trial"], iteration=1, objective=0, context={"error": returncode})

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

            run_id = self.generate_run_id()
            self.write_job_config(run_id=run_id, trial=trial)
            self.write_trial_run_file(run_id=run_id)
            self.submit_process(run_id=run_id, trial=trial)

        logging.info("Started all trials")


def run_hyp_opt(executable: str, run_file: str, work_dir: str, data_dir: str, config_file: str):
    logging.debug(f"Start hyperparameter optimization with")
    logging.debug(f"executable: {executable}")
    logging.debug(f"train_file: {run_file}")
    logging.debug(f"work_dir: {work_dir}")
    logging.debug(f"data_dir: {data_dir}")
    logging.debug(f"config_file: {config_file}")

    config = RunConfig(config_file)

    parameter_names = [parameter.name for parameter in config.parameters]
    with open(os.path.join(work_dir, "parameters.json"), "w") as f:
        json.dump(parameter_names, f)

    # TODO: load json or have dict
    # folder_config = FolderConfig(experiment_config=config_file, remote_proj_dir=work_dir)
    resource_config = ResourceConfig(experiment_config=config_file)

    # initialize Study
    study_dir = os.path.join(work_dir, "study")
    os.makedirs(study_dir, exist_ok=True)
    study = Study(
        parameters=config.parameters,
        algorithm=config.algorithm,
        lower_is_better=False,
        disable_dashboard=True,
        output_dir=study_dir
    )
    process_manager = JobScheduler(
        study=study,
        config=config,
        executable=executable,
        work_dir=work_dir,
        data_dir=data_dir,
        resource_config=resource_config
    )
    process_manager.loop_hyperparams()

    process_manager.wait_until_all_finished()

    log_best_results(study=process_manager.study, config=config)
