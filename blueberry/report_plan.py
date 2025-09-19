from typing import Optional, Union, Sequence
from datetime import datetime, timedelta
import logging

# 用于tabulate的宽度计算
from tabulate import tabulate, SEPARATING_LINE

from .picker import prefer
from .statistic import EmptyLongTaskStats, EmptyShortTaskStats
from .planner import Plan
from .fmtcolor import fmt, colorit
from .report_base import (
    ReportData,
    LONG_RUNNING,
    LONG_WAITING,
    SHORT_RUNNING,
    SHORT_WAITING,
)

log = logging.getLogger(__name__)


def report_tasks_plan(
    N: ReportData,
    P: ReportData,
    R: Plan,
    end_time: datetime,
    *,
    total_str: str = "总数",
) -> str:
    table_headers = [
        "",
        "名称",
        "用时",
        "完成",
        "点数",
        "变化",
        "建议",
        "时长",
        "剩余时间",
    ]
    table_colalign = [
        "left",
        "left",
        "right",
        "decimal",
        "decimal",
        "decimal",
        "decimal",
        "right",
        "right",
    ]
    总推荐每日用时 = timedelta(0)
    总用时 = timedelta(0)
    table_lines: list[Union[Sequence[Optional[str]], str]] = []
    for ntask1 in prefer(N.state.长期任务.values(), N.state.选择排序偏好):
        nstat1 = N.stats.长期任务统计[ntask1.名称]
        if ntask1.名称 not in P.stats.长期任务统计:
            pstat1 = EmptyLongTaskStats(ntask1)
        else:
            pstat1 = P.stats.长期任务统计[ntask1.名称]
        # 跳过完成0分项
        if pstat1.进度 >= ntask1.总数 and N.time >= ntask1.最晚结束:
            continue
        推荐每日用时 = R.建议用时.get(ntask1.名称, timedelta(0))
        总推荐每日用时 += 推荐每日用时
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]
        colorpts = nstat1.点数 - (0 if nstat1.进度 > 0 else 1)
        推荐完成 = 推荐每日用时 / timedelta(hours=1) * nstat1.速度
        time_reach_recommend = nstat1.用时 - pstat1.用时 >= 推荐每日用时
        finished = nstat1.进度 >= ntask1.总数
        reach_recommend = finished or (
            nstat1.速度 != 0 and nstat1.进度 - pstat1.进度 >= 推荐完成
        )
        table_line: list[Optional[str]] = [
            colorit(
                LONG_RUNNING if not reach_recommend else LONG_WAITING, colorpts=colorpts
            ),
            colorit(
                ntask1.标题,
                grey=reach_recommend,
                red=not finished and N.time >= ntask1.最晚结束,
            ),
            colorit(
                nstat1.用时 - pstat1.用时,
                grey=time_reach_recommend and nstat1.用时 == pstat1.用时,
                blue=time_reach_recommend and nstat1.用时 != pstat1.用时,
            ),
            colorit(
                nstat1.进度 - pstat1.进度,
                grey=reach_recommend and nstat1.进度 == pstat1.进度,
                blue=reach_recommend and nstat1.进度 != pstat1.进度,
            ),
            colorit(fmt(nstat1.点数, pos=True), colorpts=colorpts),
            colorit(
                fmt(nstat1.点数 - pstat1.点数, pos=True),
                colorchange=nstat1.点数 - pstat1.点数,
            ),
            colorit(fmt(推荐完成, p2=True), greyzero=True),
            colorit(推荐每日用时, greyzero=True),
            colorit(
                (
                    fmt(ntask1.最晚结束 - N.time)
                    if nstat1.进度 > 0
                    else fmt(ntask1.最晚开始 - N.time) + "开始"
                ),
                grey=finished,
            ),
        ]
        总用时 += nstat1.用时 - pstat1.用时
        table_lines.append(table_line)
    for ntask2 in prefer(N.state.短期任务.values(), N.state.选择排序偏好):
        nstat2 = N.stats.短期任务统计[ntask2.名称]
        if ntask2.名称 not in P.stats.短期任务统计:
            pstat2 = EmptyShortTaskStats(ntask2)
        else:
            pstat2 = P.stats.短期任务统计[ntask2.名称]
        # 跳过完成0分项
        if (
            ntask2.完成 is not None
            and P.time >= ntask2.完成
            and P.time >= ntask2.最晚结束
        ):
            continue
        推荐每日用时 = R.建议用时.get(ntask2.名称, timedelta(0))
        总推荐每日用时 += 推荐每日用时
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]"]
        colorpts = nstat2.点数 - (
            0 if ntask2.完成 is not None and N.time >= ntask2.完成 else 1
        )
        finished = ntask2.完成 is not None and N.time >= ntask2.完成
        reach_recommend = finished or 推荐每日用时 == timedelta(0)
        table_line = [
            colorit(
                SHORT_RUNNING if not reach_recommend else SHORT_WAITING,
                colorpts=colorpts,
            ),
            colorit(
                ntask2.标题,
                grey=reach_recommend,
                red=not finished and N.time >= ntask2.最晚结束,
            ),
            colorit(nstat2.用时 - pstat2.用时, greyzero=True, blue=reach_recommend),
            (
                colorit("*", blue=True)
                if ntask2.完成 is not None and N.time >= ntask2.完成
                else None
            ),
            colorit(fmt(nstat2.点数, pos=True), colorpts=colorpts),
            colorit(
                fmt(nstat2.点数 - pstat2.点数, pos=True),
                colorchange=nstat2.点数 - pstat2.点数,
            ),
            None,
            colorit(推荐每日用时, greyzero=True),
            colorit(
                ntask2.最晚结束 - N.time,
                grey=finished,
            ),
        ]
        总用时 += nstat2.用时 - pstat2.用时
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        None,
        total_str,
        colorit(总用时, greyzero=True),
        None,
        colorit(fmt(N.stats.Goldie点数, pos=True), colorpts=N.stats.Goldie点数),
        colorit(
            fmt(N.stats.Goldie点数 - P.stats.Goldie点数, pos=True),
            colorchange=N.stats.Goldie点数 - P.stats.Goldie点数,
        ),
        None,
        colorit(总推荐每日用时, greyzero=True),
        None,
    ]
    table_lines.append(total_line)
    report = tabulate(
        table_lines, headers=table_headers, colalign=table_colalign, tablefmt="simple"
    )
    return report
