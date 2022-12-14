import argparse

from slurm_utils.deprecated.readers import load_config
from slurm_utils.experiment_manager import ExperimentManager


def setup_exp(config_path: str):
    config = load_config(config_path, None)
    print(config)

    proj_name = config.get("project_name")
    proj_dir = f"/Users/andst/projects/{proj_name}"

    exp = ExperimentManager(
        local_proj_dir=proj_dir,  # local proj dir
        experiment_config=config  # os.path.join(proj_dir, "notebooks", "data", "test_data", "empty_train_config.json")
    )

    exp.prepare_local_experiment(clean_existing=True)
    return exp


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default="slurm", help="Whether to run 'local' or on 'slurm'")
    parser.add_argument('--config', help='Location of config file.')
    parser.add_argument('--upload', default=True, help="Whether to upload code")

    args = parser.parse_args()

    exp = setup_exp(args.config)
    if args.mode == "local":
        out = exp.run_locally()
    elif args.mode == "slurm":

        upload = True
        if args.upload in ["false", "False"]:
            upload = False
        exp.prepare_remote_experiment(clean_existing=True, upload_code=upload)
        out = exp.run_remote(upload_code=False)
    exp.close()
