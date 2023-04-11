from absl import flags

FLAGS = flags.FLAGS

# data flags
flags.DEFINE_string(
    "data_dir", default="",
    help="Data directory. Here, data is loaded for computation."
)

flags.DEFINE_string(
    "work_dir", default="",
    help="Working directory. Here, data is saved."
)

flags.DEFINE_string(
    "objective", default=None,
    help="Working directory. Here, data is saved."
)

flags.DEFINE_bool(
    "debug", default=False,
    help="Whether this is a debugging run or not."
)