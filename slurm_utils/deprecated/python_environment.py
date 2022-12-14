import logging


class PythonEnvironment:
    def __init__(self, proj_name: str, type: str = "conda", shell=None):
        self.proj_name = proj_name
        self.type = type  # possible: conda / virtualenv
        self.shell = shell

    def create_remote_venv(self, env_name, python_version: str = "3.8"):
        if env_name is None:
            env_name = self.proj_name

        if self.type == "conda":
            self.create_conda_venv(env_name, python_version)
        elif self.type == "venvwrapper":
            self.create_venvwrapper_venv(env_name, python_version)

    def create_conda_venv(self, env_name: str = None, python_version: str = "3.8"):
        raise RuntimeError("Conda environments have to be created manually")

    def create_venvwrapper_venv(self, env_name: str = None, python_version: str = "3.8"):
        _, _, sterr = self.shell.execute("workon")
        if self.proj_name in sterr:
            logging.info(f"Env '{self.proj_name}' already installed")
            return

        logging.info(f"Create remote environment: {env_name}")
        _, stout, _ = self.shell.execute(f"mkvirtualenv -p python{python_version} {env_name}", check_err=True)
        logging.info("\n".join(stout))
        _, stout, _ = self.shell.execute("deactivate", check_err=True)

    def activate_environment(self, env_name: str = None):
        if env_name is None:
            env_name = self.proj_name

        if self.type == "conda":
            self.activate_conda_environment(env_name)
        elif self.type == "venvwrapper":
            self.activate_venvwrapper_environment(env_name)

    def activate_conda_environment(self, env_name: str):
        self.shell.execute(f"conda activate {env_name}", check_err=True)

    def activate_venvwrapper_environment(self, env_name: str):
        self.shell.execute(f"workon {env_name}", check_err=True)

    def pip_install(self, pckg_name: str, uninstall_current: bool = True):
        logging.info(f"Install uploaded package {self.proj_name} remotely")

        if pckg_name is None:
            pckg_name = self.proj_name

        self.activate_environment()

        if uninstall_current:
            _, stout, _ = self.shell.execute(f"pip uninstall -y {pckg_name}", check_err=True)
            logging.debug(stout)
        _, stout, _ = self.shell.execute(f"pip install {pckg_name}", check_err=True)
        logging.debug(stout)
