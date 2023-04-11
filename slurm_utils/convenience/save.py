import os
import json
from slurm_utils.convenience.flags import FLAGS


def save_scheduler_info(objective, additional_info=None):
    save_dict = {FLAGS.objective: objective}
    if additional_info is not None:
        save_dict.update({"additional_information": additional_info})

    with open(os.path.join(FLAGS.work_dir, "test_metrics.json"), "w") as f:
        json.dump(save_dict, f)
