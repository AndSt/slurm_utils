import os

from slurm_utils.execution.job_scheduler import JobScheduler


class LocalJobScheduler(JobScheduler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.max_processes = 1

    def write_trial_run_file(self, run_id):
        executable = "python"
        file = f"""#!/bin/bash

# environment setup
PROJ_NAME={self.resource_config.proj_name}

# Prepare environment
export WORKON_HOME="${{XDG_CACHE_HOME}}/virtual-envs"
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
source /usr/local/bin/virtualenvwrapper.sh

# Prepare environment
source $SU_STORAGE/server_setup/init_slurm.sh
"""
# workon $PROJ_NAME
# """

        file += self.write_run_command(run_id, executable)
        self.save_single_run_file(run_id, file)

    def create_run_command(self, run_id):
        work_dir = os.path.join(self.work_dir, f"run_{run_id}")
        execution_sh_command = ["sh", os.path.join(work_dir, "single_run.sh")]
        return execution_sh_command
