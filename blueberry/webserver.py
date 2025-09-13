from datetime import datetime
from typing import Optional
import os
import aiohttp.web
import logging

from .parser import Data, load_data
from .collect import collect_state
from .statistic import statistic
from .report import fmt
from .ctz_now import ctz_now


async def index_html(request: aiohttp.web.Request) -> aiohttp.web.FileResponse:
    return aiohttp.web.FileResponse("web/index.html")


def live_server(workbook: str, host: str, port: int) -> None:
    data: Optional[Data] = None
    data_timestamp: Optional[float] = None
    data_size: Optional[int] = None
    points_cache: dict[datetime, int] = {}

    def get_point(pos_time: datetime) -> int:
        nonlocal points_cache, data, data_timestamp, data_size
        point = points_cache.get(pos_time)
        if point is None:
            if data is None:
                raise ValueError("data is None")
            pos_state = collect_state(data, pos_time)
            pos_statistic = statistic(pos_state, pos_time)
            point = pos_statistic.Goldie点数
            points_cache[pos_time] = point
        return point

    def update_data() -> bool:
        nonlocal points_cache, data, data_timestamp, data_size
        wstat = os.stat(workbook)
        if data_timestamp == wstat.st_mtime and data_size == wstat.st_size:
            return False
        data = load_data(workbook)
        data_timestamp = wstat.st_mtime
        data_size = wstat.st_size
        points_cache.clear()
        return True

    async def get_points(request: aiohttp.web.Request) -> aiohttp.web.Response:
        update_data()
        now_time = ctz_now()
        # align to 10 seconds
        pos_time = now_time.replace(second=now_time.second // 10 * 10, microsecond=0)
        point = get_point(pos_time)
        return aiohttp.web.Response(text=fmt(point))

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.get("/get_points", get_points)])
    app.add_routes([aiohttp.web.get("/", index_html)])
    app.add_routes([aiohttp.web.static("/", "web")])
    aiohttp.web.run_app(app, host=host, port=port)
