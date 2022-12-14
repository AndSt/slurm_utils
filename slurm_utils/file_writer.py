import os
import sys

import invoke

from slurm_utils.config.folder import FolderConfig
from slurm_utils.config.resources import ResourceConfig


class FileWriter:
    def __init__(self, folder_config: FolderConfig, resource_config: ResourceConfig):
        self.folder_config = folder_config
        self.resource_config = resource_config

        self.storage_env_variable = "SU_STORAGE"

    def write_sbatch_file(self):
        sbatch_settings = self.resource_config.get_sbatch_setup_string()

        sbatch_file = sbatch_settings + f"""
#SBATCH --output={self.folder_config.remote_experiment_dir}/output.out      ## sysout and syserr merged together

# project setup
PROJ_NAME={self.folder_config.proj_name}
PROJ_DIR={self.folder_config.remote_proj_dir}
EXECUTABLE={sys.executable}
RUN_FILE={self.folder_config.remote_script_dir}/main.py

# Prepare environment
source ${self.storage_env_variable}/server_setup/init_slurm.sh
            
# experiment variables
EXPERIMENT={self.folder_config.experiment_name}
DATA_DIR={self.folder_config.remote_data_dir}
WORK_DIR={self.folder_config.remote_experiment_dir}
CONFIG_FILE={self.folder_config.remote_script_dir}/config.json

pip freeze > {self.folder_config.remote_experiment_dir}/freezed_requirements.txt

python {self.folder_config.remote_script_dir}/optimize.py \\
    --executable srun \\
    --run_file $RUN_FILE \\
    --data_dir $DATA_DIR \\
    --work_dir $WORK_DIR \\
    --config_file $CONFIG_FILE
"""
        with open(os.path.join(self.folder_config.local_script_dir, "run.sbatch"), "w") as f:
            f.write(sbatch_file)

    def write_port_finder_file(self):
        file = """ #!/bin/bash
  
CHECK="do while"

while [[ ! -z $CHECK ]]; do
    PORT=$(( ( RANDOM % 1000 )  + 27000 ))
    CHECK=$(netstat -ap | grep $PORT)
done

echo $PORT 
"""
        port_finder_file = os.path.join(self.folder_config.local_script_dir, "port_finder.sh")
        with open(port_finder_file, "w") as f:
            f.write(file)
        invoke.run(f"chmod 700 {port_finder_file}")

    def write_test_file(self):
        sh_file = f"""#!/usr/bin/env bash
        
# project setup
PROJ_NAME={self.folder_config.proj_name}
PROJ_DIR={self.folder_config.local_proj_dir}
EXECUTABLE={sys.executable}
RUN_FILE={self.folder_config.local_script_dir}/main.py

# Prepare environment

export WORKON_HOME="/Users/andst/.cache/virtual-envs"
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
source /usr/local/bin/virtualenvwrapper.sh

workon $PROJ_NAME

# experiment variables
EXPERIMENT={self.folder_config.experiment_name}
DATA_DIR={self.folder_config.local_data_dir}
WORK_DIR={self.folder_config.local_experiment_dir}
CONFIG_FILE={self.folder_config.local_script_dir}/config.json

pip freeze > {self.folder_config.local_experiment_dir}/freezed_requirements.txt

python {self.folder_config.local_script_dir}/optimize.py \
    --executable local \
    --run_file $RUN_FILE \
    --data_dir $DATA_DIR \
    --work_dir $WORK_DIR \
    --config_file $CONFIG_FILE
"""
        test_file = os.path.join(self.folder_config.local_script_dir, "test.sh")
        with open(test_file, "w") as f:
            f.write(sh_file)
        invoke.run(f"chmod 700 {test_file}")

    def write_optimization_file(self):
        py_file = """import argparse

from slurm_utils.server.main import run_hyp_opt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--executable', help='Executable of the current project.')
    parser.add_argument('--run_file', help='File that starts the training procedure.')
    parser.add_argument('--data_dir', help='Data directory.')
    parser.add_argument('--work_dir', help='Working directory.')
    parser.add_argument('--config_file', help='Working directory.', default='')

    args = parser.parse_args()

    run_hyp_opt(
        executable=args.executable,
        run_file=args.run_file,
        work_dir=args.work_dir,
        data_dir=args.data_dir,
        config_file=args.config_file
    )
"""
        with open(os.path.join(self.folder_config.local_script_dir, "optimize.py"), "w") as f:
            f.write(py_file)

    def write_main_file(self):
        run_file = f"""from absl import app

from {self.folder_config.proj_name}.{self.folder_config.run_file} import main


if __name__ == '__main__':
    app.run(main)
"""
        with open(os.path.join(self.folder_config.local_script_dir, "main.py"), "w") as f:
            f.write(run_file)
