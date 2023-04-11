import os
import logging

import invoke
import click

from slurm_utils.convenience.log import init_logging


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)


def get_setup_py_string(name, python_version):
    setup_py_string = f"""from typing import Dict

from setuptools import find_packages, setup

# version.py defines the VERSION and VERSION_SHORT variables.
# We use exec here so we don't import snorkel.
VERSION: Dict[str, str] = {{}}
with open("{name}/version.py", "r") as version_file:
    exec(version_file.read(), VERSION)

with open('requirements.txt') as f:
    requirements = f.readlines()

test_requirements = ['pytest']

# Use README.md as the long_description for the package
with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name="{name}",
    version=VERSION["__version__"],
    description="This repo is named {name} and was created with slurm_utils.",
    long_description_content_type="text/markdown",
    long_description=long_description,
    author_email="andreas.stephan@univie.ac.at",
    license="Apache License 2.0",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: {python_version}",
    ],
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require={{'test': test_requirements}}
)
"""
    return setup_py_string


def get_main_file_string(name):
    main_file_string = """import os
import random
import logging

import torch

from absl import app

from slurm_utils.convenience.log import init_logging
from slurm_utils.convenience.flags import flags, FLAGS
from slurm_utils.convenience.save import save_scheduler_info


flags.DEFINE_integer("train_parameter", default=1, help="Example of a parameter used for training")


def main(_):
    init_logging(logging.INFO)

    # data loading test
    logging.info("Load data.")

    # Place where training would happen
    logging.info("Here happens training.")
    logging.info(f"Value of training parameter: {{FLAGS.train_parameter}}")

    logging.info(f"GPU available: {{torch.cuda.is_available()}}")
    logging.info(f"num_gpus: {{torch.cuda.device_count()}}")

    # save train metric
    acc = random.random()
    f1 = random.random()
    logging.info("Save metrics.")

    save_scheduler_info(objective=acc, additional_info={"macro avg": {"f1-score": f1}})


if __name__ == '__main__':
    app.run(main)
"""
    return main_file_string


@click.command()
@click.argument("name")
@click.option("--python_version", "python_version", default="3.8", help="Python Version.")
def create_proj(name, python_version):
    init_logging(logging.INFO)

    su_storage = os.environ.get("SU_STORAGE")
    proj_dir = os.path.join(su_storage, "projects", name)
    logging.info(f"Create project directories under {proj_dir}")
    # create folder
    os.makedirs(proj_dir, exist_ok=True)
    os.makedirs(os.path.join(proj_dir, name), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "notebooks"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "experiments"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "scripts", "remote"), exist_ok=True)

    # write initial files of README; .gitignore; setup.py; requirements.txt; version.py; __init__.py
    logging.info("Write initial files.")
    write_file(os.path.join(proj_dir, "README.md"), "# Notebooks")
    write_file(os.path.join(proj_dir, ".gitignore"), "*.pyc")
    write_file(os.path.join(proj_dir, "requirements.txt"), "slurm_utils")
    write_file(os.path.join(proj_dir, "setup.py"), get_setup_py_string(name, python_version))
    write_file(os.path.join(proj_dir, name, "__init__.py"), "")
    write_file(os.path.join(proj_dir, name, "version.py"), "__version__ = \"0.0.1\"")
    write_file(os.path.join(proj_dir, name, "main.py"), get_main_file_string(name))

    # create virtual environment
    logging.info("Create virtual environment.")
    logging.info(os.getenv("WORKON_HOME"))
    invoke.run(
        f"source /usr/local/bin/virtualenvwrapper.sh;"
        f"mkvirtualenv -p python{python_version} {name};"
        f"workon {name};"
        f"cd {proj_dir};"
        "pip install -r requirements.txt;"
        "pip install -e .;"
        "deactivate;"
    )

    # initialize git
    logging.info("Initialize git.")
    invoke.run(f"cd {proj_dir}; git init; git add README.md; git add {name}; git commit -m 'Initial commit.'")
