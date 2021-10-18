from dataclasses import dataclass

from ._base import DictLike


@dataclass
class S3Config(DictLike):
    host: str = ""
    bucket: str = ""
    access_key: str = ""
    secret_key: str = ""
    enabled: bool = False
