from typing import Literal
from dataclasses import dataclass
from datetime import datetime, timedelta, time as datetime_time
import math
import logging

from .models import (
    WorktimeModel,
    ProgressModel,
    PickerModel,
    LongTaskModel,
    ShortTaskModel,
)
from .collect import State
from .config import 推荐用时

log = logging.getLogger(__name__)


@dataclass
class TaskSpeed:
    速度: float  # per hour
    每日用时: timedelta


@dataclass
class TaskStats:
    预计需要时间: timedelta
    预计可用时间: timedelta
    最晚结束: datetime
    点数: int
    用时: timedelta
    推荐每日用时: timedelta  # 最后一次统计


@dataclass
class LongTaskStats(TaskStats):
    进度: float
    速度: float  # per hour
    每日用时: timedelta
    最晚开始: datetime


@dataclass
class ShortTaskStats(TaskStats):
    # blink!
    pass


def EmptyLongTaskStats(task: LongTaskModel) -> LongTaskStats:
    return LongTaskStats(
        预计需要时间=timedelta(0),
        预计可用时间=timedelta(0),
        最晚结束=task.最晚结束,
        点数=0,
        用时=timedelta(0),
        推荐每日用时=timedelta(0),
        进度=0,
        速度=0,
        每日用时=timedelta(0),
        最晚开始=task.最晚开始,
    )


def EmptyShortTaskStats(task: ShortTaskModel) -> ShortTaskStats:
    return ShortTaskStats(
        预计需要时间=timedelta(0),
        预计可用时间=timedelta(0),
        最晚结束=task.最晚结束,
        点数=0,
        用时=timedelta(0),
        推荐每日用时=timedelta(0),
    )


@dataclass
class StateStats:
    Goldie点数: int
    长期任务点数: int
    长期任务统计: dict[str, LongTaskStats]  # TODO
    短期任务点数: int
    短期任务统计: dict[str, ShortTaskStats]  # TODO
    总每日平均用时: timedelta
    建议每日用时: timedelta
    下一关键时间: datetime
    下一关键节点任务量时长: timedelta


def workday_time(time: datetime, worktime: list[WorktimeModel]) -> timedelta:
    # 计算某个时间点当天已经过了多少工作时间。
    delta = timedelta(0)
    for wt in worktime:
        wt_begin = datetime.combine(time, wt.开始)
        wt_end = datetime.combine(time, wt.结束)
        # 跨天的情况
        if wt_end <= wt_begin:
            wt_end += timedelta(days=1)
        if time < wt_begin:
            pass
        elif time < wt_end:
            delta += time - wt_begin
        else:
            delta += wt_end - wt_begin
    return delta


def workday_time_total(worktime: list[WorktimeModel]) -> timedelta:
    total_time_day = timedelta(0)
    today = datetime.today()
    for wt in worktime:
        wt_begin = datetime.combine(today, wt.开始)
        wt_end = datetime.combine(today, wt.结束)
        if wt_end <= wt_begin:
            wt_end += timedelta(days=1)
        total_time_day += wt_end - wt_begin
    return total_time_day


def workdays(begin: datetime, end: datetime, worktime: list[WorktimeModel]) -> float:
    # 计算两个时间之间的工作时长
    # 注意，这里将一天工作时长视为“一天”。
    # 如果实际的工作时长是 3 小时，而一天的工作时间和是 6 小时，那么就会得到 0.5 天

    # 为了避免过多的分类讨论，使用定数法
    begin_date = begin.date()
    end_date = end.date()

    datediff = (end_date - begin_date) / timedelta(days=1)

    begin_time_day = workday_time(begin, worktime)
    end_time_day = workday_time(end, worktime)
    total_time_day = workday_time_total(worktime)

    timediff = (end_time_day - begin_time_day) / total_time_day
    return datediff + timediff


def calculate_speed(
    progress: list[ProgressModel],
    begin_time: datetime,
    now_time: datetime,
    worktime: list[WorktimeModel],
) -> TaskSpeed:
    # 近期记录
    MIN_TOT_TIME = timedelta(hours=6)
    MIN_TOT_DAYSPAN = 4  # workdays
    tot_progress = 0.0
    tot_time = timedelta(0)
    tot_dayspan = workdays(progress[-1].时间, now_time, worktime)  # workdays: float
    # 这里需要注意时间的计算方式：
    # 进度记录描述的是 “花费‘用时’时间后，在‘时间’让进度达到了‘进度’”。
    # 选择“开始的记录”后“开始的记录”本身的时间不包含在总时间内（那是起点）
    log.debug("calculate_speed:")
    log.debug("-" * 80)
    for i in reversed(range(len(progress))):
        add_progress = (
            progress[i].进度 - progress[i - 1].进度 if i != 0 else progress[i].进度
        )
        add_time = progress[i].用时
        prev_node_time = progress[i - 1].时间 if i != 0 else begin_time
        add_dayspan = workdays(prev_node_time, progress[i].时间, worktime)
        if add_dayspan < 0:
            add_dayspan = 0
        add_ratio = 0.0
        if tot_time >= MIN_TOT_TIME:
            pass
        elif tot_time + add_time <= MIN_TOT_TIME:
            add_ratio = 1.0
        else:
            k = (MIN_TOT_TIME - tot_time) / add_time
            if add_ratio < k:
                add_ratio = k
        if tot_dayspan >= MIN_TOT_DAYSPAN:
            pass
        elif tot_dayspan + add_dayspan <= MIN_TOT_DAYSPAN:
            add_ratio = 1.0
        else:
            k = (MIN_TOT_DAYSPAN - tot_dayspan) / add_dayspan
            if add_ratio < k:
                add_ratio = k
        tot_time += add_time * add_ratio
        tot_dayspan += add_dayspan * add_ratio
        tot_progress += add_progress * add_ratio
        log.debug(
            f"{add_ratio:5.0%} t{add_time} d{add_dayspan:.2f} T{tot_time} D{tot_dayspan:.2f} @{progress[i].时间} #{progress[i].名称}"
        )
        if add_ratio < 1.0:
            break
    log.debug("=" * 80)
    if tot_time == timedelta(0):
        return TaskSpeed(
            速度=0.0,
            每日用时=timedelta(0),
        )
    速度 = tot_progress / (tot_time / timedelta(hours=1))
    每日用时 = tot_time / tot_dayspan
    log.debug(f"速度: {速度:.2f} 每日用时: {每日用时}")
    return TaskSpeed(
        速度=速度,
        每日用时=每日用时,
    )


def isdisabled(task_name: str, preference: list[PickerModel]) -> bool:
    for picker in preference:
        if task_name == picker.名称:
            if picker.禁用 == "-":
                return True
    return False


def statistic(now_state: State, now_time: datetime) -> StateStats:
    长期任务点数 = 0
    长期任务统计: dict[str, LongTaskStats] = {}
    worktime = now_state.工作时段
    tot_progress: list[ProgressModel] = []
    for task1 in now_state.长期任务.values():
        if isdisabled(task1.名称, now_state.选择排序偏好):
            continue
        progress = now_state.长期进度.get(task1.名称, None)
        进度 = 0.0
        用时 = timedelta(0)
        速度 = TaskSpeed(
            速度=0.0,
            每日用时=timedelta(0),
        )
        if progress is not None:
            tot_progress.extend(progress)
            current = progress[-1]
            进度 = current.进度
            for node in progress:
                用时 += node.用时
            速度 = calculate_speed(progress, task1.最晚开始, now_time, worktime)
        预计可用时间 = workdays(now_time, task1.最晚结束, worktime) * 速度.每日用时
        if 预计可用时间 < timedelta(0):
            预计可用时间 = timedelta(0)
        预计需要时间 = 预计可用时间
        if 速度.速度 != 0.0:
            预计需要时间 = timedelta(hours=1) * (task1.总数 - current.进度) / 速度.速度
        差距 = 预计可用时间 - 预计需要时间
        点数 = 0
        if 进度 > 0:
            点数 = math.floor(差距 / 推荐用时 * 100 + 0.5)
        elif now_time > task1.最晚开始:
            点数 = math.floor(workdays(now_time, task1.最晚开始, worktime) * 100 + 0.5)
        长期任务统计[task1.名称] = LongTaskStats(
            预计需要时间=预计需要时间,
            预计可用时间=预计可用时间,
            最晚结束=task1.最晚结束,
            点数=点数,
            用时=用时,
            推荐每日用时=timedelta(0),
            进度=进度,
            速度=速度.速度,
            每日用时=速度.每日用时,
            最晚开始=task1.最晚开始,
        )
        长期任务点数 += 点数

    短期任务点数 = 0
    短期任务统计: dict[str, ShortTaskStats] = {}
    for task2 in now_state.短期任务.values():
        if isdisabled(task2.名称, now_state.选择排序偏好):
            continue
        预计可用时间 = workdays(now_time, task1.最晚结束, worktime) * 速度.每日用时
        if 预计可用时间 < timedelta(0):
            预计可用时间 = timedelta(0)
        # TODO 其他任务点数 += todo.点数
        用时 = timedelta(0)
        if task2.用时 is not None:
            用时 = task2.用时
        elif task2.完成 is not None and now_time >= task2.完成:
            用时 = task2.预计用时
        点数 = 0
        ptsu = task2.预计用时 / 推荐用时 * 100
        pts = 0.0
        if now_time > task2.最晚结束:
            pts = -ptsu
        elif now_time <= task2.最早开始:
            pts = 0.0
        else:
            pts = (
                -ptsu
                * workdays(now_time, task2.最晚结束, worktime)
                / workdays(task2.最早开始, task2.最晚结束, worktime)
            )
        if task2.完成 is not None and now_time >= task2.完成:
            tot_progress.append(
                ProgressModel(
                    时间=task2.完成,
                    名称=task2.名称,
                    进度=0.0,
                    用时=用时,
                )
            )
            pts += ptsu
        elif task2.预计用时 != timedelta(0):
            tot_progress.append(
                ProgressModel(
                    时间=task2.时间,
                    名称=task2.名称,
                    进度=0.0,
                    用时=用时,
                )
            )
            pts += ptsu * (用时 / task2.预计用时)
        点数 = math.floor(pts + 0.5)
        短期任务统计[task2.名称] = ShortTaskStats(
            预计需要时间=task2.预计用时 - 用时,
            预计可用时间=预计可用时间,
            最晚结束=task2.最晚结束,
            点数=点数,
            用时=用时,
            推荐每日用时=timedelta(0),
        )
        短期任务点数 += 点数

    总每日平均用时 = timedelta(0)
    if tot_progress:
        tot_progress.sort(key=lambda x: x.时间)
        # 每日平均用时可以通过把所有的进度混在一起后计算近期每日时间得到
        # 返回的速度没有意义。
        tot_speed = calculate_speed(
            tot_progress, tot_progress[0].时间, now_time, worktime
        )
        总每日平均用时 = tot_speed.每日用时

    # 推荐时长
    collection: list[tuple[timedelta, datetime, TaskStats]] = []
    for task1 in now_state.长期任务.values():
        tstat1 = 长期任务统计[task1.名称]
        if tstat1.进度 >= task1.总数:
            continue
        if tstat1.进度 == 0:
            collection.append(
                (
                    timedelta(minutes=20),
                    task1.最晚开始,
                    tstat1,
                )
            )
        else:
            collection.append(
                (
                    tstat1.预计需要时间,
                    task1.最晚结束,
                    tstat1,
                )
            )
    for task2 in now_state.短期任务.values():
        if task2.完成 is not None and now_time >= task2.完成:
            continue
        tstat2 = 短期任务统计[task2.名称]
        collection.append((tstat2.预计需要时间, task2.最晚结束, tstat2))
    # 按照截止日期排序
    collection.sort(key=lambda x: x[1])
    tot_work = timedelta(0)
    tpd_max = timedelta(0)
    tpd_max_i = 0
    tpd_max_time = now_time
    tpd_max_work = timedelta(0)
    if collection and workdays(now_time, collection[0][1], worktime) <= 0:
        log.info("overdue!")
        # overdue!
        for i, (workt, endtime, tstat) in enumerate(collection):
            tot_worktime = workdays(now_time, endtime, worktime)
            if tot_worktime > 0:
                break
            tpd_max_i = i + 1
            tpd_max_time = endtime
            tpd_max_work += workt
            tstat.推荐每日用时 = workt
        tpd_max = timedelta(seconds=-1) # overdue!
    else:
        for i, (workt, endtime, tstat) in enumerate(collection):
            tot_work += workt
            tot_worktime = workdays(now_time, endtime, worktime)
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
        day_quota = tpd_max  # 总每日用时
        day_alloc = timedelta(0)  # 已分配
        for workt, endtime, tstat in collection[:tpd_max_i]:
            # floating point error
            tot_quota = tpd_max_work * (
                workdays(now_time, endtime, worktime)
                / workdays(now_time, tpd_max_time, worktime)
            )
            log.debug(
                f"workt: {workt}, into {tot_quota - tot_alloc}, day {day_quota - day_alloc}"
            )
            if tot_alloc > tot_quota:
                continue
            if day_alloc > day_quota:
                continue
            day_to_alloc = (day_quota - day_alloc) * (workt / (tot_quota - tot_alloc))
            if day_to_alloc > workt:
                day_to_alloc = workt
            tot_alloc += workt
            tstat.推荐每日用时 = day_to_alloc
            log.debug(day_to_alloc)
            day_alloc += day_to_alloc
        log.debug(f"allocated par day: {day_alloc}, {day_quota}")
        log.debug(f"allocated total: {tot_alloc}, {tot_quota}")

    Goldie点数 = 长期任务点数 + 短期任务点数
    return StateStats(
        Goldie点数=Goldie点数,
        长期任务点数=长期任务点数,
        长期任务统计=长期任务统计,
        短期任务点数=短期任务点数,
        短期任务统计=短期任务统计,
        总每日平均用时=总每日平均用时,
        建议每日用时=tpd_max,
        下一关键时间=tpd_max_time,
        下一关键节点任务量时长=tpd_max_work,
    )


def test_workdays() -> None:
    worktime = [
        WorktimeModel(
            开始=datetime_time(4, 0),
            结束=datetime_time(8, 0),
        ),
        WorktimeModel(
            开始=datetime_time(12, 0),
            结束=datetime_time(16, 0),
        ),
        WorktimeModel(
            开始=datetime_time(22, 0),
            结束=datetime_time(0, 0),
        ),
    ]
    prev_time = datetime.now()
    now_time = prev_time
    for i in range(100):
        now_time += timedelta(hours=0.5)
        days = workdays(prev_time, now_time, worktime)
        print(prev_time, now_time, days)
    for i in range(100):
        prev_time += timedelta(hours=0.5)
        days = workdays(prev_time, now_time, worktime)
        print(prev_time, now_time, days)
