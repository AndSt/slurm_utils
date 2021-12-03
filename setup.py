from typing import Dict
import os

from setuptools import find_packages, setup

project_name = "slurm_utils"

VERSION: Dict[str, str] = {}
with open(os.path.join(project_name, "version.py"), "r") as version_file:
    exec(version_file.read(), VERSION)

with open('requirements.txt') as f:
    requirements = f.readlines()

test_requirements = ['pytest']

# Use README.md as the long_description for the package
with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name="slurm-utils",
    version=VERSION["__version__"],
    description="Code to work with a SLURM cluster. Heavily biased towards our setting.",
    long_description_content_type="text/markdown",
    long_description=long_description,
    author_email="andreas.stephan@univie.ac.at",
    license="Apache License 2.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require={'test': test_requirements}
)
