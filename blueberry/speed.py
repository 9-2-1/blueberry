from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from .models import ProgressModel, WorktimeModel
from .workdays import workdays

log = logging.getLogger(__name__)


@dataclass
class TaskSpeed:
    速度: float  # per hour
    每日用时: timedelta


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
