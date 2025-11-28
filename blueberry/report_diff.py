from typing import Optional, Union, Sequence
from datetime import timedelta
import logging

from tabulate import tabulate, SEPARATING_LINE

from .picker import prefer
from .statistic import EmptyLongTaskStats
from .fmtcolor import fmt, colorit
from .report_base import ReportData, LONG_RUNNING, LONG_WAITING

log = logging.getLogger(__name__)


def report_tasks_diff(
    N: ReportData, P: ReportData, hide_decay: bool = False, *, total_str: str = "总数"
) -> str:
    table_headers = ["", "名称", "用时", "完成", "点数", "变化"]
    table_colalign = ["left", "left", "right", "decimal", "decimal", "decimal"]
    总用时 = timedelta(0)
    其它点数 = 0
    其它点数变化 = 0
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
        if hide_decay and nstat1.用时 == pstat1.用时:
            其它点数 += nstat1.点数
            其它点数变化 += nstat1.点数 - pstat1.点数
            continue
        # [None, "名称", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]
        finished = nstat1.进度 >= ntask1.总数
        colorpts = nstat1.点数 - (0 if nstat1.进度 > 0 else 1)
        table_line: list[Optional[str]] = [
            colorit(LONG_RUNNING if not finished else LONG_WAITING, colorpts=colorpts),
            colorit(
                ntask1.标题,
                grey=finished,
                red=not finished and N.time >= ntask1.最晚结束,
            ),
            fmt(nstat1.用时 - pstat1.用时),
            fmt(nstat1.进度 - pstat1.进度),
            colorit(fmt(nstat1.点数, pos=True), colorpts=colorpts),
            colorit(
                fmt(nstat1.点数 - pstat1.点数, pos=True),
                colorchange=nstat1.点数 - pstat1.点数,
            ),
        ]
        总用时 += nstat1.用时 - pstat1.用时
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    if hide_decay:
        total_line = [
            None,
            "其它",
            None,
            None,
            colorit(fmt(其它点数, pos=True), colorpts=其它点数),
            colorit(fmt(其它点数变化, pos=True), colorchange=其它点数变化),
        ]
        table_lines.append(total_line)
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
    ]
    table_lines.append(total_line)
    report = tabulate(
        table_lines, headers=table_headers, colalign=table_colalign, tablefmt="simple"
    )
    return report
