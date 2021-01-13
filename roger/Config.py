import yaml
from flatten_dict import flatten, unflatten
from os import path
from typing import Dict, Optional


CONFIG_FILENAME = path.join(path.dirname(path.abspath(__file__)), 'config.yaml')


class Config:
    """
    Singleton config wrapper
    """
    __instance__: Optional[Dict] = None

    def __init__(self, file_name: str):
        if not Config.__instance__:
            Config.__instance__ = Config.read_config_file(file_name=file_name)

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
        return Config.__instance__.__str__()


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
