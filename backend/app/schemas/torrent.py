from pydantic import BaseModel


class TorrentInfo(BaseModel):
    hash: str
    name: str
    size: int  # bytes
    progress: float  # 0.0 to 1.0
    status: str
    num_seeds: int
    num_leechs: int
    added_on: int  # timestamp


class TorrentAdd(BaseModel):
    magnet_link: str
