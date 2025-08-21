from blueberry.graph_point import get_goldie_points_history, plot_goldie_points

if __name__ == "__main__":
    print("正在测试 Goldie 点数图表生成...")

    # 使用模拟数据测试
    # print("使用模拟数据生成图表...")
    # history = get_goldie_points_history(30)
    # plot_goldie_points(history)
    # print("模拟数据图表已生成并保存为 goldie_points_trend.png")

    print("使用实际数据生成图表...")
    history = get_goldie_points_history(30, "记录.xlsx")
    plot_goldie_points(history)
    print("实际数据图表已生成并保存为 goldie_points_trend.png")
