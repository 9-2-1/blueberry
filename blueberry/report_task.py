from typing import Optional, Union, Sequence
from datetime import timedelta
import logging

from tabulate import tabulate, SEPARATING_LINE

from .picker import prefer
from .fmtcolor import fmt, colorit
from .report_base import ReportData, LONG_RUNNING, LONG_WAITING
from .statistic import EmptyLongTaskStats

log = logging.getLogger(__name__)


def report_long_tasks(N: ReportData) -> str:
    table_headers = [
        "",
        "长期任务",
        "点数",
        "完成",
        "剩余",
        "剩余时间",
        "预计用时",
        "日平均",
    ]
    table_colalign = [
        "left",
        "left",
        "decimal",
        "decimal",
        "decimal",
        "right",
        "right",
        "right",
    ]
    总预计时间 = timedelta(0)
    table_lines: list[Union[Sequence[Optional[str]], str]] = []
    for task in prefer(N.state.长期任务.values(), N.state.选择排序偏好):
        tstat = N.stats.长期任务统计[task.名称]
        # 跳过完成0分项
        if tstat.进度 >= task.总数 and N.time >= task.最晚结束:
            continue
        # [None, "名称", "点数", "完成", "剩余", "剩余时间", "预计用时", "每日平均用时"]
        colorpts = tstat.点数 - (0 if tstat.进度 > 0 else 1)
        table_line = [
            colorit(
                LONG_RUNNING if tstat.进度 > 0 else LONG_WAITING, colorpts=colorpts
            ),
            colorit(task.标题, red=N.time >= task.最晚结束),
            colorit(fmt(colorpts, pos=True), colorpts=colorpts),
            colorit(tstat.进度, greyzero=True),
            colorit(task.总数 - tstat.进度, greyzero=True),
            (
                fmt(task.最晚结束 - N.time)
                if tstat.进度 > 0
                else fmt(task.最晚开始 - N.time) + "开始"
            ),
            colorit(tstat.预计需要时间, greyzero=True),
            colorit(tstat.每日用时, greyzero=True),
        ]
        总预计时间 += tstat.预计需要时间
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        None,
        "总数",
        colorit(fmt(N.stats.长期任务点数, pos=True), colorpts=N.stats.长期任务点数),
        None,
        None,
        None,
        colorit(总预计时间, greyzero=True),
        colorit(N.stats.总每日平均用时, greyzero=True),
    ]
    table_lines.append(total_line)
    report = tabulate(
        table_lines, headers=table_headers, colalign=table_colalign, tablefmt="simple"
    )
    return report
