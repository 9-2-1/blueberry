from typing import TypeVar, overload, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from textwrap import indent

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
from tabulate import tabulate

from .config import 推荐用时
from .models import HintModel
from .collect import State
from .statistic import StateStats

FmtT = TypeVar("FmtT", int, float, datetime, timedelta)


@overload
def fmt(x: FmtT, *, pos: bool = False, timesign: bool = True) -> str: ...


@overload
def fmt(
    x: FmtT,
    y: FmtT,
    *,
    pos: bool = False,
    olddiff: bool = True,
    timesign: bool = True,
) -> str: ...


def fmt(
    x: FmtT,
    y: Optional[FmtT] = None,
    *,
    pos: bool = False,
    olddiff: bool = True,
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
        if olddiff:
            return f"{fmt(x, pos=pos, timesign=timesign)}→{fmt(y, pos=pos, timesign=timesign)}"
        else:
            if isinstance(y, timedelta):
                return f"{fmt(y, pos=pos, timesign=timesign)}({fmt(y - x, pos=True, timesign=False)})"
            else:
                return f"{fmt(y, pos=pos, timesign=timesign)}({fmt(y - x, pos=True)})"


@dataclass
class ReportData:
    time: datetime
    state: State
    stats: StateStats


def report_head(
    N: ReportData,
    P: Optional[ReportData],
    Y: Optional[ReportData] = None,
    *,
    olddiff: bool = True,
) -> str:
    report = ""
    if P is not None:
        report += f"时间:{fmt(P.time, N.time, olddiff=True)}\n"
        # 普通格式
        report += f"Goldie点数:{fmt(P.stats.Goldie点数, N.stats.Goldie点数, olddiff=olddiff)} "
        if Y is not None:
            report += f"今日:{fmt(N.stats.Goldie点数 - Y.stats.Goldie点数, pos=True)} "
        report += f"(任务:{fmt(P.stats.任务点数, N.stats.任务点数, olddiff=olddiff, pos=True)}"
        report += f" 状态:{fmt(P.stats.状态点数, N.stats.状态点数, olddiff=olddiff, pos=True)}"
        report += f" 其他:{fmt(P.stats.其他任务点数, N.stats.其他任务点数, olddiff=olddiff, pos=True)})\n"
        report += f"近期平均每日用时:{fmt(P.stats.总每日用时, N.stats.总每日用时, olddiff=olddiff)} (推荐时长的 {N.stats.总每日用时 / 推荐用时:.0%})"
    else:
        report += f"时间:{fmt(N.time)}\n"
        # 普通对比格式
        report += f"Goldie点数:{fmt(N.stats.Goldie点数)} "
        if Y is not None:
            report += f"今日:{fmt(N.stats.Goldie点数 - Y.stats.Goldie点数, pos=True)} "
        report += f"(任务:{fmt(N.stats.任务点数)}"
        report += f" 状态:{fmt(N.stats.状态点数)}"
        report += f" 其他:{fmt(N.stats.其他任务点数)})\n"
        report += f"近期平均每日用时:{fmt(N.stats.总每日用时)} (推荐时长的 {N.stats.总每日用时 / 推荐用时:.0%})"
    return report


def report_worktime(N: ReportData) -> str:
    worktime = N.state.工作时段
    if not worktime:
        return "未设置工作时段。"
    report = "工作时段:"
    for workt in worktime:
        report += f" {workt.开始.hour:02d}:{workt.开始.minute:02d}→{workt.结束.hour:02d}:{workt.结束.minute:02d}"
    return report.strip()


def report_main_tasks(
    N: ReportData,
    P: Optional[ReportData],
    Y: Optional[ReportData] = None,
    *,
    short: bool = False,
    olddiff: bool = True,
    change_only: bool = False,
    minor_change_only: bool = False,
    upcoming: Optional[float] = None,
    verbose: bool = False,
) -> str:
    category_upcoming: list[str] = []
    category_running: list[str] = []  # 包括超时任务
    category_done: list[str] = []
    category_expire: list[str] = []
    for task in N.state.任务.values():
        # change_only category
        tstat = N.stats.任务统计[task.名称]
        changed = False
        minor_changed = False
        if P is not None:
            ptask = P.state.任务.get(task.名称)
            if ptask != task:
                changed = True
            else:
                pstat = P.stats.任务统计[task.名称]
                if pstat.进度 != tstat.进度:
                    minor_changed = True
                elif pstat.用时 != tstat.用时:
                    minor_changed = True
                elif P.time < task.开始 <= N.time:
                    minor_changed = True
                elif P.time < task.结束 <= N.time:
                    minor_changed = True
        category__ = None
        if task.总数 is not None and tstat.进度 >= task.总数:
            if N.time >= task.结束:
                if changed:
                    category__ = category_expire
            else:
                category__ = category_done
        elif tstat.进度 != 0 or N.time >= task.开始:
            category__ = category_running
        elif upcoming is None or task.开始 < N.time + timedelta(days=upcoming):
            category__ = category_upcoming
        if category__ is not None:
            if (
                (change_only and changed)
                or (minor_change_only and minor_changed)
                or not (change_only or minor_change_only)
            ):
                category__.append(task.名称)

    def report_main_tasks_category(
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
            if P is not None:
                ptask = P.state.任务.get(task_name)
                pstat = P.stats.任务统计.get(task_name)
                p进度 = pstat.进度 if pstat is not None else 0
                p用时 = pstat.用时 if pstat is not None else timedelta(0)
                p点数 = (
                    pstat.点数 if pstat is not None and pstat.点数 is not None else 0
                )
                if ptask != task:
                    verbose_str += f"  | 更新于{fmt(N.time - task.时间)}前\n"
                point_str = f"点数{fmt(p点数, t点数, olddiff=olddiff, pos=True)}"
                if task.总数 is not None:
                    statuses.append(
                        f"完成{fmt(p进度, tstat.进度, olddiff=olddiff)}/{fmt(task.总数)} ({tstat.进度/task.总数:.0%})"
                    )
                else:
                    statuses.append(f"完成{fmt(p进度, tstat.进度, olddiff=olddiff)}")
                if Y is None or Y.time != P.time:
                    # 如果不排除的话会有两列重复
                    statuses.append(
                        f"用时{fmt(tstat.用时 - p用时, timesign=False, pos=True)}"
                    )
            else:
                point_str = f"点数{fmt(t点数, pos=True)}"
                if task.总数 is not None:
                    statuses.append(
                        f"完成{fmt(tstat.进度)}/{fmt(task.总数)} ({tstat.进度/task.总数:.0%})"
                    )
                else:
                    statuses.append(f"完成{fmt(tstat.进度)}")
            # 今日...
            if Y is not None:
                ystat = Y.stats.任务统计.get(task_name)
                y进度 = ystat.进度 if ystat is not None else 0
                y用时 = ystat.用时 if ystat is not None else timedelta(0)
                y点数 = (
                    ystat.点数 if ystat is not None and ystat.点数 is not None else 0
                )
                statuses.append(f"今日:点数{fmt(t点数 - y点数, pos=True)}")
                statuses.append(f"完成{fmt(tstat.进度 - y进度)}")
                statuses.append(f"用时{fmt(tstat.用时 - y用时, timesign=False)}")

            verbose_str += f"  | 开始:{fmt(N.time, task.开始, olddiff=False)} 结束:{fmt(N.time, task.结束, olddiff=False)}\n"
            if tstat.速度 is not None:
                verbose_str += f"  | 近期完成:{fmt(tstat.速度.tot_progress)} 近期用时:{fmt(tstat.速度.tot_time)} 近期工作天数:{fmt(tstat.速度.tot_dayspan)}天\n"
                verbose_str += f"  | 近期速度:{fmt(tstat.速度.速度)}/小时 近期每日平均用时:{fmt(tstat.速度.每日用时)}\n"
            if tstat.预计 is not None:
                verbose_str += f"  | 预计完成时间:{fmt(tstat.预计.预计完成时间)} 预计可用时间:{fmt(tstat.预计.预计可用时间)} 差距:{fmt(tstat.预计.差距, timesign=False, pos=True)}\n"
            if is_upcoming:
                statuses.append(f"{fmt(task.开始 - N.time, pos=True)}开始")
            else:
                statuses.append(f"{fmt(task.结束 - N.time, pos=True)}到期")
            statuses.append(tstat.进度描述 if tstat.进度描述 is not None else "")
            table_line.append([f"[{point_str}]", title, task.标题, *statuses])
            statuses = [x for x in statuses if x != ""]
            if statuses:
                status_str = "(" + ", ".join(statuses) + ")"
            else:
                status_str = ""
            report += f"- [{point_str}] {task.标题} {status_str}\n"
            if verbose:
                report += verbose_str
            if task.描述 is not None:
                report += indent(task.描述, "  ")
            report += "\n\n"
        return report, table_line

    report_upcoming, table_upcoming = report_main_tasks_category(
        "即将开始", category_upcoming, is_upcoming=True
    )
    report_running, table_running = report_main_tasks_category(
        "进行中", category_running
    )
    report_done, table_done = report_main_tasks_category("已完成", category_done)
    report_expire, table_expire = report_main_tasks_category("已结束", category_expire)

    report = ""
    if short:
        table_line: list[list[str]] = []
        table_line.extend(table_running)
        table_line.extend(table_upcoming)
        table_line.extend(table_done)
        table_line.extend(table_expire)
        report += tabulate(table_line, tablefmt="plain") + "\n\n"
    else:
        report += report_running
        report += report_upcoming
        report += report_done
        report += report_expire
    return report.strip()


def report_daily_time(
    N: ReportData,
    P: Optional[ReportData],
    Y: Optional[ReportData],
    *,
    olddiff: bool = False,
) -> str:
    n今日用时 = timedelta(0)
    p今日用时 = timedelta(0)
    if Y is not None:
        if P is not None and N.time.date() != P.time.date():
            raise ValueError("不能对比不在同一天的每日进度")
        for task in N.state.任务.values():
            tstat = N.stats.任务统计[task.名称]
            ystat = Y.stats.任务统计.get(task.名称)
            y用时 = ystat.用时 if ystat is not None else timedelta(0)
            n今日用时 += tstat.用时 - y用时
            if P is not None:
                pstat = P.stats.任务统计.get(task.名称)
                p用时 = pstat.用时 if pstat is not None else timedelta(0)
                p今日用时 += p用时 - y用时
    if Y is not None:
        if P is not None and P.time != Y.time:
            report = f"今日用时: {fmt(p今日用时, n今日用时, olddiff=olddiff)} (推荐时长的 {n今日用时 / 推荐用时:.0%})"
        else:
            report = (
                f"今日用时: {fmt(n今日用时)} (推荐时长的 {n今日用时 / 推荐用时:.0%})"
            )
    return report.strip()


def report_todo_tasks(
    N: ReportData,
    P: Optional[ReportData],
    *,
    short: bool = False,
    change_only: bool = False,
    minor_change_only: bool = False,
    upcoming: Optional[float] = None,
    verbose: bool = False,
    olddiff: bool = False,
) -> str:
    category_upcoming: list[str] = []
    category_running: list[str] = []  # 包括超时任务
    category_done: list[str] = []
    category_expire: list[str] = []
    category_cancel: list[str] = []
    for todo in N.state.待办事项.values():
        changed = False
        minor_changed = False
        if P is not None:
            ptodo = P.state.待办事项.get(todo.名称)
            if ptodo != todo:
                changed = True
            elif todo.开始 is not None and P.time < todo.开始 <= N.time:
                minor_changed = True
            elif todo.结束 is not None and P.time < todo.结束 <= N.time:
                minor_changed = True
            elif (todo.名称 in N.stats.其他任务生效) != (
                todo.名称 in P.stats.其他任务生效
            ):
                minor_changed = True
        category__ = None
        if todo.标记 is None:
            if P is not None:
                if changed:
                    category__ = category_cancel
        elif todo.名称 in N.stats.其他任务生效:
            category__ = category_done
        elif todo.完成 is not None:
            if changed or minor_changed:
                category__ = category_expire
        elif todo.开始 is None or N.time >= todo.开始:
            category__ = category_running
        elif upcoming is None or (
            todo.开始 is not None and todo.开始 < N.time + timedelta(days=upcoming)
        ):
            category__ = category_upcoming
        if category__ is not None:
            if (
                (change_only and changed)
                or (minor_change_only and minor_changed)
                or not (change_only or minor_change_only)
            ):
                category__.append(todo.名称)

    def report_todo_tasks_category(
        title: str, todo_names: list[str], *, is_finished: bool = False
    ) -> tuple[str, list[list[str]]]:
        if not todo_names:
            return "", []
        report = ""
        report += f"{title}:\n"
        table_line: list[list[str]] = []
        for todo_name in todo_names:
            verbose_str = ""
            todo = N.state.待办事项[todo_name]
            t点数 = todo.点数
            statuses = []
            if P is not None:
                ptodo = P.state.待办事项.get(todo_name)
                if ptodo != todo:
                    verbose_str += f"  | 更新于{fmt(N.time - todo.时间)}前\n"
                p点数 = ptodo.点数 if ptodo is not None else 0
                if p点数 != t点数:
                    point_str = f"点数{fmt(p点数, t点数, olddiff=olddiff, pos=True)}"
                else:
                    point_str = f"点数{fmt(t点数, pos=True)}"
            else:
                point_str = f"点数{fmt(t点数, pos=True)}"
            if todo.标记 == "+":
                mode = "可选"
            elif todo.标记 == "-":
                mode = "等待"
            elif todo.标记 == "*":
                mode = "重要"
            else:
                mode = "取消"
            if not is_finished:
                point_str = f"预计{point_str}"
            if todo.完成 is not None and N.time >= todo.完成:
                statuses.append(f"{fmt(todo.完成 - N.time, pos=True)}完成")
            elif todo.开始 is not None and N.time < todo.开始:
                statuses.append(f"{fmt(todo.开始 - N.time, pos=True)}开始")
            elif todo.结束 is not None:
                statuses.append(f"{fmt(todo.结束 - N.time, pos=True)}到期")
            else:
                statuses.append("")
            if todo.开始 is not None or todo.结束 is not None or todo.完成 is not None:
                verbose_str += f"  |"
                if todo.开始 is not None:
                    verbose_str += f" 开始:{fmt(N.time, todo.开始, olddiff=False)}"
                if todo.结束 is not None:
                    verbose_str += f" 结束:{fmt(N.time, todo.结束, olddiff=False)}"
                if todo.完成 is not None:
                    verbose_str += f" 完成:{fmt(N.time, todo.完成, olddiff=False)}"
                verbose_str += "\n"
            table_line.append([f"[{point_str}]", title, mode, todo.标题, *statuses])
            statuses = [x for x in statuses if x != ""]
            if statuses:
                status_str = "(" + ", ".join(statuses) + ")"
            else:
                status_str = ""
            report += f"- [{point_str}] {todo.标题} {status_str}\n"
            if verbose:
                report += verbose_str
            if todo.描述 is not None:
                report += indent(todo.描述, "  ")
            report += "\n\n"
        return report, table_line

    report_upcoming, table_upcoming = report_todo_tasks_category(
        "即将开始", category_upcoming
    )
    report_running, table_running = report_todo_tasks_category(
        "进行中", category_running
    )
    report_done, table_done = report_todo_tasks_category(
        "已完成", category_done, is_finished=True
    )
    report_cancel, table_cancel = report_todo_tasks_category("已取消", category_cancel)
    report_expire, table_expire = report_todo_tasks_category(
        "已失效", category_expire, is_finished=True
    )

    report = ""
    if short:
        table_line: list[list[str]] = []
        table_line.extend(table_running)
        table_line.extend(table_upcoming)
        table_line.extend(table_done)
        table_line.extend(table_cancel)
        table_line.extend(table_expire)
        report += tabulate(table_line, tablefmt="plain") + "\n\n"
    else:
        report += report_running
        report += report_upcoming
        report += report_done
        report += report_cancel
        report += report_expire
    return report.strip()


def report_statuses(
    N: ReportData,
    P: Optional[ReportData],
    *,
    short: bool = False,
    change_only: bool = False,
    minor_change_only: bool = False,
    upcoming: Optional[float] = None,
    verbose: bool = False,
    olddiff: bool = False,
) -> str:
    category_upcoming: list[str] = []
    category_active: list[str] = []
    category_expire: list[str] = []
    for status in N.state.状态.values():
        changed = False
        minor_changed = False
        if P is not None:
            pstatus = P.state.状态.get(status.名称)
            if pstatus != status:
                minor_changed = True
            elif status.开始 is not None and P.time < status.开始 <= N.time:
                minor_changed = True
            elif status.结束 is not None and P.time < status.结束 <= N.time:
                minor_changed = True
        category__ = None
        if status.点数 is None or (status.结束 is not None and N.time >= status.结束):
            if changed or minor_changed:
                category__ = category_expire
        elif status.开始 is None or N.time >= status.开始:
            category__ = category_active
        elif upcoming is None or (
            status.开始 is not None and status.开始 < N.time + timedelta(days=upcoming)
        ):
            category__ = category_upcoming
        if category__ is not None:
            if (
                (change_only and changed)
                or (minor_change_only and minor_changed)
                or not (change_only or minor_change_only)
            ):
                category__.append(status.名称)

    def report_statuses_category(
        title: str, status_names: list[str]
    ) -> tuple[str, list[list[str]]]:
        if not status_names:
            return "", []
        report = ""
        report += f"{title}:\n"
        table_line: list[list[str]] = []
        for status_name in status_names:
            verbose_str = ""
            status = N.state.状态[status_name]
            t点数 = status.点数 if status.点数 is not None else 0
            statuses = []
            p点数 = t点数
            if P is not None:
                p点数 = 0
                pstatus = P.state.状态.get(status_name)
                if pstatus != status:
                    verbose_str += f"  | 更新于{fmt(N.time - status.时间)}前\n"
                if pstatus is not None and pstatus.点数 is not None:
                    p点数 = pstatus.点数
            if p点数 != t点数:
                point_str = f"点数{fmt(p点数, t点数, olddiff=olddiff, pos=True)}"
            else:
                point_str = f"点数{fmt(t点数, pos=True)}"
            if status.开始 is not None and N.time < status.开始:
                statuses.append(f"{fmt(status.开始 - N.time, pos=True)}开始")
            elif status.结束 is not None:
                statuses.append(f"{fmt(status.结束 - N.time, pos=True)}结束")
            else:
                statuses.append("")
            if status.开始 is not None or status.结束 is not None:
                verbose_str += f"  |"
                if status.开始 is not None:
                    verbose_str += f" 开始:{fmt(N.time, status.开始, olddiff=False)}"
                if status.结束 is not None:
                    verbose_str += f" 结束:{fmt(N.time, status.结束, olddiff=False)}"
                verbose_str += "\n"
            table_line.append([f"[{point_str}]", title, status.标题, *statuses])
            statuses = [x for x in statuses if x != ""]
            if statuses:
                status_str = "(" + ", ".join(statuses) + ")"
            else:
                status_str = ""
            report += f"- [{point_str}] {status.标题} {status_str}\n"
            if verbose:
                report += verbose_str
            if status.描述 is not None:
                report += indent(status.描述, "  ")
            report += "\n\n"
        return report, table_line

    report_upcoming, table_upcoming = report_statuses_category(
        "即将开始", category_upcoming
    )
    report_active, table_active = report_statuses_category("生效中", category_active)
    report_expire, table_expire = report_statuses_category("已失效", category_expire)

    report = ""
    if short:
        table_line: list[list[str]] = []
        table_line.extend(table_active)
        table_line.extend(table_upcoming)
        table_line.extend(table_expire)
        report += tabulate(table_line, tablefmt="plain")
    else:
        report += report_active
        report += report_upcoming
        report += report_expire
    return report.strip()


def report_hints(
    N: ReportData,
    P: Optional[ReportData],
    *,
    change_only: bool = False,
    verbose: bool = False,
) -> str:
    category_hints: list[HintModel] = []

    MIN_HINTS = 5
    MIN_TIME = timedelta(days=1)
    counts = 0
    for hints in reversed(N.state.提示):
        changed = False
        if P is not None:
            if hints.时间 and P.time < hints.时间 <= N.time:
                changed = True
        if (change_only and changed) or not change_only:
            if verbose or hints.时间 >= N.time - MIN_TIME or counts < MIN_HINTS:
                counts += 1
                category_hints.append(hints)

    def report_hints_category(hints: list[HintModel]) -> str:
        if not hints:
            return ""
        report = ""
        for hint in hints:
            report += f"- {hint.标题} ({fmt(N.time, hint.时间, olddiff=False)})\n"
            if hint.描述 is not None:
                report += indent(hint.描述, "  ")
            report += "\n\n"
        return report

    report = report_hints_category(category_hints)
    return report.strip()
