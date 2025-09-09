from typing import TypeVar, Optional, Iterable, Union, Literal, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
from tabulate import tabulate, SEPARATING_LINE
import tabulate as Tabulate

from .models import AppendOnly, PickerModel
from .collect import State
from .statistic import StateStats, isdisabled, EmptyLongTaskStats, EmptyShortTaskStats


log = logging.getLogger(__name__)

Tabulate.PRESERVE_WHITESPACE = True


FmtT = TypeVar("FmtT", int, float, datetime, timedelta, str)


def fmt(
    x: FmtT,
    *,
    pos: bool = False,
    p2: bool = False,
) -> str:
    if isinstance(x, int):
        if pos and x != 0:
            return f"{x:+d}"
        else:
            return f"{x:d}"
    elif isinstance(x, float):
        if p2:
            if pos and x != 0.0:
                return f"{x:+.2f}"
            else:
                return f"{x:.2f}"
        else:
            if pos and x != 0.0:
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
            if pos and x != timedelta(0):
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
        elif v > timedelta(minutes=1):
            vstr = f"{v // timedelta(minutes=1)}m"
        else:
            vstr = "0 "
        return sign + vstr
    elif isinstance(x, str):
        return x
    else:
        raise TypeError("未知类型")


ColorMode = Literal["goldie", "shadowzero", "goldiechange", "highlightreach"]


def colorit(
    value: FmtT,
    *,
    colorpts: Optional[int] = None,
    colorchange: Optional[int] = None,
    greyzero: bool = False,
    grey: bool = False,
    blue: bool = False,
    red: bool = False,
) -> str:
    pstr = fmt(value)
    if colorpts is not None:
        color = goldie_color(colorpts)
        pstr = f"{ESC}[{color}m{pstr}{ESC}[0m"
    if colorchange is not None:
        color = goldie_change_color(colorchange)
        pstr = f"{ESC}[{color}m{pstr}{ESC}[0m"
    if greyzero:
        if isinstance(value, str):
            try:
                fv = float(value)
                if fv == 0.0:
                    pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
            except ValueError:
                pass
        elif value in {0, 0.0, timedelta(0)}:
            pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
    if grey:
        pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
    if blue:
        pstr = f"{ESC}[{BLUE}m{pstr}{ESC}[0m"
    if red:
        pstr = f"{ESC}[{RED}m{pstr}{ESC}[0m"
    return pstr


ESC = "\033"
RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
MAGENTA = "35"
CYAN = "36"
WHITE = "37"
ORANGE = "38;5;130"
DARKGREY = "90"
LONG_RUNNING = "●"
LONG_WAITING = "◯"
SHORT_RUNNING = "■"
SHORT_WAITING = "□"

goldie_thresholds = [-100, -50, 0, 50, 100]
goldie_levels = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE]


def goldie_color(goldie: int) -> str:
    for i, threshold in enumerate(goldie_thresholds):
        if goldie < threshold:
            return goldie_levels[i]
    return goldie_levels[-1]


goldie_change_thresholds = [-50, -20, 0, 1, 20, 50]
goldie_change_levels = [RED, ORANGE, YELLOW, DARKGREY, GREEN, CYAN, BLUE]


def goldie_change_color(goldie: int) -> str:
    for i, threshold in enumerate(goldie_change_thresholds):
        if goldie < threshold:
            return goldie_change_levels[i]
    return goldie_change_levels[-1]


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


def report_head(N: ReportData) -> str:
    report = f"blueberry - {N.time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"近期每日平均用时: {fmt(N.stats.总每日平均用时)}\n"
    report += f"建议每日用时: {fmt(N.stats.建议每日用时)} "
    report += f"(在 {fmt(N.stats.下一关键时间)} ({fmt(N.stats.下一关键时间 - N.time)})"
    report += f" 前完成 {fmt(N.stats.下一关键节点任务量时长)} 工作量)"
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
        "推荐时长",
        "完成",
        "剩余",
        "剩余时间",
        "预计用时",
        "日平均",
    ]
    table_colalign = [
        "left",
        "left",
        "left",  # "|"
        "decimal",
        "right",
        "decimal",
        "decimal",
        "right",
        "right",
        "right",
    ]
    推荐每日用时 = timedelta(0)
    总预计时间 = timedelta(0)
    table_lines: list[Union[Sequence[Optional[str]], str]] = []
    for task in prefer(N.state.长期任务.values(), N.state.选择排序偏好):
        tstat = N.stats.长期任务统计[task.名称]
        # 跳过完成0分项
        if tstat.进度 >= task.总数 and N.time >= task.最晚结束:
            continue
        # [None, "名称", "|", "点数", "推荐时长", "完成", "剩余", "剩余时间", "预计用时", "每日平均用时"]
        colorpts = tstat.点数 - (0 if tstat.进度 > 0 else 1)
        table_line = [
            colorit(
                LONG_RUNNING if tstat.进度 > 0 else LONG_WAITING, colorpts=colorpts
            ),
            colorit(task.标题, red=N.time >= task.最晚结束),
            "|",
            colorit(colorpts, colorpts=colorpts),
            colorit(tstat.推荐每日用时, greyzero=True),
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
        推荐每日用时 += tstat.推荐每日用时
        总预计时间 += tstat.预计需要时间
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        None,
        "总数",
        "|",
        colorit(N.stats.长期任务点数, colorpts=N.stats.长期任务点数),
        colorit(推荐每日用时, greyzero=True),
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
        "推荐时长",
        "用时",
        "预计时间",
        "剩余时间",
    ]
    table_colalign = [
        "left",
        "left",
        "left",  # "|"
        "decimal",
        "right",
        "right",
        "right",
        "right",
    ]
    推荐每日用时 = timedelta(0)
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
            colorit(colorpts, colorpts=colorpts),
            colorit(tstat.推荐每日用时, greyzero=True),
            colorit(tstat.用时, greyzero=True),
            colorit(tstat.预计需要时间, greyzero=True),
            fmt(task.最晚结束 - N.time),
        ]
        推荐每日用时 += tstat.推荐每日用时
        总用时 += tstat.用时
        总预计时间 += tstat.预计需要时间
        table_lines.append(table_line)
    table_lines.append(SEPARATING_LINE)
    total_line = [
        None,
        "总数",
        "|",
        colorit(N.stats.短期任务点数, colorpts=N.stats.短期任务点数),
        colorit(推荐每日用时, greyzero=True),
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
        "建议",
        "时长",
        "剩余时间",
    ]
    table_colalign = [
        "left",
        "left",
        "left",  # "|"
        "right",
        "decimal",
        "decimal",
        "decimal",
        "decimal",
        "right",
        "right",
    ]
    推荐每日用时 = timedelta(0)
    总用时 = timedelta(0)
    其它点数 = 0
    其它点数变化 = 0
    其它推荐每日用时 = timedelta(0)
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
        推荐每日用时 += nstat1.推荐每日用时
        if hide_decay and nstat1.用时 == pstat1.用时:
            其它点数 += nstat1.点数
            其它点数变化 += nstat1.点数 - pstat1.点数
            其它推荐每日用时 += nstat1.推荐每日用时
            continue
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]
        colorpts = nstat1.点数 - (0 if nstat1.进度 > 0 else 1)
        推荐完成 = nstat1.推荐每日用时 / timedelta(hours=1) * nstat1.速度
        time_reach_recommend = nstat1.用时 - pstat1.用时 >= nstat1.推荐每日用时
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
            colorit(nstat1.点数, colorpts=colorpts),
            colorit(nstat1.点数 - pstat1.点数, colorchange=nstat1.点数 - pstat1.点数),
            colorit(fmt(推荐完成, p2=True), greyzero=True),
            colorit(nstat1.推荐每日用时, greyzero=True),
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
        推荐每日用时 += nstat2.推荐每日用时
        if hide_decay and nstat2.用时 == pstat2.用时:
            其它点数 += nstat2.点数
            其它点数变化 += nstat2.点数 - pstat2.点数
            其它推荐每日用时 += nstat2.推荐每日用时
            continue
        # [None, "名称", "|", "用时", "完成", "点数", "变化", "建议", "时长", "剩余时间"]"]
        colorpts = nstat2.点数 - (
            0 if ntask2.完成 is not None and N.time >= ntask2.完成 else 1
        )
        finished = ntask2.完成 is not None and N.time >= ntask2.完成
        reach_recommend = finished or nstat2.推荐每日用时 == timedelta(0)
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
            colorit(nstat2.点数, colorpts=colorpts),
            colorit(
                fmt(nstat2.点数 - pstat2.点数, pos=True),
                colorchange=nstat2.点数 - pstat2.点数,
            ),
            None,
            colorit(nstat2.推荐每日用时, greyzero=True),
            colorit(
                ntask2.最晚结束 - N.time,
                grey=finished,
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
            colorit(其它点数, colorpts=其它点数),
            colorit(其它点数变化, colorchange=其它点数变化),
            None,
            colorit(其它推荐每日用时, greyzero=True),
            None,
        ]
        table_lines.append(total_line)
    total_line = [
        None,
        total_str,
        "|",
        colorit(总用时, greyzero=True),
        None,
        colorit(N.stats.Goldie点数, colorpts=N.stats.Goldie点数),
        colorit(
            fmt(N.stats.Goldie点数 - P.stats.Goldie点数, pos=True),
            colorchange=N.stats.Goldie点数 - P.stats.Goldie点数,
        ),
        None,
        colorit(推荐每日用时, greyzero=True),
        None,
    ]
    table_lines.append(total_line)
    report = tabulate(
        table_lines, headers=table_headers, colalign=table_colalign, tablefmt="simple"
    )
    return report
