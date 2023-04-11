import os
import stat

from slurm_utils.config.folder import FolderConfig
from slurm_utils.config.resources import ResourceConfig


class FileWriter:
    def __init__(self, folder_config: FolderConfig, **kwargs):
        self.folder_config = folder_config
        self.storage_env_variable = "SU_STORAGE"
        self.executable = "local"

    def write_execution_file(self):
        raise NotImplementedError()

    def get_project_string(self):
        project_string = f"""
# project setup
PROJ_NAME={self.folder_config.proj_name}
PROJ_DIR={self.folder_config.proj_dir}
EXECUTABLE={self.executable}
RUN_FILE={self.folder_config.script_dir}/main.py
"""
        return project_string

    def get_scheduling_string(self):
        scheduling_string = f"""
# experiment variables
EXPERIMENT={self.folder_config.experiment_name}
DATA_DIR={self.folder_config.data_dir}
WORK_DIR={self.folder_config.experiment_dir}
CONFIG_FILE={self.folder_config.script_dir}/config.json

pip freeze > {self.folder_config.experiment_dir}/freezed_requirements.txt

schedule  --executable $EXECUTABLE \\
    --run_file $RUN_FILE \\
    --data_dir $DATA_DIR \\
    --work_dir $WORK_DIR \\
    --config_file $CONFIG_FILE
"""
        return scheduling_string

    def write_pyhton_main_file(self):
        run_file = f"""from absl import app

from {self.folder_config.proj_name}.{self.folder_config.run_file} import main


if __name__ == '__main__':
    app.run(main)
"""
        with open(os.path.join(self.folder_config.script_dir, "main.py"), "w") as f:
            f.write(run_file)


class ServerFileWriter(FileWriter):
    def __init__(self, folder_config: FolderConfig, resource_config: ResourceConfig, **kwargs):
        super().__init__(folder_config, **kwargs)
        self.resource_config = resource_config
        self.executable = "srun"

    def get_sbatch_string(self):
        sbatch_string = f"""{self.resource_config.get_sbatch_setup_string()}
#SBATCH --output={self.folder_config.experiment_dir}/output.out      ## sysout and syserr merged together
"""
        return sbatch_string

    def write_execution_file(self):
        sbatch_file = f"""{self.get_sbatch_string()}

module load CUDA
module load NCCL
module load cuDNN       
        
{self.get_project_string()}

# Prepare environment
source ${self.storage_env_variable}/server_setup/init_slurm.sh

{self.get_scheduling_string()}
"""

        with open(os.path.join(self.folder_config.script_dir, "run.sbatch"), "w") as f:
            f.write(sbatch_file)


class LocalFileWriter(FileWriter):

    def write_execution_file(self):
        sh_file = f"""#!/usr/bin/env bash
{self.get_project_string()}

# Prepare environment
export WORKON_HOME="/Users/andst/.cache/virtual-envs"
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
source /usr/local/bin/virtualenvwrapper.sh
workon $PROJ_NAME

{self.get_scheduling_string()}
"""

        test_file = os.path.join(self.folder_config.script_dir, "test.sh")
        with open(test_file, "w") as f:
            f.write(sh_file)
        os.chmod(test_file, stat.S_IRWXU)
