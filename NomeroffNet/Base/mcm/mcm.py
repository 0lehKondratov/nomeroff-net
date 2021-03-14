import os
import urllib.request
from tqdm import tqdm
import pathlib
from .latest import latest_models

# sys var for model storage main dir
MODEL_STORAGE_DIR = os.environ.get("MODEL_STORAGE_DIR", os.path.dirname(os.path.realpath(__file__)))

def show_last_models():
    print(latest_models)


def get_mode():
    from tensorflow.python.client import device_lib
    local_device_protos = device_lib.list_local_devices()
    for x in local_device_protos:
        if x.device_type == 'GPU':
            return "gpu"
    return "cpu"


def get_mode_torch():
    import torch
    if torch.cuda.is_available():
        return "gpu"
    return "cpu"


def ls():
    models_list = []
    for r, d, f in os.walk(os.path.join(MODEL_STORAGE_DIR, "./models")):
        for file in f:
            models_list.append(file)
    return models_list


def rm(model_name):
    models_list = []
    for r, d, f in os.walk(os.path.join(MODEL_STORAGE_DIR, "./models")):
        for file in f:
            if file == model_name:
                os.remove(os.path.join(r, file))
                return True
    return False


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output_path):
    with DownloadProgressBar(unit='B', unit_scale=True,
                             miniters=1, desc=url.split('/')[-1]) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


def download_latest_model(detector, model_name, ext="h5", mode = None):
    mode = mode or get_mode()
    if mode != "cpu" and mode != "gpu":
        mode = get_mode()
    info = latest_models[detector][model_name][ext]
    info["path"] = os.path.join(MODEL_STORAGE_DIR, "./models", detector, model_name, os.path.basename(info[mode]))

    p = pathlib.Path(os.path.dirname(info["path"]))
    p.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(info["path"]):
        download_url(info[mode], info['path'])

    return info

