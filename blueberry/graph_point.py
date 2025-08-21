from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List, Tuple

from .parser import load_data
from .collect import collect_state
from .statistic import statistic

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


def get_goldie_points_history(
    days: int = 30, data_file: str = "data.xlsx"
) -> List[Tuple[datetime, int]]:
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
            history.append((current_time, stats.Goldie点数))
        except Exception as e:
            print(f"{current_time}: {e}")
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
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    plt.gca().xaxis.set_major_locator(
        mdates.DayLocator(interval=1)
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


if __name__ == "__main__":
    print("正在生成近30天 Goldie 点数变化折线图 (30分钟采样)...")
    history = get_goldie_points_history(30)
    plot_goldie_points(history)
    print("图表已保存为 goldie_points_trend.png")
