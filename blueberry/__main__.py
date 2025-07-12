from datetime import datetime
import os
import argparse

import dateparser

from .parser import load_data
from .collect import collect_state
from .statistic import statistic
from .webserver import live_server
from .report import (
    report_head,
    report_worktime,
    report_main_tasks,
    report_daily_time,
    report_todo_tasks,
    report_statuses,
    report_hints,
    ReportData,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    # 基本参数
    parser.add_argument(
        "-l", "--live", action="store_true", help="开启实时点数显示HTTP网页"
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
    # 格式
    parser.add_argument("-c", "--changes", action="store_true", help="只显示变化")
    parser.add_argument("-d", "--daily", action="store_true", help="显示今日完成")
    parser.add_argument("-s", "--short", action="store_true", help="简单格式")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细格式")
    parser.add_argument(
        "-u", "--upcoming-days", type=float, help="隐藏 UPCOMING_DAYS 天后开始的项目"
    )
    # 详细格式设定
    parser.add_argument(
        "-D",
        "--olddiff",
        action="store_true",
        help="使用 旧→新 格式，不用 新(±变化) 格式",
    )
    parser.add_argument("-I", "--no-info", action="store_true", help="不显示说明")
    parser.add_argument("-o", "--output", action="store", help="输出文件路径")
    args = parser.parse_args()

    if args.live:
        live_server(args.workbook)
        return

    data = load_data(args.workbook)
    tmark = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.time is not None:
        now_time = args.time
    else:
        now_time = datetime.now()
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

    yesterday_state = collect_state(data, yesterday_time)
    yesterday_stats = statistic(yesterday_state, yesterday_time)
    yesterday_data = ReportData(yesterday_time, yesterday_state, yesterday_stats)

    prev_data = None
    if prev_time is not None:
        prev_state = collect_state(data, prev_time)
        prev_stats = statistic(prev_state, prev_time)
        prev_data = ReportData(prev_time, prev_state, prev_stats)

    keyword = ""
    if args.short:
        keyword += "简单"
    elif args.verbose:
        keyword += "详细"
    if args.changes:
        keyword += "变化"
    report = f"Blueberry {keyword}报告\n"
    report += (
        report_head(
            now_data,
            prev_data,
            yesterday_data if args.daily else None,
            olddiff=args.olddiff,
        )
        + "\n\n"
    )
    report += report_worktime(now_data) + "\n\n"

    report_main_tasks_strs: list[str] = []
    if args.changes:
        report_main_tasks_strs.append(
            report_main_tasks(
                now_data,
                prev_data,
                yesterday_data if args.daily else None,
                change_only=True,
                verbose=args.verbose,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
        report_main_tasks_strs.append(
            report_main_tasks(
                now_data,
                prev_data,
                yesterday_data if args.daily else None,
                minor_change_only=True,
                short=True,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    else:
        report_main_tasks_strs.append(
            report_main_tasks(
                now_data,
                prev_data,
                yesterday_data if args.daily else None,
                verbose=args.verbose,
                short=args.short,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    if args.daily:
        report_main_tasks_strs.append(
            report_daily_time(
                now_data,
                prev_data,
                yesterday_data if args.daily else None,
                olddiff=args.olddiff,
            )
        )
    report_main_tasks_strs = [x for x in report_main_tasks_strs if x != ""]
    if report_main_tasks_strs:
        if args.changes:
            report += "-- 主要任务变化 --\n"
        else:
            report += "-- 主要任务 --\n"
        report += "\n\n".join(report_main_tasks_strs) + "\n\n"

    report_todo_tasks_strs: list[str] = []
    if args.changes:
        report_todo_tasks_strs.append(
            report_todo_tasks(
                now_data,
                prev_data,
                change_only=True,
                verbose=args.verbose,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
        report_todo_tasks_strs.append(
            report_todo_tasks(
                now_data,
                prev_data,
                minor_change_only=True,
                short=True,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    else:
        report_todo_tasks_strs.append(
            report_todo_tasks(
                now_data,
                prev_data,
                verbose=args.verbose,
                short=args.short,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    report_todo_tasks_strs = [x for x in report_todo_tasks_strs if x != ""]
    if report_todo_tasks_strs:
        if args.changes:
            report += "-- 其他任务变化 --\n"
        else:
            report += "-- 其他任务 --\n"
        report += "\n\n".join(report_todo_tasks_strs) + "\n\n"

    report_hints_str = report_hints(
        now_data,
        prev_data,
        change_only=args.changes or args.short,
        verbose=args.verbose,
    )
    if report_hints_str != "":
        report += "-- 提示 --\n"
        report += report_hints_str + "\n\n"

    report_statuses_strs: list[str] = []
    if args.changes:
        report_statuses_strs.append(
            report_statuses(
                now_data,
                prev_data,
                change_only=True,
                verbose=args.verbose,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
        report_statuses_strs.append(
            report_statuses(
                now_data,
                prev_data,
                minor_change_only=True,
                short=True,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    else:
        report_statuses_strs.append(
            report_statuses(
                now_data,
                prev_data,
                verbose=args.verbose,
                short=args.short,
                upcoming=args.upcoming_days,
                olddiff=args.olddiff,
            )
        )
    report_statuses_strs = [x for x in report_statuses_strs if x != ""]
    if report_statuses_strs:
        if args.changes:
            report += "-- 状态变化 --\n"
        else:
            report += "-- 状态 --\n"
        report += "\n\n".join(report_statuses_strs) + "\n\n"

    if not (args.short or args.changes or args.no_info):
        report += "-- 说明 --\n"
        with open("blueberry说明.txt", "r", encoding="utf-8") as g:
            report += g.read() + "\n\n"

    if args.output is not None:
        with open(f"{args.output}.json", "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
        with open(f"{args.output}.txt", "w", encoding="utf-8") as f:
            f.write(report)

    print(report)


if __name__ == "__main__":
    main()
