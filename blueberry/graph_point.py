from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List, Tuple
import traceback

from .parser import load_data
from .config import 推荐用时
from .collect import collect_state
from .statistic import statistic
from .planner import planner, PlanData

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


def get_goldie_points_loads_history(
    days: int = 30, data_file: str = "data.xlsx"
) -> List[Tuple[datetime, int, timedelta, timedelta]]:
    """
    获取近 days 天的 Goldie 点数历史数据，采样精度为30分钟每次

    Args:
        days: 要获取的天数
        data_file: 数据文件的路径，默认为 'data.xlsx'

    Returns:
        包含 (日期, Goldie点数) 的列表
    """
    # 加载数据
    try:
        data = load_data(data_file)
    except Exception as e:
        print(f"加载数据失败: {e}")
        raise e

    history = []
    end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=days)

    # 每30分钟采样一次
    current_time = start_time
    while current_time <= end_time:
        state = collect_state(data, current_time)
        try:
            stats = statistic(state, current_time)
            current_data = PlanData(current_time, state, stats)
            tomorrow_time = current_time + timedelta(days=1)
            plan = planner(current_data, current_data, tomorrow_time, state.工作时段)
            history.append(
                (
                    current_time,
                    stats.Goldie点数,
                    plan.总建议用时,
                    stats.总每日平均用时,
                )
            )
        except Exception as e:
            print(f"{current_time}: {e}")
            traceback.print_exc()
        current_time += timedelta(minutes=30)

    # 按日期升序排序
    history.sort(key=lambda x: x[0])
    return history


def plot_goldie_points(history: List[Tuple[datetime, int]]) -> None:
    """
    绘制 Goldie 点数变化折线图

    Args:
        history: 包含 (日期, Goldie点数) 的列表
    """
    dates, points = zip(*history)

    plt.figure(figsize=(12, 6))
    plt.plot(dates, points, linestyle="-", color="blue", linewidth=2)

    # 设置标题和坐标轴标签
    plt.title("近30天 Goldie 点数变化趋势 (30分钟采样)", fontsize=16)
    plt.xlabel("日期", fontsize=14)
    plt.ylabel("Goldie 点数", fontsize=14)

    # 设置x轴日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))  # type: ignore
    plt.gca().xaxis.set_major_locator(
        mdates.DayLocator(interval=1)  # type: ignore
    )  # 每1天显示一个刻度
    plt.gcf().autofmt_xdate()  # 自动旋转日期标签

    # 添加网格线
    plt.grid(True, linestyle="--", alpha=0.7)

    # 设置y轴范围，让图表更美观
    min_point = min(points)
    max_point = max(points)
    plt.ylim(min_point - 50, max_point + 50)

    plt.tight_layout()
    plt.savefig("goldie_points_trend.png", dpi=300)


def plot_daily_time(history: List[Tuple[datetime, timedelta, timedelta]]) -> None:
    """
    绘制每日时长变化折线图

    Args:
        history: 包含 (日期, 负载) 的列表
    """
    dates, time_recommend, time_used = zip(*history)

    plt.figure(figsize=(12, 6))
    plt.plot(
        dates,
        [x / timedelta(hours=1) for x in time_recommend],
        linestyle="-",
        color="green",
        linewidth=2,
    )
    plt.plot(
        dates,
        [x / timedelta(hours=1) for x in time_used],
        linestyle="-",
        color="blue",
        linewidth=2,
    )
    plt.plot(
        dates,
        [推荐用时 / timedelta(hours=1) for x in time_recommend],
        linestyle="--",
        color="red",
        linewidth=2,
    )

    # 设置标题和坐标轴标签
    plt.title("近30天每日时长变化趋势 (30分钟采样)", fontsize=16)
    plt.xlabel("日期", fontsize=14)
    plt.ylabel("时长 (小时)", fontsize=14)

    # 设置x轴日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))  # type: ignore
    plt.gca().xaxis.set_major_locator(
        mdates.DayLocator(interval=1)  # type: ignore
    )  # 每1天显示一个刻度
    plt.gcf().autofmt_xdate()  # 自动旋转日期标签

    # 添加网格线
    plt.grid(True, linestyle="--", alpha=0.7)

    # 设置y轴范围，让图表更美观
    plt.ylim(0, 24)

    plt.tight_layout()
    plt.savefig("loads_trend.png", dpi=300)


def main() -> None:
    print("正在生成近30天 Goldie 点数变化折线图 (30分钟采样)...")
    history = get_goldie_points_loads_history(30, "记录.xlsx")
    plot_goldie_points([(x[0], x[1]) for x in history])
    plot_daily_time([(x[0], x[2], x[3]) for x in history])


if __name__ == "__main__":
    main()
