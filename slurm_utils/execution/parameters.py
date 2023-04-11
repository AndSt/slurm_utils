from typing import Dict

from sherpa import Parameter
from sherpa.algorithms import GridSearch, GPyOpt


class RunConfig:
    def __init__(self, experiment_config: Dict):

        run_settings = experiment_config.get("run_settings", {})

        self.objective = run_settings.get("objective")

        self.algorithm_name = run_settings.get("hyperparam_algorithm", "grid")
        self.algorithm_params = run_settings.get("hyperparameter_params")

        if self.algorithm_name == "bayesian":
            self.algorithm = GPyOpt(
                max_concurrent=1, model_type='GP_MCMC', acquisition_type='EI_MCMC', max_num_trials=10
            )
        else:
            self.algorithm = GridSearch(num_grid_points=2)

        parameters = experiment_config.get("parameters", [])
        if isinstance(parameters, list):
            self.parameters = [Parameter.from_dict(p) for p in parameters]
        elif isinstance(parameters, dict):
            self.parameters = Parameter.grid(parameters)
