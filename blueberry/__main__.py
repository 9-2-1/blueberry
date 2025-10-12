import argparse
import logging
import os
import time
import traceback
from datetime import timedelta

import dateparser

from .parser import load_data, Data
from .collect import collect_state
from .statistic import statistic
from .planner import planner, PlanData
from .webserver import live_server
from .report_base import report_head, report_plan_head, report_worktime, ReportData
from .report_task import report_long_tasks, report_short_tasks
from .report_diff import report_tasks_diff
from .report_plan import report_tasks_plan
from .ctz_now import ctz_now

log = logging.getLogger(__name__)


def get_report_and_write(data: Data, args: argparse.Namespace) -> str:
    now_time = ctz_now()
    if args.time is not None:
        now_time = args.time

    yesterday_time = now_time.replace(hour=0, minute=0, second=0)
    tomorrow_time = yesterday_time + timedelta(days=1)

    if args.from_ is not None:
        prev_time = args.from_
    elif args.daily:
        prev_time = yesterday_time
    else:
        prev_time = None

    if args.end is not None:
        end_time = args.end
    elif args.daily:
        end_time = tomorrow_time
    else:
        end_time = None

    now_state = collect_state(data, now_time)
    now_stats = statistic(now_state, now_time)
    now_data = ReportData(now_time, now_state, now_stats)

    report = report_head(now_data) + "\n"
    report += report_worktime(now_data) + "\n"
    if prev_time:
        prev_state = collect_state(data, prev_time)
        prev_stats = statistic(prev_state, prev_time)
        prev_data = ReportData(prev_time, prev_state, prev_stats)
        if end_time:
            plan = planner(
                PlanData(now_time, now_state, now_stats),
                PlanData(prev_time, prev_state, prev_stats),
                end_time,
                data.工作时段,
            )
            report += report_plan_head(plan, now_time) + "\n\n"
            report += report_tasks_plan(
                now_data,
                prev_data,
                plan,
                end_time,
                total_str="今日总数" if args.daily else "总数",
            )
        else:
            report += "\n"
            report += report_tasks_diff(
                now_data,
                prev_data,
                hide_decay=args.change,
                total_str="今日总数" if args.daily else "总数",
            )
    else:
        report += report_long_tasks(now_data) + "\n\n"
        report += report_short_tasks(now_data)

    if args.output is not None:
        with open(f"{args.output}.json", "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
        with open(f"{args.output}", "w", encoding="utf-8") as f:
            f.write(report)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    # 基本参数
    parser.add_argument("-W", "--watch", action="store_true", help="保持显示并自动更新")
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
        "-e",
        "--end",
        action="store",
        type=dateparser.parse,
        help="结束时间(可选)",
    )
    parser.add_argument("-d", "--daily", action="store_true", help="显示每日建议数量")
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
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试信息")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif args.live:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.live:
        live_server(args.workbook, host=args.host, port=args.port)
        return

    if args.watch:
        try:
            ESC = "\033"
            HIDECURSOR = ESC + "[?25l"
            SHOWCURSOR = ESC + "[?25h"
            HOME = ESC + "[H"
            CLTEOL = ESC + "[K"
            CLTEOS = ESC + "[J"
            print(HIDECURSOR, end="")
            fstat = os.stat(args.workbook)
            last_mtime = 0.0
            last_report_time = 0.0
            data = None
            while True:
                try:
                    fstat = os.stat(args.workbook)
                    if (
                        fstat.st_mtime != last_mtime
                        or last_report_time is None
                        or time.time() - last_report_time > 3600
                    ):
                        data = load_data(args.workbook)
                        last_mtime = fstat.st_mtime
                        last_report_time = 0.0
                    assert data is not None
                    if last_report_time == 0.0 or time.time() - last_report_time > 300:
                        last_report_time = time.time()
                        report = get_report_and_write(data, args)
                        print(
                            HOME + report.replace("\n", CLTEOL + "\n"),
                            end=CLTEOS,
                            flush=True,
                        )
                except Exception as e:
                    log.error(e)
                    print(
                        HOME + traceback.format_exc().replace("\n", CLTEOL + "\n"),
                        end=CLTEOS,
                        flush=True,
                    )
                    if isinstance(e, KeyboardInterrupt):
                        raise
                time.sleep(1)
        except KeyboardInterrupt:
            return
        finally:
            print(SHOWCURSOR, end="")

    data = load_data(args.workbook)
    report = get_report_and_write(data, args)

    print(report)


if __name__ == "__main__":
    main()
