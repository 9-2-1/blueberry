from typing import TypeVar, Optional, Union, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
from tabulate import tabulate, SEPARATING_LINE
import tabulate as Tabulate

from .models import AppendOnly
from .collect import State
from .picker import prefer
from .statistic import StateStats, EmptyLongTaskStats, EmptyShortTaskStats
from .planner import Plan
from .fmtcolor import fmt, colorit

log = logging.getLogger(__name__)

Tabulate.PRESERVE_WHITESPACE = True


LONG_RUNNING = "●"
LONG_WAITING = "◯"
SHORT_RUNNING = "■"
SHORT_WAITING = "□"


@dataclass
class ReportData:
    time: datetime
    state: State
    stats: StateStats


T = TypeVar("T", bound=AppendOnly)


def report_head(N: ReportData) -> str:
    report = f"blueberry - {N.time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"近期每日平均用时: {fmt(N.stats.总每日平均用时)}\n"
    return report


def report_plan_head(R: Plan, now_time: datetime) -> str:
    report = f"建议用时: {fmt(R.总建议用时)} "
    report += f"(保持 {fmt(R.保持用时)} + 在 {fmt(R.下一关键时间)} ({fmt(R.下一关键时间 - now_time)})"
    report += f" 前完成 {fmt(R.下一关键节点任务量时长)} 工作量)"
    return report


def report_worktime(N: ReportData) -> str:
    worktime = N.state.工作时段
    if not worktime:
        return "工作时段: 未设定"
    report = "工作时段:"
    for workt in worktime:
        report += f" {workt.开始.hour:02d}:{workt.开始.minute:02d}~{workt.结束.hour:02d}:{workt.结束.minute:02d}"
    return report.strip()


def report_long_tasks(N: ReportData) -> str:
    table_headers = [
        "",
        "长期任务",
        "|",
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
        "center",  # "|"
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
        # [None, "名称", "|", "点数", "完成", "剩余", "剩余时间", "预计用时", "每日平均用时"]
        colorpts = tstat.点数 - (0 if tstat.进度 > 0 else 1)
        table_line = [
            colorit(
                LONG_RUNNING if tstat.进度 > 0 else LONG_WAITING, colorpts=colorpts
            ),
            colorit(task.标题, red=N.time >= task.最晚结束),
            "|",
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
        "|",
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


def report_short_tasks(N: ReportData) -> str:
    table_lines: list[Union[Sequence[Optional[str]], str]] = []
    table_headers = [
        "",
        "短期任务",
        "|",
        "点数",
        "用时",
        "预计时间",
        "剩余时间",
    ]
    table_colalign = [
        "left",
        "left",
        "center",  # "|"
        "decimal",
        "right",
        "right",
        "right",
    ]
    总用时 = timedelta(0)
    总预计时间 = timedelta(0)
    for task in prefer(N.state.短期任务.values(), N.state.选择排序偏好):
        # 跳过完成0分项
        if task.完成 is not None and N.time >= task.完成 and N.time >= task.最晚结束:
            continue
        tstat = N.stats.短期任务统计[task.名称]
        colorpts = tstat.点数 - (0 if task.完成 else 1)
        table_line = [
            colorit(
                SHORT_RUNNING if tstat.用时 > timedelta(0) else SHORT_WAITING,
                colorpts=colorpts,
            ),
            colorit(task.标题, red=N.time >= task.最晚结束),
            "|",
            colorit(fmt(colorpts, pos=True), colorpts=colorpts),
            colorit(tstat.用时, greyzero=True),
            colorit(tstat.预计需要时间, greyzero=True),
            fmt(task.最晚结束 - N.time),
        ]
        总用时 += tstat.用时
        总预计时间 += tstat.预计需要时间
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        None,
        "总数",
        "|",
        colorit(fmt(N.stats.短期任务点数, pos=True), colorpts=N.stats.短期任务点数),
        colorit(总用时, greyzero=True),
        colorit(总预计时间, greyzero=True),
        None,
    ]
    table_lines.append(total_line)
    report = tabulate(
        table_lines, headers=table_headers, colalign=table_colalign, tablefmt="simple"
    )
    return report


def report_tasks_diff(
    N: ReportData, P: ReportData, hide_decay: bool = False, *, total_str: str = "总数"
) -> str:
    table_headers = [
        "",
        "名称",
        "|",
        "用时",
        "完成",
        "点数",
        "变化",
    ]
    table_colalign = [
        "left",
        "left",
        "center",  # "|"
        "right",
        "decimal",
        "decimal",
        "decimal",
    ]
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
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]
        finished = nstat1.进度 >= ntask1.总数
        colorpts = nstat1.点数 - (0 if nstat1.进度 > 0 else 1)
        table_line: list[Optional[str]] = [
            colorit(LONG_RUNNING if not finished else LONG_WAITING, colorpts=colorpts),
            colorit(
                ntask1.标题,
                grey=finished,
                red=not finished and N.time >= ntask1.最晚结束,
            ),
            "|",
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
        if hide_decay and nstat2.用时 == pstat2.用时:
            其它点数 += nstat2.点数
            其它点数变化 += nstat2.点数 - pstat2.点数
            continue
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]"]
        colorpts = nstat2.点数 - (
            0 if ntask2.完成 is not None and N.time >= ntask2.完成 else 1
        )
        finished = ntask2.完成 is not None and N.time >= ntask2.完成
        table_line = [
            colorit(
                SHORT_RUNNING if not finished else SHORT_WAITING,
                colorpts=colorpts,
            ),
            colorit(
                ntask2.标题,
                grey=finished,
                red=not finished and N.time >= ntask2.最晚结束,
            ),
            "|",
            colorit(nstat2.用时 - pstat2.用时, greyzero=True),
            ("*" if ntask2.完成 is not None and N.time >= ntask2.完成 else None),
            colorit(fmt(nstat2.点数, pos=True), colorpts=colorpts),
            colorit(
                fmt(nstat2.点数 - pstat2.点数, pos=True),
                colorchange=nstat2.点数 - pstat2.点数,
            ),
        ]
        总用时 += nstat2.用时 - pstat2.用时
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    if hide_decay:
        total_line = [
            None,
            "其它",
            "|",
            None,
            None,
            colorit(fmt(其它点数, pos=True), colorpts=其它点数),
            colorit(fmt(其它点数变化, pos=True), colorchange=其它点数变化),
        ]
        table_lines.append(total_line)
    total_line = [
        None,
        total_str,
        "|",
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
        "|",
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
        "center",  # "|"
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
            "|",
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
            "|",
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
        "|",
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
