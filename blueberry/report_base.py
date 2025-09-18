from typing import TypeVar
from dataclasses import dataclass
from datetime import datetime
import logging

import wcwidth  # type: ignore

# 用于tabulate的宽度计算
import tabulate as Tabulate

from .models import AppendOnly
from .collect import State
from .statistic import StateStats
from .planner import Plan
from .fmtcolor import fmt

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
