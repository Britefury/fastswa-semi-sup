from datetime import datetime
from collections import defaultdict
import threading
import time
import logging
import os
import torch

from pandas import DataFrame
from collections import defaultdict


class TrainLog:
    """Saves training logs in Pandas msgpacks"""

    INCREMENTAL_UPDATE_TIME = 300

    def __init__(self, directory, name):
        self.log_file_path = "{}/{}.msgpack".format(directory, name)
        self._log = defaultdict(dict)
        self._log_lock = threading.RLock()
        self._last_update_time = time.time() - self.INCREMENTAL_UPDATE_TIME

    def record_single(self, step, column, value):
        self._record(step, {column: value})

    def record(self, step, col_val_dict):
        self._record(step, col_val_dict)

    def save(self):
        df = self._as_dataframe()
        df.to_msgpack(self.log_file_path, compress='zlib')

    def _record(self, step, col_val_dict):
        fixed_col_val_dict = dict()
        for key, val in col_val_dict.items():
            if isinstance(val, torch.Tensor):
                if val.dtype == torch.int32 or val.dtype == torch.int64:
                    val = int(val)
                else:
                    val = float(val)
            fixed_col_val_dict[key] = val
        with self._log_lock:
            self._log[step].update(fixed_col_val_dict)
            if time.time() - self._last_update_time >= self.INCREMENTAL_UPDATE_TIME:
                self._last_update_time = time.time()
                self.save()

    def _as_dataframe(self):
        with self._log_lock:
            return DataFrame.from_dict(self._log, orient='index')


class RunContext:
    """Creates directories and files for the run"""

    def __init__(self, runner_file, run_idx):
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        runner_name = os.path.basename(runner_file).split(".")[0]
        self.result_dir = "{root}/{runner_name}/{date:%Y-%m-%d_%H-%M-%S}/{run_idx}".format(
            root='results',
            runner_name=runner_name,
            date=datetime.now(),
            run_idx=run_idx
        )
        self.transient_dir = self.result_dir + "/transient"
        os.makedirs(self.result_dir)
        os.makedirs(self.transient_dir)

    def create_train_log(self, name):
        return TrainLog(self.result_dir, name)
