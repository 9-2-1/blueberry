from datetime import datetime
from typing import Optional, TypedDict
import json
import os
import aiohttp.web
import logging

from .parser import Data, load_data
from .collect import collect_state
from .statistic import statistic
from .fmtcolor import fmt
from .ctz_now import ctz_now

log = logging.getLogger(__name__)


async def index_html(request: aiohttp.web.Request) -> aiohttp.web.FileResponse:
    return aiohttp.web.FileResponse("web/index.html")


async def numberhell_index_html_redirect(
    request: aiohttp.web.Request,
) -> aiohttp.web.Response:
    return aiohttp.web.Response(status=302, headers={"Location": "/numberhell/"})


async def numberhell_index_html(
    request: aiohttp.web.Request,
) -> aiohttp.web.FileResponse:
    return aiohttp.web.FileResponse("web/numberhell/index.html")


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

    class Points(TypedDict):
        time: float
        done: float

    class Report(TypedDict):
        name: str
        tot: float
        speed: float
        starttime: float
        endtime: float
        progress: list[Points]

    def get_number() -> list[Report]:
        nonlocal data
        if data is None:
            raise ValueError("data is None")
        progresses: dict[str, list[Points]] = {}
        for name in collect_state(data, ctz_now()).长期任务.keys():
            progresses[name] = []
        for record in data.长期进度:
            if record.名称 in progresses:
                progresses[record.名称].append(
                    Points(time=record.时间.timestamp(), done=record.进度)
                )
        reports: list[Report] = []
        state = collect_state(data, ctz_now())
        stats = statistic(state, ctz_now())
        for name, task in state.长期任务.items():
            tstat = stats.长期任务统计[name]
            reports.append(
                Report(
                    name=task.名称,
                    tot=task.总数,
                    speed=tstat.速度,
                    starttime=task.最晚开始.timestamp(),
                    endtime=task.最晚结束.timestamp(),
                    progress=progresses[name],
                )
            )
        return reports

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

    async def get_numbers(request: aiohttp.web.Request) -> aiohttp.web.Response:
        update_data()
        reports = get_number()
        return aiohttp.web.Response(
            text=json.dumps(reports, ensure_ascii=False, separators=(",", ":"))
        )

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.get("/get_points", get_points)])
    app.add_routes([aiohttp.web.get("/get_numbers", get_numbers)])
    app.add_routes([aiohttp.web.get("/", index_html)])
    app.add_routes([aiohttp.web.get("/numberhell", numberhell_index_html_redirect)])
    app.add_routes([aiohttp.web.get("/numberhell/", numberhell_index_html)])
    app.add_routes([aiohttp.web.static("/", "web")])
    aiohttp.web.run_app(app, host=host, port=port)
