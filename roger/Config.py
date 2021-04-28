import json
import os
import warnings
import yaml

from flatten_dict import flatten, unflatten
from typing import Dict, Optional


CONFIG_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')


class Config:
    """
    Singleton config wrapper
    """
    __instance__: Optional[Dict] = None
    os_var_prefix = "ROGERENV_"

    def __init__(self, file_name: str):
        if not Config.__instance__:
            Config.__instance__ = Config.read_config_file(file_name=file_name)
            os_var_keys = os.environ.keys()
            keys_of_interest = [x for x in os_var_keys if x.startswith(Config.os_var_prefix)]
            for key in keys_of_interest:
                new_key = key.replace(Config.os_var_prefix, "")
                value = os.environ[key]
                new_dict = Config.os_var_to_dict(new_key, value)
                try:
                    Config.update(new_dict)
                except ValueError as e:
                    warnings.warn(f"{e} encountered trying to assign string from "
                                  f"OS variable `{key}` to a dictionary object."
                                  f"Please specify inner keys.")

    @staticmethod
    def os_var_to_dict(var_name, value):
        var_name = var_name.replace("__", "~")
        var_name = var_name.replace("_", ".")
        var_name = var_name.replace("~", "_")
        var_name = var_name.lower()
        m = {var_name: value}
        result = unflatten(m, "dot")
        return result

    @staticmethod
    def read_config_file(file_name: str):
        return yaml.load(open(file_name), Loader=yaml.FullLoader)

    def __getattr__(self, item):
        """
        Proxies calls to instance dict.
        Note: dict.update is overridden to do partial updates.
        Refer to Config.update method.
        :param item: method called
        :return: proxied method
        """
        if item == 'update':
            # overrides default dict update method
            return self.update
        return getattr(Config.__instance__, item)

    def __getitem__(self, item):
        """
        Makes config object subscriptable
        :param item: key to lookup
        :return: value stored in key
        """
        return self.__instance__.get(item)

    @staticmethod
    def update(new_value: Dict):
        """
        Updates dictionary partially.
        Given a config {'name': {'first': 'name', 'last': 'name'}}
        and a partial update {'name': {'first': 'new name'} }
        result would be {'name': {'first': 'new name', 'last': 'name'}}
        :param new_value: parts to update
        :return: updated dict
        """
        config_flat = flatten(Config.__instance__)
        new_value_flat = flatten(new_value)
        config_flat.update(new_value_flat)
        Config.__instance__ = unflatten(config_flat)
        return Config.__instance__

    def __str__(self):
        flat = flatten(Config.__instance__)
        for k in flat:
            if 'PASSWORD' in k or 'password' in k:
                flat[k] = '******'
        flat = unflatten(flat)
        result = json.dumps(flat)
        return f"""{result}"""


def get_default_config(file_name: str = CONFIG_FILENAME) -> Config:
    """
    Get config as a dictionary

    Parameters
    ----------
    file_name: str
        The filename with all the configuration

    Returns
    -------
    dict
        A dictionary containing all the entries from the config YAML

    """
    config_instance = Config(file_name)
    return config_instance


config: Config = get_default_config()
