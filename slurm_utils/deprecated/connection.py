import os
from paramiko import SSHConfig, SSHClient, AutoAddPolicy
import re

from stat import S_ISDIR

import logging

import pandas as pd


class SLURMConnector:

    def __init__(
            self,
            hostname=None,
            ssh_config_file=None
    ):
        self.hostname = hostname
        if ssh_config_file is None:
            self.ssh_config_file = os.path.join(os.path.expanduser("~"), ".ssh", "config")
        else:
            self.ssh_config_file = ssh_config_file

        s = SSHConfig()
        try:
            with open(self.ssh_config_file) as f:
                s.parse(f)
            info = s.lookup(hostname)
            print(info)

            self.hostname = info.get("hostname")
            self.username = info.get("user")
            self.port = info.get("port", 22)
            self.key_filename = info.get("identityfile")[0]

            self.ssh = SSHClient()
            self.ssh.set_missing_host_key_policy(AutoAddPolicy())

            self.stdin = None
            self.stdout = None
            self.sftp = None
        except:
            print("No connection possible")

    def is_connected(self):
        try:
            transport = self.ssh.get_transport()
            if transport:
                transport.send_ignore()
            else:
                return False
            return True
        except EOFError as e:
            return False

    def connect(self):
        if self.is_connected():
            return
        print("oi")
        self.ssh.connect(
            hostname=self.hostname,
            username=self.username,
            key_filename=self.key_filename,
            port=self.port
        )
        print("oi")

        channel = self.ssh.invoke_shell()
        print("oi")
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')
        print("oi")
        # self.sftp = self.ssh.open_sftp()
        print("oi")

    def __del__(self):
        self.close()

    def close(self):

        if self.sftp is not None:
            self.sftp.close()
        self.ssh.close()
        self.stdin = None
        self.stdout = None

    def execute(self, cmd, check_err: bool = False):
        """

        :param cmd: the command to be executed on the remote computer
        :examples:  execute('ls')
                    execute('finger')
                    execute('cd folder_name')
        """
        if not self.is_connected():
            raise RuntimeError("You first have to connect to a DGX. Call exp.connect() to do so.")

        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        finish = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        shin = self.stdin
        self.stdin.flush()

        shout = []
        sherr = []

        for line in self.stdout:
            if str(line).startswith(cmd) or str(line).startswith(echo_cmd):  # testets
                # up for now filled with shell junk from stdin
                shout = []
            elif str(line).startswith(finish):
                # our finish command ends with the exit status
                exit_status = int(str(line).rsplit(maxsplit=1)[1])
                if exit_status:
                    # stderr is combined with stdout.
                    # thus, swap sherr with shout in a case of failure.
                    sherr = shout
                    shout = []
                break
            else:
                # get rid of 'coloring and formatting' special characters
                shout.append(
                    re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).replace('\b', '').replace('\r', '')
                )

        # first and last lines of shout/sherr contain a prompt
        # TODO here is some bug: Sometimes the first line of multiline response gets eaten
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        shout = [s.replace("\n", "") for s in shout]
        sherr = [s.replace("\n", "") for s in sherr]

        if check_err:
            if len(sherr) > 0:
                error = "\n".join(sherr)
                logging.error(f"Error occured during command: {cmd}")
                logging.error("\n".join(error))
                raise RuntimeError(error)
        return shin, shout, sherr

    def squeue(self):
        _, stout, sterr = self.execute(
            f"squeue --format='%.18i %.9P %.20j %.8u %.15T %.15M %.15l %.15D %.30R %C %m %b' ", check_err=True
        )
        df = []
        for row in stout:
            df.append(re.sub(' +', ' ', row.strip()).split(" "))
        df = pd.DataFrame(df[5:], columns=df[4])
        return df

    def available_resources(self):
        """TODO: FIX FOR memory, CPU, GPU"""
        _, stout, sterr = self.execute("sinfo -o '%G %m %e %C'")

        gpu, total_mem, free_mem, cpu = stout[1].split(" ")
        allocated_cpu, idle_cpu, other_cpu, total_cpu = cpu.split("/")

        df = []
        df.append(["memory", total_mem, free_mem])
        df.append(["cpu", total_cpu, idle_cpu])
        df.append(["gpu", gpu, ""])

        df = pd.DataFrame(df, columns=["Device", "Total", "Free"])

        return df

    def upload_file(self, local_file, remote_file):
        if self.sftp is None:
            logging.warning("Please connect() before uploading a file")

        logging.debug(f"Upload file {local_file} to {remote_file}")
        self.sftp.put(localpath=local_file, remotepath=remote_file, confirm=False)

    def download(self, remote_file, local_file, skip_existing: bool = False):
        if self.sftp is None:
            logging.warning("Please connect() before uploading a file")

        if skip_existing:
            if os.path.isfile(local_file):
                return

        logging.debug(f"Download file {remote_file} to {local_file}")
        try:
            local_dir = os.path.dirname(local_file)
            os.makedirs(local_dir, exist_ok=True)
            self.sftp.get(localpath=local_file, remotepath=remote_file)
        except FileNotFoundError as e:
            logging.error("The remote file does not exist (yet?)")

    def download_folder(self, remote_path, local_path, filter_fn=None, skip_existing: bool = False):
        # filter_fn will enable filtering
        if self.sftp is None:
            logging.warning("Please connect() before uploading a file")

        item_list = self.sftp.listdir(remote_path)

        for item in item_list:
            remote_item, local_item = os.path.join(remote_path, item), os.path.join(local_path, item)

            is_dir = S_ISDIR(self.sftp.stat(remote_item).st_mode)
            if is_dir:
                self.download_folder(remote_item, local_item, filter_fn=filter_fn, skip_existing=skip_existing)
            else:
                self.download(remote_item, local_item, skip_existing=skip_existing)

    def download_extension(self, remote_path, local_path, extension: str = "", skip_existing: bool = False):
        if self.sftp is None:
            logging.warning("Please connect() before uploading a file")

        item_list = self.sftp.listdir(remote_path)

        for item in item_list:
            remote_item, local_item = os.path.join(remote_path, item), os.path.join(local_path, item)

            is_dir = S_ISDIR(self.sftp.stat(remote_item).st_mode)
            if is_dir:
                self.download_extension(remote_item, local_item, extension=extension, skip_existing=skip_existing)
            elif item.endswith(extension):
                self.download(remote_item, local_item, skip_existing=skip_existing)

    def download_test_metrics(self, remote_path, local_path, skip_existing: bool = False):
        if self.sftp is None:
            logging.warning("Please connect() before uploading a file")

        item_list = self.sftp.listdir(remote_path)
        for item in item_list:
            remote_item, local_item = os.path.join(remote_path, item), os.path.join(local_path, item)

            is_dir = S_ISDIR(self.sftp.stat(remote_item).st_mode)
            if is_dir:
                print(item)
                if item.startswith("run_"):
                    self.download(
                        os.path.join(remote_item, "config.json"),
                        os.path.join(local_item, "config.json"),
                        skip_existing=skip_existing
                    )
                    self.download(
                        os.path.join(remote_item, "test_metrics.json"),
                        os.path.join(local_item, "test_metrics.json"),
                        skip_existing=skip_existing
                    )
                if item.startswith("scripts"):
                    self.download(
                        os.path.join(remote_item, "config.json"),
                        os.path.join(local_item, "config.json"),
                        skip_existing=skip_existing
                    )
                else:
                    self.download_test_metrics(remote_item, local_item, skip_existing=skip_existing)



