from datetime import datetime
import aiohttp.web

from .parser import load_data
from .collect import collect_state
from .statistic import statistic
from .report import fmt


async def index_html(request: aiohttp.web.Request) -> aiohttp.web.FileResponse:
    return aiohttp.web.FileResponse("web/index.html")


def live_server(workbook: str, host: str, port: int) -> None:
    async def get_points(request: aiohttp.web.Request) -> aiohttp.web.Response:
        data = load_data(workbook)
        now_time = datetime.now()
        now_state = collect_state(data, now_time)
        now_statistic = statistic(now_state, now_time)
        return aiohttp.web.Response(text=fmt(now_statistic.Goldie点数))

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.post("/get_points", get_points)])
    app.add_routes([aiohttp.web.get("/", index_html)])
    app.add_routes([aiohttp.web.static("/", "web")])
    aiohttp.web.run_app(app, host=host, port=port)
