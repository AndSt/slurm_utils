from typing import Dict, Union
import json


class ResourceConfig:
    def __init__(self, hostname: str = None, experiment_config: Union[str, Dict] = None):

        # set and load experiment config file
        if isinstance(experiment_config, str):
            with open(experiment_config, "r") as f:
                experiment_config = json.load(f)

        server_settings = experiment_config.get("server_settings", {})

        if hostname is None or hostname == "":
            self.hostname = server_settings.get("hostname")
        else:
            self.hostname = hostname

        self.experiment_config = experiment_config

        self.proj_name = self.experiment_config.get("project_name")
        self.experiment_name = self.experiment_config.get("experiment_name")

        # SLURM settings
        self.sbatch = server_settings.get("sbatch_required")
        self.host_specific = server_settings.get("host_specific").get(self.hostname, {}).copy()

        self.nodes = self.host_specific.get("nodes", self.sbatch.get("nodes", 1))
        self.ntasks_per_node = self.host_specific.get("n_tasks_per_node", self.sbatch.get("n_tasks_per_node", 1))
        self.cpus_per_task = self.host_specific.get("cpus-per-task", self.sbatch.get("cpus-per-task", 1))
        self.gres = self.host_specific.get("gres", self.sbatch.get("gres", 1))

        self.ntasks = self.nodes * self.ntasks_per_node

        self.gpus_per_node = int(self.gres.replace("gpu:", ""))
        self.gpus_per_task = self.gpus_per_node // self.ntasks_per_node

        for key in ["nodes", "n_tasks_per_node", "cpus-per-task", "gres"]:
            if key in self.host_specific:
                self.host_specific.pop(key)

    def get_sbatch_setup_string(self):
        setup = f"""#!/bin/bash 

#SBATCH --nodes={self.nodes}                         ## always 1 (we have just 1 server)
#SBATCH --job-name={self.proj_name}_{self.experiment_name}        ## name you give to your job

#SBATCH --ntasks-per-node={self.ntasks_per_node} # number of tasks per node
#SBATCH --cpus-per-task={self.cpus_per_task}    ## number of cores for the job - max 80
#SBATCH --gres={self.gres}    ## number of GPU's per node

"""
        for key, val in self.host_specific.items():
            setup += f"#SBATCH --{key}={val} \n"
        return setup
