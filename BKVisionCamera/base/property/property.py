import os
from collections import defaultdict
from pathlib import Path

import yaml

from BKVisionCamera import CONFIG


class BaseProperty(object):
    def __init__(self, yaml_path: str):

        def _load_yaml(yaml_url):
            with open(yaml_url, 'r', encoding=CONFIG.ENCODE) as f:
                yaml_dict_ = yaml.load(f, Loader=yaml.FullLoader)
                print(yaml_dict_)
                if yaml_dict_.get('extends', None):
                    extends = yaml_dict_.pop('extends')
                    extends_path = os.path.join(self.dir_path, extends)
                    extends_dict = _load_yaml(extends_path)
                    extends_dict.update(yaml_dict_)
                    yaml_dict_ = extends_dict
                return yaml_dict_

        if os.path.isdir(yaml_path):
            yaml_path = os.path.join(yaml_path, "config.yaml")
        self.dir_path = os.path.dirname(yaml_path)
        if os.path.exists(yaml_path) is False:
            raise FileNotFoundError(f"File {yaml_path} not found")
        self.yaml_path = yaml_path
        self.yaml_dict = _load_yaml(self.yaml_path)
        self.type = self.yaml_dict.get('type', None)

        self.name = self.yaml_dict.get('name', None)
        self.debug = self.yaml_dict.get('debug', False)
        self.selectType = self.yaml_dict.get('selectType', 'index')
        self.configFile = self.yaml_dict.get('configFile', None)
        self.ip = self.yaml_dict.get('ip', None)
        self.mac = self.yaml_dict.get('mac', None)
        self.index = self.yaml_dict.get('index', None)



