from datetime import datetime, timedelta
from typing import Optional, TypedDict, Literal
import json
import time
import calendar
import os
import aiohttp.web
import logging

from .config import CTZ
from .parser import Data, load_data
from .collect import collect_state
from .statistic import statistic
from .fmtcolor import fmt
from .models import DeleteModel
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

    pointcache_value: int = 0
    pointcache_time: float = 0

    numbercache_value: Optional[str] = None

    def get_point(pos_time: datetime) -> int:
        nonlocal pointcache_value, pointcache_time, data, data_timestamp, data_size
        if pos_time.timestamp() == pointcache_time:
            return pointcache_value
        if data is None:
            raise ValueError("data is None")
        pos_state = collect_state(data, pos_time)
        pos_statistic = statistic(pos_state, pos_time)
        point = pos_statistic.Goldie点数
        pointcache_value = point
        pointcache_time = pos_time.timestamp()
        return point

    class Points(TypedDict):
        time: float
        done: float

    class Report(TypedDict):
        name: str
        mode: Literal["short", "long"]
        tot: float
        speed: float
        starttime: float
        endtime: float
        progress: list[Points]

    def get_number() -> str:  # json.dumps(list[Report])
        nonlocal numbercache_value, data
        assert data is not None
        if numbercache_value is None:
            reports: list[Report] = []
            state = collect_state(data, ctz_now())
            stats = statistic(state, ctz_now())

            # 长期任务
            progresses: dict[str, list[Points]] = {}
            for name in collect_state(data, ctz_now()).长期任务.keys():
                progresses[name] = []
            for record in data.长期进度:
                if record.名称 in progresses:
                    progresses[record.名称].append(
                        Points(
                            time=record.时间.replace(tzinfo=CTZ).timestamp(),
                            done=record.进度,
                        )
                    )
            for name, task in state.长期任务.items():
                tstat = stats.长期任务统计[name]
                reports.append(
                    Report(
                        name=task.名称,
                        mode="long",
                        tot=task.总数,
                        speed=tstat.速度,
                        starttime=task.最晚开始.replace(tzinfo=CTZ).timestamp(),
                        endtime=task.最晚结束.replace(tzinfo=CTZ).timestamp(),
                        progress=progresses[name],
                    )
                )

            # 短期任务
            progresses = {}
            for name in collect_state(data, ctz_now()).短期任务.keys():
                progresses[name] = []
            for srecord in data.短期任务:
                if isinstance(srecord, DeleteModel):
                    continue
                if srecord.名称 in progresses:
                    if srecord.用时 is not None:
                        用时 = srecord.用时 / timedelta(hours=1)
                    else:
                        用时 = 0.0
                    progresses[srecord.名称].append(
                        Points(
                            time=srecord.时间.replace(tzinfo=CTZ).timestamp(), done=用时
                        )
                    )
                    if srecord.完成 is not None:
                        progresses[srecord.名称].append(
                            Points(
                                time=srecord.完成.replace(tzinfo=CTZ).timestamp(),
                                done=srecord.预计用时 / timedelta(hours=1),
                            )
                        )
            for name, task2 in state.短期任务.items():
                reports.append(
                    Report(
                        name=task2.名称,
                        mode="short",
                        tot=task2.预计用时 / timedelta(hours=1),
                        speed=1,  # 短期任务的完成数量=完成用时小时数
                        starttime=progresses[name][0]["time"],
                        endtime=task2.最晚结束.replace(tzinfo=CTZ).timestamp(),
                        progress=progresses[name],
                    )
                )

            assert data_timestamp is not None
            numbercache_value = json.dumps(
                reports, ensure_ascii=False, separators=(",", ":")
            )
        return numbercache_value

    def update_data() -> bool:
        nonlocal pointcache_time, numbercache_value, data, data_timestamp, data_size
        wstat = os.stat(workbook)
        if data_timestamp == wstat.st_mtime and data_size == wstat.st_size:
            return False
        data = load_data(workbook)
        data_timestamp = wstat.st_mtime
        data_size = wstat.st_size
        pointcache_time = 0
        numbercache_value = None
        return True

    async def get_points(request: aiohttp.web.Request) -> aiohttp.web.Response:
        update_data()
        now_time = ctz_now()
        # align to 10 seconds
        pos_time = now_time.replace(second=now_time.second // 10 * 10, microsecond=0)
        point = get_point(pos_time)
        return aiohttp.web.Response(text=fmt(point))

    async def get_numbers(request: aiohttp.web.Request) -> aiohttp.web.Response:
        nonlocal data_timestamp, numbercache_value
        update_data()

        assert data_timestamp is not None
        last_modified = time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(int(data_timestamp))
        )
        if_modified_since = request.headers.get("If-Modified-Since", "?")
        try:
            req_timestamp = calendar.timegm(
                time.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT")
            )
        except ValueError:
            req_timestamp = int(data_timestamp) - 1
        headers = {
            "Last-Modified": last_modified,
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
        }
        if int(data_timestamp) == int(req_timestamp):
            return aiohttp.web.Response(status=304, headers=headers)

        reports = get_number()
        response = aiohttp.web.Response(text=reports, headers=headers)
        response.enable_compression(False, 9)
        return response

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.get("/get_points", get_points)])
    app.add_routes([aiohttp.web.get("/get_numbers", get_numbers)])
    app.add_routes([aiohttp.web.get("/", index_html)])
    app.add_routes([aiohttp.web.get("/numberhell", numberhell_index_html_redirect)])
    app.add_routes([aiohttp.web.get("/numberhell/", numberhell_index_html)])
    app.add_routes([aiohttp.web.static("/", "web")])
    aiohttp.web.run_app(app, host=host, port=port)
