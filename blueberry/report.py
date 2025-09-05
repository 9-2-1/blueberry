from typing import TypeVar, overload, Optional, Iterable, Union, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta
from textwrap import indent
import warnings

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
from tabulate import tabulate, SEPARATING_LINE

from .config import 推荐用时
from .models import AppendOnly, PickerModel
from .collect import State
from .statistic import StateStats, isdisabled, EmptyLongTaskStats, EmptyShortTaskStats


FmtT = TypeVar("FmtT", int, float, datetime, timedelta)


@overload
def fmt(x: FmtT, *, pos: bool = False, p2: bool = False) -> str: ...


@overload
def fmt(
    x: FmtT,
    y: FmtT,
    *,
    pos: bool = False,
    p2: bool = False,
    olddiff: bool = True,
) -> str: ...


def fmt(
    x: FmtT,
    y: Optional[FmtT] = None,
    *,
    pos: bool = False,
    p2: bool = False,
    olddiff: bool = True,
) -> str:
    if y is None:
        if isinstance(x, int):
            if pos:
                return f"{x:+d}"
            else:
                return f"{x:d}"
        elif isinstance(x, float):
            if p2:
                if pos:
                    return f"{x:+.2f}"
                else:
                    return f"{x:.2f}"
            else:
                if pos:
                    return f"{x:+g}"
                else:
                    return f"{x:g}"
        elif isinstance(x, datetime):
            if pos:
                raise TypeError("datetime无符号")
            else:
                return x.strftime("%m/%d %H:%M")
        elif isinstance(x, timedelta):
            sign = ""
            if x >= timedelta(0):
                if pos:
                    sign = "+"
                v = x
            else:
                sign = "-"
                v = -x
            if v > timedelta(days=7):
                vstr = f"{v // timedelta(days=1)}d"
            elif v > timedelta(days=1):
                vstr = f"{v // timedelta(days=1)}d{v // timedelta(hours=1) % 24}h"
            elif v > timedelta(hours=1):
                vstr = f"{v // timedelta(hours=1)}h{v // timedelta(minutes=1) % 60}m"
            else:
                vstr = f"{v.seconds // 60}min"
            return sign + vstr
        else:
            raise TypeError("未知类型")
    else:
        if olddiff:
            return f"{fmt(x, pos=pos)} → {fmt(y, pos=pos)}"
        else:
            if isinstance(y, timedelta):
                return f"{fmt(y, pos=pos)}({fmt(y - x, pos=True)})"
            else:
                return f"{fmt(y, pos=pos)}({fmt(y - x, pos=True)})"


ESC = "\033"
RED = 1
GREEN = 2
YELLOW = 3
BLUE = 4
MAGENTA = 5
CYAN = 6
WHITE = 7
goldie_thresholds = [-100, -50, 0, 50, 100]
goldie_levels = [RED, MAGENTA, YELLOW, GREEN, CYAN, BLUE]
LONG_RUNNING = "●"
LONG_WAITING = "◯"
SHORT_RUNNING = "■"
SHORT_WAITING = "□"


def getcolor(goldie: int) -> int:
    for i, threshold in enumerate(goldie_thresholds):
        if goldie < threshold:
            return goldie_levels[i]
    return goldie_levels[-1]


def colorline(
    table_line: list[str], color: int, skip: tuple[int, ...] = ()
) -> list[str]:
    return [
        f"{ESC}[3{color}m{item}{ESC}[37m" if i not in skip else item
        for i, item in enumerate(table_line)
    ]


@dataclass
class ReportData:
    time: datetime
    state: State
    stats: StateStats


T = TypeVar("T", bound=AppendOnly)


def priority(item: T, preference: list[PickerModel]) -> int:
    for i, picker in enumerate(preference):
        if item.名称 == picker.名称:
            return i
    return len(preference)


def prefer(items: Iterable[T], preference: list[PickerModel]) -> list[T]:
    filtered_items = filter(lambda x: not isdisabled(x.名称, preference), items)
    sorted_items = sorted(filtered_items, key=lambda x: priority(x, preference))
    return sorted_items


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
        "负载",
        "完成",
        "剩余",
        "剩余时间",
        "预计用时",
        "每日平均用时",
    ]
    最大负载 = 0.0
    总预计时间 = timedelta(0)
    table_lines: list[Union[list[str], str]] = []
    for task in prefer(N.state.长期任务.values(), N.state.选择排序偏好):
        tstat = N.stats.长期任务统计[task.名称]
        # 跳过完成0分项
        if tstat.进度 >= task.总数 and N.time >= task.最晚结束:
            continue
        # ["", "名称", "|", "点数", "负载", "完成", "剩余", "剩余时间", "预计用时", "每日平均用时"]
        table_line = [
            LONG_RUNNING if tstat.进度 > 0 else LONG_WAITING,
            task.名称,
            "|",
            fmt(tstat.点数),
            f"{tstat.负载程度:.2f}",
            fmt(tstat.进度),
            fmt(task.总数 - tstat.进度),
            (
                fmt(task.最晚结束 - N.time)
                if tstat.进度 > 0
                else fmt(task.最晚开始 - N.time) + "开始"
            ),
            fmt(tstat.预计需要时间),
            fmt(tstat.每日用时),
        ]
        最大负载 = max(最大负载, tstat.负载程度)
        总预计时间 += tstat.预计需要时间
        table_line = colorline(
            table_line, getcolor(tstat.点数 - (0 if tstat.进度 > 0 else 1)), skip=(2,)
        )
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        "",
        "总数",
        "|",
        fmt(N.stats.长期任务点数),
        f"{最大负载:.2f}",
        "",
        "",
        "",
        fmt(总预计时间),
        fmt(N.stats.总每日平均用时),
    ]
    total_line = colorline(
        total_line,
        getcolor(N.stats.长期任务点数 - (0 if tstat.进度 > 0 else 1)),
        skip=(2,),
    )
    table_lines.append(total_line)
    report = tabulate(table_lines, headers=table_headers, tablefmt="simple")
    return report


def report_short_tasks(N: ReportData) -> str:
    table_lines: list[Union[list[str], str]] = []
    table_headers = [
        "",
        "短期任务",
        "|",
        "点数",
        "负载",
        "用时",
        "预计时间",
        "剩余时间",
    ]
    最大负载 = 0.0
    总用时 = timedelta(0)
    总预计时间 = timedelta(0)
    for task in prefer(N.state.短期任务.values(), N.state.选择排序偏好):
        # 跳过完成0分项
        if task.完成 is not None and N.time >= task.完成 and N.time >= task.最晚结束:
            continue
        tstat = N.stats.短期任务统计[task.名称]
        table_line = [
            SHORT_RUNNING if tstat.用时 > timedelta(0) else SHORT_WAITING,
            task.标题,
            "|",
            fmt(tstat.点数),
            f"{tstat.负载程度:.2f}",
            fmt(tstat.用时),
            fmt(tstat.预计需要时间),
            fmt(task.最晚结束 - N.time),
        ]
        最大负载 = max(最大负载, tstat.负载程度)
        总用时 += tstat.用时
        总预计时间 += tstat.预计需要时间
        table_line = colorline(
            table_line, getcolor(tstat.点数 - (0 if task.完成 else 1)), skip=(2,)
        )
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        "",
        "总数",
        "|",
        fmt(N.stats.短期任务点数),
        f"{最大负载:.2f}",
        fmt(总用时),
        fmt(总预计时间),
        "",
    ]
    total_line = colorline(
        total_line, getcolor(N.stats.短期任务点数 - (0 if task.完成 else 1)), skip=(2,)
    )
    table_lines.append(total_line)
    report = tabulate(table_lines, headers=table_headers, tablefmt="simple")
    return report


def report_tasks_diff(N: ReportData, P: ReportData, hide_decay: bool = False) -> str:
    table_headers = [
        "",
        "名称",
        "|",
        "用时",
        "完成",
        "点数",
        "变化",
        "负载",
        "剩余时间",
    ]
    最大负载 = 0.0
    最大负载p = 0.0
    总用时 = timedelta(0)
    其它点数 = 0
    其它点数变化 = 0
    table_lines: list[Union[list[str], str]] = []
    for ntask1 in prefer(N.state.长期任务.values(), N.state.选择排序偏好):
        nstat1 = N.stats.长期任务统计[ntask1.名称]
        if ntask1.名称 not in P.stats.长期任务统计:
            pstat1 = EmptyLongTaskStats(ntask1)
        else:
            pstat1 = P.stats.长期任务统计[ntask1.名称]
        # 跳过完成0分项
        if pstat1.进度 >= ntask1.总数 and N.time >= ntask1.最晚结束:
            continue
        最大负载 = max(最大负载, nstat1.负载程度)
        最大负载p = max(最大负载p, pstat1.负载程度)
        if hide_decay and nstat1.用时 == pstat1.用时:
            其它点数 += nstat1.点数
            其它点数变化 += nstat1.点数 - pstat1.点数
            continue
        # ["", "名称", "|", "用时", "完成", "点数", "变化", "负载", "剩余时间"]
        table_line = [
            LONG_RUNNING if nstat1.用时 != pstat1.用时 else LONG_WAITING,
            ntask1.标题,
            "|",
            fmt(nstat1.用时 - pstat1.用时),
            fmt(nstat1.进度 - pstat1.进度),
            fmt(nstat1.点数),
            fmt(nstat1.点数 - pstat1.点数, pos=True),
            fmt(nstat1.负载程度, p2=True),
            (
                fmt(ntask1.最晚结束 - N.time)
                if nstat1.进度 > 0
                else fmt(ntask1.最晚开始 - N.time) + "开始"
            ),
        ]
        总用时 += nstat1.用时 - pstat1.用时
        table_line = colorline(
            table_line, getcolor(nstat1.点数 - (0 if nstat1.进度 > 0 else 1)), skip=(2,)
        )
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
            and N.time >= ntask2.完成
            and N.time >= ntask2.最晚结束
        ):
            continue
        最大负载 = max(最大负载, nstat2.负载程度)
        最大负载p = max(最大负载p, pstat2.负载程度)
        if hide_decay and nstat2.用时 == pstat2.用时:
            其它点数 += nstat2.点数
            其它点数变化 += nstat2.点数 - pstat2.点数
            continue
        # ["", "名称", "|", "用时", "完成", "点数", "变化", "负载", "剩余时间"]
        table_line = [
            SHORT_RUNNING if nstat2.用时 != pstat2.用时 else SHORT_WAITING,
            ntask2.标题,
            "|",
            fmt(nstat2.用时 - pstat2.用时),
            "√" if ntask2.完成 is not None else "",
            fmt(nstat2.点数),
            fmt(nstat2.点数 - pstat2.点数, pos=True),
            fmt(nstat2.负载程度, p2=True),
            fmt(ntask2.最晚结束 - N.time),
        ]
        总用时 += nstat2.用时 - pstat2.用时
        table_line = colorline(
            table_line,
            getcolor(nstat2.点数 - (0 if ntask2.完成 is not None else 1)),
            skip=(2,),
        )
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    if hide_decay:
        total_line = [
            "",
            "其它",
            "|",
            "",
            "",
            fmt(其它点数),
            fmt(其它点数变化),
            "",
            "",
        ]
        total_line = colorline(total_line, getcolor(其它点数), skip=(2,))
        table_lines.append(total_line)
    total_line = [
        "",
        "总数",
        "|",
        fmt(总用时),
        "",
        fmt(N.stats.Goldie点数),
        fmt(N.stats.Goldie点数 - P.stats.Goldie点数, pos=True),
        fmt(最大负载, p2=True),
        "",
    ]
    total_line = colorline(
        total_line,
        getcolor(N.stats.长期任务点数 - (0 if nstat1.进度 > 0 else 1)),
        skip=(2,),
    )
    table_lines.append(total_line)
    report = tabulate(table_lines, headers=table_headers, tablefmt="simple")
    return report
