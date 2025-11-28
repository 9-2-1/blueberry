from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import logging

from .models import ProgressModel, LongTaskModel
from .collect import State
from .speed import TaskSpeed, calculate_speed
from .picker import isdisabled
from .workdays import workdays
from .config import 推荐用时

log = logging.getLogger(__name__)


@dataclass
class TaskStats:
    预计需要时间: timedelta
    预计可用时间: timedelta
    最晚结束: datetime
    点数: int
    用时: timedelta


@dataclass
class LongTaskStats(TaskStats):
    进度: float
    速度: float  # per hour
    每日用时: timedelta
    最晚开始: datetime


def EmptyLongTaskStats(task: LongTaskModel) -> LongTaskStats:
    return LongTaskStats(
        预计需要时间=timedelta(0),
        预计可用时间=timedelta(0),
        最晚结束=task.最晚结束,
        点数=0,
        用时=timedelta(0),
        进度=0,
        速度=0,
        每日用时=timedelta(0),
        最晚开始=task.最晚开始,
    )


@dataclass
class StateStats:
    Goldie点数: int
    长期任务点数: int
    长期任务统计: dict[str, LongTaskStats]
    总每日平均用时: timedelta


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
        速度 = TaskSpeed(速度=0.0, 每日用时=timedelta(0))
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
            预计需要时间 = timedelta(hours=1) * (task1.总数 - 进度) / 速度.速度
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
            进度=进度,
            速度=速度.速度,
            每日用时=速度.每日用时,
            最晚开始=task1.最晚开始,
        )
        长期任务点数 += 点数

    总每日平均用时 = timedelta(0)
    if tot_progress:
        tot_progress.sort(key=lambda x: x.时间)
        # 每日平均用时可以通过把所有的进度混在一起后计算近期每日时间得到
        # 返回的速度没有意义。
        tot_speed = calculate_speed(
            tot_progress, tot_progress[0].时间, now_time, worktime
        )
        总每日平均用时 = tot_speed.每日用时

    Goldie点数 = 长期任务点数
    return StateStats(
        Goldie点数=Goldie点数,
        长期任务点数=长期任务点数,
        长期任务统计=长期任务统计,
        总每日平均用时=总每日平均用时,
    )
