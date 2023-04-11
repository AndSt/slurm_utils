# import os
# import argparse
# import logging
#
# from slurm_utils.connection import SLURMConnector
#
# if __name__ == '__main__':
#
#     logging.getLogger().setLevel(logging.ERROR)
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--hostname', default="vda-dgx", help="Where to connect to")
#     parser.add_argument('--config', help='Location of config file.')
#
#     args = parser.parse_args()
#
#     shell = SLURMConnector(
#         hostname=args.hostname,
#         ssh_config_file=os.path.join(os.path.expanduser("~"), ".ssh", "config")
#     )
#     shell.connect()
#     squeue_df = shell.squeue()
#     print(squeue_df)
#     shell.close()
