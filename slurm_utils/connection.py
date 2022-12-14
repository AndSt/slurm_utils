import os
from fabric import Connection


class RemoteConnector:
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.ssh_config_file = os.path.join(os.path.expanduser("~"), ".ssh", "config")

        self.connection = Connection(self.hostname)
        self.folder_config = None

    def close(self):
        self.connection.close()

    def execute(self, cmd: str):
        response = self.connection.run(cmd)
        return response.stdout[0: -1]

    def get_storage_dir(self):
        return self.execute("echo $SU_STORAGE")

    def upload(self, local_path: str, remote_path: str):
        self.connection.put(local_path, remote_path)
