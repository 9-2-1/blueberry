from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from .picker import isdisabled
from .statistic import StateStats, EmptyLongTaskStats, EmptyShortTaskStats
from .workdays import workdays
from .collect import State
from .models import WorktimeModel

log = logging.getLogger(__name__)


@dataclass
class PlanData:
    time: datetime
    state: State
    stats: StateStats


@dataclass
class Plan:
    建议用时: dict[str, timedelta]
    总建议用时: timedelta
    下一关键时间: datetime
    下一关键节点任务量时长: timedelta
    保持用时: timedelta


@dataclass
class TaskItem:
    name: str
    worktime: timedelta
    endtime: datetime
    keep: bool
    skipped: bool


def planner(
    N: PlanData, P: PlanData, end_time: datetime, worktime: list[WorktimeModel]
) -> Plan:
    # 推荐时长
    建议用时: dict[str, timedelta] = {}
    collection: list[TaskItem] = []
    perioddays = workdays(P.time, end_time, worktime)
    for task1 in N.state.长期任务.values():
        if isdisabled(task1.名称, N.state.选择排序偏好):
            continue
        tstat1 = N.stats.长期任务统计[task1.名称]
        pstat1 = P.stats.长期任务统计.get(task1.名称, None)
        if pstat1 is None:
            pstat1 = EmptyLongTaskStats(task1)
        if pstat1.进度 >= task1.总数:
            continue
        预计需要时间 = timedelta(minutes=20)
        if tstat1.进度 > 0:
            预计需要时间 = timedelta(hours=1) * (task1.总数 - pstat1.进度) / tstat1.速度
        collection.append(
            TaskItem(
                name=task1.名称,
                worktime=预计需要时间,
                endtime=task1.最晚结束 if tstat1.进度 > 0 else task1.最晚开始,
                keep=task1.保持安排 == "+",
                skipped=False,
            )
        )
    for task2 in N.state.短期任务.values():
        if isdisabled(task2.名称, N.state.选择排序偏好):
            continue
        skip_period = False
        if workdays(end_time, task2.最早开始, worktime) >= 0:
            log.info(f"task {task2.名称} is skipped")
            skip_period = True
        if task2.完成 is not None and P.time >= task2.完成:
            continue
        if task2.预计用时 == timedelta(0):
            continue
        tstat2 = P.stats.短期任务统计.get(task2.名称, None)
        if tstat2 is None:
            tstat2 = EmptyShortTaskStats(task2)
        collection.append(
            TaskItem(
                name=task2.名称,
                worktime=tstat2.预计需要时间,
                endtime=task2.最晚结束,
                keep=False,
                skipped=skip_period,
            )
        )
    # 按照截止日期排序
    collection.sort(key=lambda x: x.endtime)
    tot_work = timedelta(0)
    tpd_keep = timedelta(0)
    tpd_max = timedelta(0)
    tpd_max_i = 0
    tpd_max_time = P.time
    tpd_max_work = timedelta(0)
    for i, item in enumerate(collection):
        item_end_time = max(item.endtime, end_time)
        if item.keep:
            if item.endtime < end_time:
                tpd_keep_time = item.worktime
            else:
                tpd_keep_time = item.worktime * (
                    workdays(P.time, end_time, worktime)
                    / workdays(P.time, item.endtime, worktime)
                )
            建议用时[item.name] = tpd_keep_time
            tpd_keep += tpd_keep_time
            continue
        tot_work += item.worktime
        tot_worktime = workdays(P.time, item_end_time, worktime)
        tpd = tot_work / tot_worktime
        if tpd > tpd_max:
            tpd_max_i = i + 1
            tpd_max = tpd
            tpd_max_time = item_end_time
            tpd_max_work = tot_work
    # 对tpd_max_i（关键点）之前的任务全部合理调度
    tot_quota = timedelta(0)  # 当前任务截止时间前可用时间（包含已分配和未分配时间）
    tot_alloc = timedelta(0)  # 总时间已分配
    period_quota = tpd_max * perioddays  # 总用时
    period_alloc = timedelta(0)  # 已分配
    for item in collection[:tpd_max_i]:
        # floating point error
        if item.keep:
            continue
        item_end_time = max(item.endtime, end_time)
        tot_quota = tpd_max_work * (
            workdays(P.time, item_end_time, worktime)
            / workdays(P.time, tpd_max_time, worktime)
        )
        log.debug(
            f"workt: {item.worktime}, into {tot_quota - tot_alloc}, day {period_quota - period_alloc}"
        )
        # float point error tolerance
        if tot_alloc > tot_quota:
            continue
        if period_alloc > period_quota:
            continue
        period_to_alloc = (period_quota - period_alloc) * (
            item.worktime / (tot_quota - tot_alloc)
        )
        if period_to_alloc > item.worktime:
            period_to_alloc = item.worktime
        tot_alloc += item.worktime
        if item.skipped:
            period_to_alloc = timedelta(0)
        建议用时[item.name] = period_to_alloc
        log.debug(period_to_alloc)
        period_alloc += period_to_alloc
    log.debug(f"allocated in period: {period_alloc}, {period_quota}")
    log.debug(f"allocated total: {tot_alloc}, {tot_quota}")
    return Plan(
        建议用时=建议用时,
        总建议用时=tpd_max + tpd_keep,
        下一关键时间=tpd_max_time,
        下一关键节点任务量时长=tpd_max_work,
        保持用时=tpd_keep,
    )
