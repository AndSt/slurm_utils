import json

from sherpa import Parameter
from sherpa.algorithms import GridSearch, GPyOpt


class RunConfig:
    def __init__(self, config_file_path: str):
        self.path = config_file_path

        if config_file_path.endswith(".json"):
            with open(self.path, "r") as f:
                content = json.load(f)
        # elif config_file_path.endswith(".yaml"):
        #     with open(self.path, "r") as f:
        #         content = yaml.load(f)
        else:
            raise RuntimeError("Provide a valid config file.")

        run_settings = content.get("run_settings", {})

        self.objective = run_settings.get("objective")
        self.capture_output = not run_settings.get("print_training_output", False)

        self.algorithm_name = run_settings.get("hyperparam_algorithm", "grid")
        self.algorithm_params = run_settings.get("hyperparameter_params")

        if self.algorithm_name == "bayesian":
            self.algorithm = GPyOpt(
                max_concurrent=1, model_type='GP_MCMC', acquisition_type='EI_MCMC', max_num_trials=10
            )
        else:
            self.algorithm = GridSearch(num_grid_points=2)

        self.parameters = [Parameter.from_dict(p) for p in content.get("parameters", [])]