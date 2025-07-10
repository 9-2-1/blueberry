from typing import TypeVar, overload
from dataclasses import dataclass
from datetime import datetime, timedelta
from textwrap import indent

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
from tabulate import tabulate

from bb_collect import State
from bb_statistic import StateStats

FmtT = TypeVar("FmtT", int, float, datetime, timedelta)


@overload
def fmt(x: FmtT, *, pos: bool = False, timesign: bool = True) -> str: ...


@overload
def fmt(
    x: FmtT,
    y: FmtT,
    *,
    pos: bool = False,
    diff: bool = True,
    timesign: bool = True,
) -> str: ...


def fmt(
    x: FmtT,
    y: FmtT | None = None,
    *,
    pos: bool = False,
    diff: bool = True,
    timesign: bool = True,
) -> str:
    if y is None:
        if isinstance(x, int):
            if pos:
                return f"{x:+d}"
            else:
                return f"{x:d}"
        elif isinstance(x, float):
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
                    if timesign:
                        sign = "后"
                    else:
                        sign = "+"
                v = x
            else:
                if pos:
                    if timesign:
                        sign = "前"
                    else:
                        sign = "-"
                v = -x
            if v > timedelta(days=7):
                vstr = f"{v // timedelta(days=1)}天"
            elif v > timedelta(days=1):
                vstr = f"{v // timedelta(days=1)}天{v // timedelta(hours=1) % 24}时"
            elif v > timedelta(hours=1):
                vstr = f"{v // timedelta(hours=1)}时{v // timedelta(minutes=1) % 60}分"
            else:
                vstr = f"{v.seconds // 60}分钟"
            return vstr + sign if timesign else sign + vstr
        else:
            raise TypeError("未知类型")
    else:
        if diff:
            if isinstance(y, timedelta):
                return f"{fmt(y, pos=pos, timesign=timesign)}({fmt(y - x, pos=True, timesign=False)})"
            else:
                return f"{fmt(y, pos=pos, timesign=timesign)}({fmt(y - x, pos=True)})"
        else:
            return f"{fmt(x, pos=pos, timesign=timesign)}→{fmt(y, pos=pos, timesign=timesign)}"


@dataclass
class ReportData:
    time: datetime
    state: State
    stats: StateStats


def report_head(
    N: ReportData, P: ReportData | None, *, short: bool = False, diff: bool = True
) -> str:
    report = "blueberry 报告\n"
    if P is not None:
        report += f"时间:{fmt(P.time, N.time, diff=False)}\n"
        if short:
            # 短格式
            report += f"点数:{fmt(P.stats.Goldie点数, N.stats.Goldie点数, diff=diff)} "
            report += f"({fmt(P.stats.任务点数, N.stats.任务点数, diff=diff)},"
            report += f"{fmt(P.stats.状态点数, N.stats.状态点数, diff=diff)},"
            report += f"{fmt(P.stats.其他任务点数, N.stats.其他任务点数, diff=diff)})"
            report += (
                f" 日均:{fmt(P.stats.总每日用时, N.stats.总每日用时, diff=diff)}\n"
            )
        else:
            # 普通格式
            report += (
                f"Goldie点数:{fmt(P.stats.Goldie点数, N.stats.Goldie点数, diff=diff)} "
            )
            report += f"(任务:{fmt(P.stats.任务点数, N.stats.任务点数, diff=diff)}"
            report += f" 状态:{fmt(P.stats.状态点数, N.stats.状态点数, diff=diff)}"
            report += (
                f" 其他:{fmt(P.stats.其他任务点数, N.stats.其他任务点数, diff=diff)})\n"
            )
            report += f"近期平均每日用时:{fmt(P.stats.总每日用时, N.stats.总每日用时, diff=diff)}\n"
    else:
        report += f"时间:{fmt(N.time)}\n"
        if short:
            # 短对比格式
            report += f"点数:{fmt(N.stats.Goldie点数)} "
            report += f"({fmt(N.stats.任务点数)},"
            report += f"{fmt(N.stats.状态点数)},"
            report += f"{fmt(N.stats.其他任务点数)})"
            report += f" 日均:{fmt(N.stats.总每日用时)}\n"
        else:
            # 普通对比格式
            report += f"Goldie点数:{fmt(N.stats.Goldie点数)} "
            report += f"(任务:{fmt(N.stats.任务点数)}"
            report += f" 状态:{fmt(N.stats.状态点数)}"
            report += f" 其他:{fmt(N.stats.其他任务点数)})\n"
            report += f"近期平均每日用时:{fmt(N.stats.总每日用时)}\n"
    return report + "\n"


def report_main_tasks(
    N: ReportData,
    P: ReportData | None,
    *,
    short: bool = False,
    daily: bool = False,
    diff: bool = True,
    change_only: bool = False,
    upcoming: float | None = None,
    verbose: bool = False,
) -> str:
    fliter_upcoming: list[str] = []
    fliter_running: list[str] = []  # 包括超时任务
    fliter_running_change: list[str] = []
    fliter_done: list[str] = []
    fliter_done_end_change: list[str] = []
    fliter_done_end: list[str] = []
    for task in N.state.任务.values():
        tstat = N.stats.任务统计[task.名称]
        if task.总数 is not None and tstat.进度 >= task.总数:
            if N.time >= task.结束:
                fliter_done_end.append(task.名称)
                if P is not None and P.time <= task.结束:
                    fliter_done_end_change.append(task.名称)
            else:
                fliter_done.append(task.名称)
        elif tstat.进度 != 0 or N.time >= task.开始:
            fliter_running.append(task.名称)
            if P is not None:
                ptask = P.state.任务.get(task.名称)
                if ptask != task or P.time < task.开始:
                    fliter_running_change.append(task.名称)
                else:
                    pstat = P.stats.任务统计.get(task.名称)
                    if pstat is None or pstat.进度 != tstat.进度:
                        fliter_running_change.append(task.名称)
        else:
            # N.time < task.开始
            if upcoming is None or task.开始 < N.time + timedelta(days=upcoming):
                fliter_upcoming.append(task.名称)

    def report_main_tasks_flitered(
        title: str, task_names: list[str], *, is_upcoming: bool = False
    ) -> tuple[str, list[list[str]]]:
        if not task_names:
            return "", []
        report = ""
        report += f"{title}:\n"
        table_line: list[list[str]] = []
        for task_name in task_names:
            verbose_str = ""
            task = N.state.任务[task_name]
            tstat = N.stats.任务统计[task_name]
            t点数 = tstat.点数 if tstat.点数 is not None else 0
            statuses = []
            verbose_str += f"  | 开始:{fmt(N.time, task.开始, diff=True)} 结束:{fmt(N.time, task.结束, diff=True)}\n"
            if tstat.速度 is not None:
                verbose_str += f"  | 速度:{fmt(tstat.速度.速度)}/小时 每日平均用时:{fmt(tstat.速度.每日用时)}\n"
            if tstat.预计 is not None:
                verbose_str += f"  | 预计完成时间:{fmt(tstat.预计.预计完成时间)} 预计可用时间:{fmt(tstat.预计.预计可用时间)} 差距:{fmt(tstat.预计.差距)}\n"
            if P is not None:
                ptask = P.state.任务.get(task_name)
                pstat = P.stats.任务统计.get(task_name)
                p进度 = pstat.进度 if pstat is not None else 0
                p用时 = pstat.用时 if pstat is not None else timedelta(0)
                p点数 = (
                    pstat.点数 if pstat is not None and pstat.点数 is not None else 0
                )
                point_str = f"{fmt(p点数, t点数, diff=diff)}"
                if ptask != task:
                    statuses.append(f"更新于{fmt(N.time - task.时间)}前")
                if task.总数 is not None:
                    statuses.append(
                        f"{fmt(p进度, tstat.进度, diff=diff)}/{fmt(task.总数)} ({tstat.进度/task.总数:.0%})"
                    )
                else:
                    statuses.append(f"{fmt(p进度, tstat.进度, diff=diff)}")
                statuses.append(f"用时{fmt(tstat.用时 - p用时)}")
            else:
                point_str = f"{fmt(t点数)}"
                if task.总数 is not None:
                    statuses.append(
                        f"{fmt(tstat.进度)}/{fmt(task.总数)} ({tstat.进度/task.总数:.0%})"
                    )
                else:
                    statuses.append(f"{fmt(tstat.进度)}")
            if is_upcoming:
                statuses.append(f"{fmt(task.开始 - N.time)}后开始")
            elif N.time >= task.结束:
                statuses.append(f"过期{fmt(N.time - task.结束)}")
            else:
                statuses.append(f"剩余{fmt(task.结束 - N.time)}")
            table_line.append([title, point_str, task.标题, *statuses])
            if statuses:
                status_str = "(" + ",".join(statuses) + ")"
            else:
                status_str = ""
            report += f"- [{point_str}] {task.标题} {status_str}\n"
            if verbose:
                report += verbose_str
            if task.描述 is not None:
                report += indent(task.描述, "  ")
            report += "\n\n"
        return report, table_line

    report_upcoming, table_upcoming = report_main_tasks_flitered(
        "即将开始", fliter_upcoming, is_upcoming=True
    )
    report_running, table_running = report_main_tasks_flitered("进行中", fliter_running)
    report_running_change, table_running_change = report_main_tasks_flitered(
        "进行中", fliter_running_change
    )
    report_done_end, table_done_end = report_main_tasks_flitered(
        "已结束", fliter_done_end
    )
    report_done_end_change, table_done_end_change = report_main_tasks_flitered(
        "已完成", fliter_done_end_change
    )

    report = ""
    if short:
        table_line: list[list[str]] = []
        if change_only:
            table_line.extend(table_running_change)
            table_line.extend(table_done_end_change)
        else:
            table_line.extend(table_running)
            table_line.extend(table_upcoming)
            table_line.extend(table_done_end)
            table_line.extend(table_done_end_change)
        report += tabulate(table_line, tablefmt="plain") + "\n"
    else:
        if change_only:
            report += report_running_change
            report += report_done_end_change
        else:
            report += report_running
            report += report_upcoming
            report += report_done_end
            report += report_done_end_change
    return report
