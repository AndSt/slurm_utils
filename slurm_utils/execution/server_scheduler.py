import os

from slurm_utils.execution.job_scheduler import JobScheduler


class SlurmJobScheduler(JobScheduler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write_system_info(self):
        file = f"""

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

"""
        return file

    def write_trial_run_file(self, run_id):

        if self.resource_config.gpus_per_task <= 1:
            executable = "python"
        else:
            # executable = "python"
            executable = f"accelerate launch --main_process_port $RUN_PORT"
            # executable = f"accelerate launch --mixed_precision fp16 --multi_gpu --num_machines 1 --main_process_port $RUN_PORT"

        file = f"""#!/bin/bash

# environment setup
PROJ_NAME={self.resource_config.proj_name}

# Prepare environment
source $SU_STORAGE/server_setup/init_slurm.sh
"""
        file += self.write_system_info()
        file += self.write_run_command(run_id, executable)
        self.save_single_run_file(run_id, file)

    def create_run_command(self, run_id):

        work_dir = os.path.join(self.work_dir, f"run_{run_id}")
        run_port = 27100 + run_id

        execution_sh_command = [
            "srun",
            f"--export=ALL,RUN_PORT={run_port}",
            "--nodes=1",
            f"--ntasks=1",
            f"--gres=gpu:{self.resource_config.gpus_per_task}",
            f"--cpus-per-task={self.resource_config.cpus_per_task}",
            os.path.join(work_dir, "single_run.sh")
        ]
        return execution_sh_command
