from typing import Literal
from dataclasses import dataclass
from datetime import datetime, timedelta, time as datetime_time
import math

from bb_models import WorktimeModel, ProgressModel
from bb_collect import State
from bb_config import 推荐用时


@dataclass
class TaskSpeed:
    速度: float  # per hour
    每日用时: timedelta
    tot_time: timedelta
    tot_dayspan: float
    tot_progress: float


@dataclass
class TaskEstimate:
    预计完成时间: timedelta
    预计可用时间: timedelta
    差距: timedelta


@dataclass
class TaskStats:
    进度: float
    用时: timedelta
    标记: Literal["*", "-", "=", "!"]
    进度描述: str | None = None
    # * 进行中 - 等待开始 = 已完成 ! 已超时
    速度: TaskSpeed | None = None  # 开始的任务才能计算速度
    预计: TaskEstimate | None = None  # 开始但未完成的任务才能估计完成时间
    点数: int | None = (
        None  # 点数。到时未开始: -100 * 延后天数。已开始：100 * (时间差距 / 每日用时)。已结束：100 * 剩余天数
    )


@dataclass
class StateStats:
    Goldie点数: int
    任务点数: int
    任务统计: dict[str, TaskStats]
    状态点数: int
    状态生效: list[str]
    其他任务点数: int
    其他任务生效: list[str]
    总每日用时: timedelta


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
    total_time_day = timedelta(0)

    for wt in worktime:
        wt_begin = datetime.combine(end, wt.开始)
        wt_end = datetime.combine(end, wt.结束)
        if wt_end <= wt_begin:
            wt_end += timedelta(days=1)
        total_time_day += wt_end - wt_begin

    timediff = (end_time_day - begin_time_day) / total_time_day
    return datediff + timediff


def calculate_speed(
    progress: list[ProgressModel],
    begin_time: datetime,
    now_time: datetime,
    worktime: list[WorktimeModel],
) -> TaskSpeed | None:
    # 近期记录
    MIN_TIME = timedelta(hours=2)
    MIN_TIMESPAN = 3
    new_time = now_time
    tot_time = timedelta(0)
    new_progress = progress[-1].进度
    found = False
    count = 0
    # 这里需要注意时间的计算方式：
    # 进度记录描述的是 “花费‘用时’时间后，在‘时间’让进度达到了‘进度’”。
    # 选择“开始的记录”后“开始的记录”本身的时间不包含在总时间内（那是起点）
    for p in reversed(progress):
        old_time = p.时间
        if (
            tot_time > MIN_TIME
            and workdays(old_time, new_time, worktime) > MIN_TIMESPAN
        ):
            found = True
            old_progress = p.进度
            break
        tot_time += p.用时
        if p.用时 != timedelta(0):
            count += 1
    if not found:
        if begin_time < old_time:
            old_time = begin_time
        old_progress = 0.0
    if old_progress == new_progress or tot_time == timedelta(0):
        # bad condition
        return None
    tot_dayspan = workdays(old_time, new_time, worktime)
    tot_progress = new_progress - old_progress
    速度 = tot_progress / (tot_time / timedelta(hours=1))
    每日用时 = tot_time / tot_dayspan
    return TaskSpeed(
        速度=速度,
        每日用时=每日用时,
        tot_time=tot_time,
        tot_dayspan=tot_dayspan,
        tot_progress=tot_progress,
    )


def statistic(now_state: State, now_time: datetime) -> StateStats:
    # Goldie点数 = 任务 + 状态 + 其他任务完成
    # 任务
    任务点数 = 0
    任务统计: dict[str, TaskStats] = {}
    总每日用时 = timedelta(0)
    worktime = now_state.工作时段
    for task in now_state.任务.values():
        标记: Literal["*", "-", "=", "!"] = "*"
        if now_time < task.开始:
            标记 = "-"
        elif now_time > task.结束:
            标记 = "!"
        else:
            标记 = "*"
        progress = now_state.进度.get(task.名称, None)
        进度 = 0.0
        进度描述 = None
        用时 = timedelta(0)
        速度 = None
        if progress is not None:
            current = progress[-1]
            进度 = current.进度
            for node in progress:
                if node.描述 is not None or node.进度 != 进度:
                    进度描述 = node.描述
                用时 += node.用时
            速度 = calculate_speed(progress, task.开始, now_time, worktime)
            if task.总数 is not None:
                if 进度 >= task.总数:
                    标记 = "="
        预计 = None
        if 速度 and task.总数 is not None:
            总每日用时 += 速度.每日用时
            预计完成时间 = timedelta(hours=1) * (task.总数 - current.进度) / 速度.速度
            预计可用时间 = workdays(now_time, task.结束, worktime) * 速度.每日用时
            差距 = 预计可用时间 - 预计完成时间
            预计 = TaskEstimate(
                预计完成时间=预计完成时间, 预计可用时间=预计可用时间, 差距=差距
            )
        任务统计[task.名称] = TaskStats(
            进度=进度,
            进度描述=进度描述,
            用时=用时,
            标记=标记,
            速度=速度,
            预计=预计,
        )
    for name, stats in 任务统计.items():
        if stats.标记 == "=":
            end_time = now_state.任务[name].结束
            if end_time > now_time:
                # 提前完成的奖励
                stats.点数 = math.floor(
                    100 * workdays(now_time, end_time, worktime) + 0.5
                )
        else:
            if stats.预计 is not None:
                if stats.预计.差距 > timedelta(0):
                    # 提前的任务，使用推荐用时作为总每日用时来估计“提前天数”，防止“完成后休息”的行为反而提高点数（继续提前完成反而降低点数）
                    stats.点数 = math.floor(stats.预计.差距 / 推荐用时 * 100 + 0.5)
                else:
                    # 落后的任务，使用真正的平均每日用时估计“提前天数”。
                    stats.点数 = math.floor(stats.预计.差距 / 总每日用时 * 100 + 0.5)
            else:
                start_time = now_state.任务[name].开始
                if now_time > start_time:
                    # 延迟开始的惩罚
                    stats.点数 = math.floor(
                        workdays(start_time, now_time, worktime) * -100 + 0.5
                    )
        if stats.点数 is not None:
            任务点数 += stats.点数

    # 状态点数
    状态点数 = 0
    状态生效: list[str] = []
    for status in now_state.状态.values():
        if status.点数 is None:
            continue
        if status.开始 is not None and status.开始 > now_time:
            continue
        if status.结束 is not None and status.结束 < now_time:
            continue
        状态点数 += status.点数
        状态生效.append(status.名称)

    # 其他任务点数
    其他任务点数 = 0
    其他任务生效: list[str] = []
    for todo in now_state.待办事项.values():
        if todo.完成 is not None and todo.完成 > now_time - timedelta(days=3):
            其他任务点数 += todo.点数
            其他任务生效.append(todo.名称)

    Goldie点数 = 任务点数 + 状态点数 + 其他任务点数
    return StateStats(
        Goldie点数=Goldie点数,
        任务点数=任务点数,
        任务统计=任务统计,
        状态点数=状态点数,
        状态生效=状态生效,
        其他任务点数=其他任务点数,
        其他任务生效=其他任务生效,
        总每日用时=总每日用时,
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
