import logging
import os


def write_run_output_stream(output, work_dir: str):
    if output.returncode:
        logging.error(output.returncode)
        logging.error(output.stderr) # TODO: currently it's tought to identify where error happened
        with open(os.path.join(work_dir, "error.txt"), "w") as f:
            f.write(output.stderr)

    # use decode function to convert to string
    output_text = output.stderr.decode('utf-8')
    logging.debug(f"Output: {output_text}")
    with open(os.path.join(work_dir, "stdout.txt"), "w") as f:
        f.write(output_text)


def log_best_results(study, config):
    best = study.get_best_result()
    logging.info(f"Best trial run - ID: {best.get('Trial-ID')}, {config.metric}: {best.get('Objective')} ")
    logging.info(f"Find all related data at {best.get('work_dir')}")


def summarize():
    # TODO: put together a directory, holding subset of important information which is then suitable for download
    pass
