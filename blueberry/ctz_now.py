from .config import CTZ
from datetime import datetime


def ctz_now() -> datetime:
    current_time = datetime.now()
    target_time = current_time.astimezone(CTZ)
    naive_time = target_time.replace(tzinfo=None)
    return naive_time
