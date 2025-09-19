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


def planner(
    N: PlanData,
    P: PlanData,
    end_time: datetime,
    worktime: list[WorktimeModel],
) -> Plan:
    # 推荐时长
    tpd_keep = timedelta(0)
    建议用时: dict[str, timedelta] = {}
    collection: list[tuple[timedelta, datetime, bool, str]] = []
    perioddays = workdays(P.time, end_time, worktime)
    for task1 in N.state.长期任务.values():
        if isdisabled(task1.名称, N.state.选择排序偏好):
            continue
        tstat1 = P.stats.长期任务统计.get(task1.名称, None)
        if tstat1 is None:
            tstat1 = EmptyLongTaskStats(task1)
        if task1.保持安排 == "+":
            # 保持安排，不计入调度
            leftdays = workdays(P.time, task1.最晚结束, worktime)
            if leftdays < perioddays:
                tpd = tstat1.预计需要时间
            else:
                tpd = tstat1.预计需要时间 * perioddays / leftdays
            建议用时[task1.名称] = tpd
            tpd_keep += tpd
            continue
        if tstat1.进度 >= task1.总数:
            continue
        if tstat1.进度 == 0:
            collection.append(
                (
                    timedelta(minutes=20),
                    task1.最晚开始,
                    False,
                    task1.名称,
                )
            )
        else:
            collection.append(
                (
                    tstat1.预计需要时间,
                    task1.最晚结束,
                    False,
                    task1.名称,
                )
            )
    for task2 in N.state.短期任务.values():
        if isdisabled(task2.名称, N.state.选择排序偏好):
            continue
        skip_period = False
        if workdays(P.time, task2.最早开始, worktime) > perioddays:
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
            (tstat2.预计需要时间, task2.最晚结束, skip_period, task2.名称)
        )
    # 按照截止日期排序
    collection.sort(key=lambda x: x[1])
    tot_work = timedelta(0)
    tpd_max = timedelta(0)
    tpd_max_i = 0
    tpd_max_time = P.time
    tpd_max_work = timedelta(0)
    if collection and workdays(P.time, collection[0][1], worktime) <= 0:
        log.info(f"overdue!, {collection[0]}, {P.time}")
        # overdue!
        for i, (workt, endtime, skip_period, name) in enumerate(collection):
            tot_worktime = workdays(P.time, endtime, worktime)
            if tot_worktime > 0:
                break
            tpd_max_i = i + 1
            tpd_max_time = endtime
            tpd_max_work += workt
            建议用时[name] = workt
        tpd_max = timedelta(seconds=-1)  # overdue!
    else:
        for i, (workt, endtime, skip_period, name) in enumerate(collection):
            tot_work += workt
            tot_worktime = workdays(P.time, endtime, worktime)
            # tot_worktime > 0
            tpd = tot_work / tot_worktime
            if tpd > tpd_max:
                tpd_max_i = i + 1
                tpd_max = tpd
                tpd_max_time = endtime
                tpd_max_work = tot_work
        # 对tpd_max_i（关键点）之前的任务全部合理调度
        tot_quota = timedelta(0)  # 当前任务截止时间前可用时间（包含已分配和未分配时间）
        tot_alloc = timedelta(0)  # 总时间已分配
        period_quota = tpd_max * perioddays  # 总用时
        period_alloc = timedelta(0)  # 已分配
        for workt, endtime, skip_period, name in collection[:tpd_max_i]:
            # floating point error
            tot_quota = tpd_max_work * (
                workdays(P.time, endtime, worktime)
                / workdays(P.time, tpd_max_time, worktime)
            )
            log.debug(
                f"workt: {workt}, into {tot_quota - tot_alloc}, day {period_quota - period_alloc}"
            )
            # float point error tolerance
            if tot_alloc > tot_quota:
                continue
            if period_alloc > period_quota:
                continue
            period_to_alloc = (period_quota - period_alloc) * (
                workt / (tot_quota - tot_alloc)
            )
            if period_to_alloc > workt:
                period_to_alloc = workt
            tot_alloc += workt
            if skip_period:
                period_to_alloc = timedelta(0)
            建议用时[name] = period_to_alloc
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
