from datetime import timedelta
import argparse

import dateparser

from .parser import load_data
from .collect import collect_state
from .statistic import statistic
from .webserver import live_server
from .report import (
    report_head,
    report_worktime,
    report_long_tasks,
    report_short_tasks,
    report_tasks_diff,
    ReportData,
)
from .config import 推荐用时
from .ctz_now import ctz_now


def main() -> None:
    parser = argparse.ArgumentParser()
    # 基本参数
    parser.add_argument(
        "-l", "--live", action="store_true", help="开启实时点数显示HTTP网页"
    )
    # 实时参数
    parser.add_argument(
        "-H",
        "--host",
        action="store",
        default="127.0.0.1",
        help="HTTP服务器IP(默认: 127.0.0.1)",
    )
    parser.add_argument(
        "-P",
        "--port",
        action="store",
        type=int,
        default=26019,
        help="HTTP服务器端口(默认: 26019)",
    )
    parser.add_argument(
        "-w",
        "--workbook",
        action="store",
        default="记录.xlsx",
        help="表格文件路径(默认: 记录.xlsx)",
    )
    # 时间
    parser.add_argument(
        "-f",
        "--from",
        action="store",
        dest="from_",
        metavar="FROM",
        type=dateparser.parse,
        help="开始时间(可选)",
    )
    parser.add_argument(
        "-t",
        "--time",
        "--to",
        action="store",
        type=dateparser.parse,
        help="当前时间(默认为现在)",
    )
    parser.add_argument(
        "-d", "--daily", action="store_true", help="设置开始时间为今天零点"
    )
    # 详细格式设定
    parser.add_argument(
        "-c",
        "--change",
        action="store_true",
        help="只显示进度变化",
    )
    parser.add_argument(
        "-D",
        "--olddiff",
        action="store_true",
        help="使用 旧→新 格式，不用 新(±变化) 格式",
    )
    parser.add_argument("-o", "--output", action="store", help="输出文件路径")
    args = parser.parse_args()

    if args.live:
        live_server(args.workbook, host=args.host, port=args.port)
        return

    data = load_data(args.workbook)

    now_time = ctz_now()
    if args.time is not None:
        now_time = args.time

    yesterday_time = now_time.replace(hour=0, minute=0, second=0)

    if args.from_ is not None:
        prev_time = args.from_
    elif args.daily:
        prev_time = yesterday_time
    else:
        prev_time = None

    now_state = collect_state(data, now_time)
    now_stats = statistic(now_state, now_time)
    now_data = ReportData(now_time, now_state, now_stats)

    report = report_head(now_data) + "\n\n"
    if prev_time:
        prev_state = collect_state(data, prev_time)
        prev_stats = statistic(prev_state, prev_time)
        prev_data = ReportData(prev_time, prev_state, prev_stats)
        report += report_tasks_diff(now_data, prev_data, hide_decay=args.change)
    else:
        report += report_worktime(now_data) + "\n\n"
        report += report_long_tasks(now_data) + "\n\n"
        report += report_short_tasks(now_data) + "\n\n"
    if args.output is not None:
        with open(f"{args.output}.json", "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
        with open(f"{args.output}", "w", encoding="utf-8") as f:
            f.write(report)

    print(report)


if __name__ == "__main__":
    main()
