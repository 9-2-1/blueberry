from datetime import datetime
import os
import argparse

from .parser import load_data
from .collect import collect_state
from .statistic import statistic
from .webserver import live_server
from .report import (
    report_head,
    report_main_tasks,
    report_todo_tasks,
    report_statuses,
    report_hints,
    ReportData,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--live", action="store_true", help="开启实时点数显示HTTP网页"
    )
    parser.add_argument(
        "-w",
        "--workbook",
        action="store",
        default="记录.xlsx",
        help="表格文件路径 (默认: 记录.xlsx)",
    )
    parser.add_argument(
        "-f",
        "--from",
        action="store",
        dest="from_",
        help="开始时间(可选, YYYY-MM-DDTHH:MM[:SS])",
    )
    parser.add_argument("-t", "--time", "--to", action="store", help="当前时间")
    parser.add_argument("-s", "--short", action="store_true", help="使用简化格式")
    parser.add_argument(
        "-C",
        "--change-append",
        action="store_true",
        help="使用简化格式的同时用普通格式显示变化部分",
    )
    parser.add_argument(
        "-c", "--change-only", action="store_true", help="只显示变化的部分"
    )
    parser.add_argument(
        "-d",
        "--olddiff",
        action="store_true",
        help="使用 旧→新 格式，不用 新(±变化) 格式",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    parser.add_argument(
        "-D",
        "--daily",
        action="store_true",
        help="显示今日进度(-t 对应的日期), 如果指定了 -f, 则 -f 和 -t 应该在同一天)",
    )
    parser.add_argument("-N", "--shownote", action="store_true", help="显示说明")
    parser.add_argument(
        "-n", "--nologging", action="store_true", help="不保存报告为文件"
    )

    args = parser.parse_args()

    if args.live:
        live_server(args.workbook)
        return

    data = load_data(args.workbook)
    tmark = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.time is not None:
        now_time = datetime.fromisoformat(args.time)
    else:
        now_time = datetime.now()
    yesterday_time = now_time.replace(hour=0, minute=0, second=0)
    if args.from_ is not None:
        prev_time = datetime.fromisoformat(args.from_)
    elif args.daily:
        prev_time = yesterday_time
    else:
        prev_time = None

    now_state = collect_state(data, now_time)
    now_stats = statistic(now_state, now_time)
    now_data = ReportData(now_time, now_state, now_stats)

    yesterday_state = collect_state(data, yesterday_time)
    yesterday_stats = statistic(yesterday_state, yesterday_time)
    yesterday_data = ReportData(yesterday_time, yesterday_state, yesterday_stats)

    prev_data = None
    if prev_time is not None:
        prev_state = collect_state(data, prev_time)
        prev_stats = statistic(prev_state, prev_time)
        prev_data = ReportData(prev_time, prev_state, prev_stats)

    report = ""
    report += report_head(now_data, prev_data, short=args.short, olddiff=args.olddiff)

    report += report_main_tasks(
        now_data,
        prev_data,
        yesterday_data if args.daily else None,
        change_only=args.change_only,
        verbose=args.verbose,
        short=args.short or args.change_append,
        olddiff=args.olddiff,
    )
    if args.change_append:
        report += report_main_tasks(
            now_data,
            prev_data,
            yesterday_data if args.daily else None,
            change_only=True,
            verbose=args.verbose,
            short=False,
            olddiff=args.olddiff,
        )
    report += report_todo_tasks(
        now_data,
        prev_data,
        change_only=args.change_only,
        verbose=args.verbose,
        short=args.short or args.change_append,
        olddiff=args.olddiff,
    )
    if args.change_append:
        report += report_todo_tasks(
            now_data,
            prev_data,
            change_only=True,
            verbose=args.verbose,
            short=False,
            olddiff=args.olddiff,
        )
    report += report_statuses(
        now_data,
        prev_data,
        change_only=args.change_only,
        verbose=args.verbose,
        short=args.short or args.change_append,
        olddiff=args.olddiff,
    )
    if args.change_append:
        report += report_statuses(
            now_data,
            prev_data,
            change_only=True,
            verbose=args.verbose,
            short=False,
            olddiff=args.olddiff,
        )
    report += report_hints(
        now_data,
        prev_data,
        change_only=args.change_only or args.short or args.change_append,
        verbose=args.verbose,
    )

    if args.shownote:
        report += "-- 说明 --\n"
        with open("blueberry说明.txt", "r", encoding="utf-8") as g:
            report += g.read() + "\n\n"

    if not args.nologging:
        if not os.path.exists("data"):
            os.makedirs("data")
        with open(f"data/{tmark}.json", "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
        with open(f"data/{tmark}.txt", "w", encoding="utf-8") as f:
            f.write(report)

    print(report)


if __name__ == "__main__":
    main()
