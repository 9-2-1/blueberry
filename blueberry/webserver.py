from datetime import datetime, timedelta
from typing import Optional, TypedDict
import os
import aiohttp.web
import json

from .config import CTZ
from .parser import Data, load_data
from .collect import collect_state
from .statistic import statistic
from .report import fmt
from .ctz_now import ctz_now


async def index_html(request: aiohttp.web.Request) -> aiohttp.web.FileResponse:
    return aiohttp.web.FileResponse("web/index.html")


class Point(TypedDict):
    time: float
    value: int


def smooth(X: list[float], jump: float) -> float:
    window = len(X)
    W = [1 - x / window for x in range(window)]
    D = [X[i] - X[i - 1] if i > 0 else 0 for i in range(len(X))]
    for i in range(window):
        if abs(D[i]) > jump:
            if i == 0:
                D[i] = D[i + 1]
            elif i == window - 1:
                D[i] = D[i - 1]
            else:
                D[i] = (D[i - 1] + D[i + 1]) / 2
    cur = X[0]
    curv = D[0]
    for i in range(1, window):
        curv = curv + (D[i] - curv) * W[i]
        cur += curv
        cur = cur + (X[i] - cur) * W[i]
    return cur


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

    def point_history() -> list[Point]:
        nonlocal points_cache, data, data_timestamp, data_size
        now_time = ctz_now()
        # align to 10 seconds
        pos_time = now_time.replace(second=now_time.second // 10 * 10, microsecond=0)
        history: list[Point] = []
        update_data()
        TC = timedelta(hours=2) // timedelta(seconds=10)
        last_point = None
        for i in range(TC, -2, -1):
            ptime = pos_time - timedelta(seconds=i * 10)
            point = get_point(ptime)
            if last_point != point:
                last_point = point
                history.append(
                    Point(
                        {
                            "time": (ptime - now_time) / timedelta(seconds=1),
                            "value": point,
                        }
                    )
                )
        return history

    async def get_points_experience(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        nonlocal points_cache, data, data_timestamp, data_size
        now_time = ctz_now()
        # align to 10 seconds
        pos_time = now_time.replace(second=now_time.second // 10 * 10, microsecond=0)
        history: list[float] = []
        update_data()
        TC = timedelta(hours=2) // timedelta(seconds=10)
        # 2小时前 → 1分钟后
        for i in range(TC, -2, -1):
            ptime = pos_time - timedelta(seconds=i * 10)
            point = get_point(ptime)
            history.append(point)
        # pos_time → history[TC]
        pt_0 = smooth(history[0 : TC + 1], 10)
        pt_1 = smooth(history[1 : TC + 2], 10)
        speed = (pt_1 - pt_0) / 10  # 点数/秒
        point_f = pt_0 + (pt_1 - pt_0) * (now_time - pos_time) / timedelta(seconds=10)
        return aiohttp.web.Response(
            text=json.dumps(
                {"point": point_f, "speed": speed},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            content_type="application/json",
        )

    async def get_points(request: aiohttp.web.Request) -> aiohttp.web.Response:
        update_data()
        now_time = ctz_now()
        # align to 10 seconds
        pos_time = now_time.replace(second=now_time.second // 10 * 10, microsecond=0)
        point = get_point(pos_time)
        return aiohttp.web.Response(text=fmt(point))

    async def get_points_history(request: aiohttp.web.Request) -> aiohttp.web.Response:
        return aiohttp.web.Response(
            text=json.dumps(point_history(), ensure_ascii=False, separators=(",", ":")),
            content_type="application/json",
        )

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.get("/get_points_history", get_points_history)])
    app.add_routes([aiohttp.web.get("/get_points_experience", get_points_experience)])
    app.add_routes([aiohttp.web.get("/get_points", get_points)])
    app.add_routes([aiohttp.web.post("/get_points", get_points)])
    app.add_routes([aiohttp.web.get("/", index_html)])
    app.add_routes([aiohttp.web.static("/", "web")])
    aiohttp.web.run_app(app, host=host, port=port)
