from datetime import datetime, timedelta, time as datetime_time

from .models import WorktimeModel


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
