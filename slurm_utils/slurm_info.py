import re

import pandas as pd

from slurm_utils.connection import RemoteConnector


class SLURMInfo:
    def __init__(self, hostname: str):
        self.connection = RemoteConnector(hostname=hostname)

    def squeue(self):
        stout = self.connection.execute(
            f"squeue --format='%.18i %.9P %.20j %.8u %.15T %.15M %.15l %.15D %.30R %C %m %b' "
        )
        df = []
        for row in stout.split("\n"):
            df.append(re.sub(' +', ' ', row.strip()).split(" "))
        df = pd.DataFrame(df[1:], columns=df[0])
        return df

    def available_resources(self):
        stout = self.connection.execute("sinfo -o '%G %m %e %C'").split("\n")
        df = [row.split(" ") for row in stout]
        df = pd.DataFrame(df[1:], columns=df[0])

        return df

    def get_job_info(self, job_id: int):

        df = self.squeue()
        df = df[df["JOBID"] == str(job_id)]
        if len(df) > 0:
            return df.iloc[0].to_dict()
        else:
            return {
                "JOBID": job_id,
                "STATUS": "FINISHED"
            }

    def get_status(self, job_id: int):
        return self.get_job_info(job_id).get("STATUS")

    def scancel(self, job_id: int = None):

        self.connection.execute(f"scancel {job_id}")

        return self.squeue()
