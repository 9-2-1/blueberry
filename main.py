from typing import Literal, Any, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta, time as datetime_time
from textwrap import indent, wrap
import math

from rich import inspect, traceback as rich_traceback
from rich.pretty import pprint
from pydantic import BaseModel, ConfigDict
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

rich_traceback.install()


class AppendOnly(BaseModel):
    """
    记录表中共有的两列，一列代表记录的名称，一列代表记录添加、更新或删除的时间。
    """

    名称: str
    时间: datetime


class DeleteModel(AppendOnly):
    """
    代表“删除”的记录行。
    在“时间”删除名为“名称”的行。
    """

    名称: str
    时间: datetime


class TaskModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标题: str
    描述: str | None = None
    开始: datetime
    结束: datetime
    总数: float | None = None


class ProgressModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    时间: datetime
    名称: str
    # ---
    进度: float = 0.0
    用时: timedelta = timedelta(0)
    分数: float | None = None
    描述: str | None = None


class StatusModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标题: str
    描述: str | None = None
    点数: float | None = None  # 点数为None意味着这是一个“取消之前状态”的记录。
    开始: datetime | None = None
    结束: datetime | None = None


class TodoModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    delete: bool = False
    # ---
    标记: Literal["+", "*", "-"] | None = None  # + 未开始，* 继续，- 等待
    标题: str
    描述: str | None = None
    点数: float = 0.0
    开始: datetime | None = None
    结束: datetime | None = None
    完成: datetime | None = None


class HintModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    时间: datetime
    # ---
    标题: str
    描述: str | None = None


AppendOnlyModel = TypeVar("AppendOnlyModel", bound=AppendOnly)
T = TypeVar("T")


def parse_table(table: Worksheet) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys: list[str] = []
    for row in table.iter_rows(min_row=1):
        for cell in row:
            keys.append(str(cell.value))
    for row in table.iter_rows(min_row=2):
        row_: dict[str, Any] = {}
        for i, cell in enumerate(row):
            if cell.value is None:
                continue
            row_[keys[i]] = cell.value
        if row_:
            rows.append(row_)
    return rows


def parse_model_table(table: Worksheet, datatype: type[T]) -> list[T]:
    parsed_table = parse_table(table)
    ret: list[T] = []
    for x in parsed_table:
        ret.append(datatype(**x))
    return ret


def parse_append_only_table(
    table: Worksheet, datatype: type[AppendOnlyModel]
) -> list[AppendOnlyModel | DeleteModel]:
    parsed_table = parse_table(table)
    ret: list[AppendOnlyModel | DeleteModel] = []
    for x in parsed_table:
        if set(x.keys()) == {"名称", "时间"}:
            ret.append(DeleteModel(**x))
        else:
            ret.append(datatype(**x))
    return ret


class Data(BaseModel):
    任务: list[TaskModel | DeleteModel]
    进度: list[ProgressModel]
    状态: list[StatusModel | DeleteModel]
    待办事项: list[TodoModel | DeleteModel]
    提示: list[HintModel]


class State(BaseModel):
    任务: dict[str, TaskModel]
    进度: dict[str, list[ProgressModel]]
    状态: dict[str, StatusModel]
    待办事项: dict[str, TodoModel]
    提示: list[HintModel]


def mark_delete(x: dict[str, Any]) -> dict[str, Any]:
    if len(set(x.keys()) - {"名称", "时间"}) == 0:
        x["delete"] = True
    return x


def load_data() -> Data:
    wb = load_workbook("记录.xlsx")
    任务 = parse_append_only_table(wb["任务"], TaskModel)
    进度 = parse_model_table(wb["进度"], ProgressModel)
    状态 = parse_append_only_table(wb["状态"], StatusModel)
    待办事项 = parse_append_only_table(wb["待办事项"], TodoModel)
    提示 = parse_model_table(wb["提示"], HintModel)
    return Data(状态=状态, 任务=任务, 进度=进度, 待办事项=待办事项, 提示=提示)


def collect_lines(
    lines: list[AppendOnlyModel | DeleteModel], now_time: datetime
) -> dict[str, AppendOnlyModel]:
    lines = sorted(lines, key=lambda x: x.时间)
    state: dict[str, AppendOnlyModel] = {}
    for line in lines:
        if line.时间 >= now_time:
            continue
        if isinstance(line, DeleteModel):
            del state[line.名称]
        else:
            state[line.名称] = line
    return state


def collect_progress(
    progress: list[ProgressModel], now_time: datetime
) -> dict[str, list[ProgressModel]]:
    progress = sorted(progress, key=lambda x: x.时间)
    state: dict[str, list[ProgressModel]] = {}  # list of progress nodes
    for line in progress:
        if line.时间 >= now_time:
            continue
        if line.名称 in state:
            state[line.名称].append(line)
        else:
            state[line.名称] = [line]
    return state


def collect_hints(lines: list[HintModel], now_time: datetime) -> list[HintModel]:
    lines = sorted(lines, key=lambda x: x.时间)
    return [x for x in lines if x.时间 <= now_time]


def collect_state(data: Data, now_time: datetime) -> State:
    return State(
        任务=collect_lines(data.任务, now_time),
        进度=collect_progress(data.进度, now_time),
        状态=collect_lines(data.状态, now_time),
        待办事项=collect_lines(data.待办事项, now_time),
        提示=collect_hints(data.提示, now_time),
    )


def deltafmt_unsigned(delta: timedelta) -> str:
    if delta > timedelta(days=7):
        return f"{delta // timedelta(days=1)}d"
    elif delta > timedelta(days=1):
        return f"{delta // timedelta(days=1)}d{delta // timedelta(hours=1) % 24}h"
    elif delta > timedelta(hours=1):
        return f"{delta // timedelta(hours=1)}h{delta // timedelta(minutes=1) % 60}m"
    else:
        return f"{delta.seconds // 60}min"


def deltafmt_signed(delta: timedelta) -> str:
    if delta > timedelta(minutes=1):
        return f"+{deltafmt_unsigned(delta)}"
    elif delta < timedelta(minutes=-1):
        return f"-{deltafmt_unsigned(-delta)}"
    else:
        return f"现在"


def timefmt(t: datetime, now: datetime) -> str:
    if t.date() == now.date():
        timestr = t.strftime("%H:%M")
    else:
        timestr = t.strftime("%m/%d %H:%M")
    delta = t - now
    timestr += f" ({deltafmt_signed(delta)})"
    return timestr


def pointfmt(p: float) -> str:
    p_i = math.floor(p + 0.5)
    if p_i == 0:
        return "0"
    else:
        return f"{p_i:+g}"


def main() -> None:
    data = load_data()
    tmark = datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(f"data/{tmark}.json", "w", encoding="utf-8") as f:
        f.write(data.model_dump_json(indent=2))
    now_time = datetime.now()
    prev_time = datetime.combine(datetime.today(), datetime_time(0, 0))

    now_state = collect_state(data, now_time)
    prev_state = collect_state(data, prev_time)

    # Goldie点数 = 任务 + 状态 + 其他任务完成
    # 任务
    @dataclass
    class TaskEstimate:
        速度: float  # per hour
        采样进度: float
        采样用时: timedelta
        每日用时: timedelta
        预计完成时间: timedelta
        预计可用时间: timedelta
        差距: timedelta
        点数: float = 0.0
        # * 进行中 - 等待开始 = 已完成 ! 已超时

    @dataclass
    class TaskStats:
        进度: float | None = None
        标记: Literal["*", "-", "=", "!"] = "*"
        估计: TaskEstimate | None = None

    主要点数 = 0.0
    task_stats: dict[str, TaskStats] = {}
    总每日用时 = timedelta(0)
    for task in now_state.任务.values():
        task_stats[task.名称] = TaskStats()
        # 标记
        if now_time < task.开始:
            task_stats[task.名称].标记 = "-"
        elif now_time > task.结束:
            task_stats[task.名称].标记 = "!"
        else:
            task_stats[task.名称].标记 = "*"
        if task.总数 is None:
            print(f"任务 {task.标题} 没有总数。需要确认总数才能正常估计进度。")
            continue
        progress = now_state.进度.get(task.名称, None)
        if progress is None:
            print(f"任务 {task.标题} 没有开始。需要完成一部分才能正常估计进度。")
            continue
        current = progress[-1]
        task_stats[task.名称].进度 = current.进度
        if current.进度 >= task.总数:
            task_stats[task.名称].标记 = "="
        # 速度
        # 近期记录
        MIN_TIME = timedelta(hours=2)
        MIN_COUNT = 3
        new_time = now_time
        # old_time = ?
        tot_time = timedelta(0)
        new_progress = current.进度
        # old_progress = ?
        found = False
        count = 0
        for p in reversed(progress):
            old_time = p.时间
            tot_time += p.用时
            old_progress = p.进度
            if p.用时 != timedelta(0):
                count += 1
            if tot_time > MIN_TIME and count > MIN_COUNT:
                found = True
                break
        if not found:
            old_time = task.开始
            old_progress = 0.0
        if tot_time == timedelta(0):
            print(f"任务 {task.标题} 没有开始。需要完成一部分才能正常估计进度。")
            continue
        采样进度 = new_progress - old_progress
        采样用时 = tot_time
        速度 = 采样进度 / (采样用时 / timedelta(hours=1))
        每日用时 = tot_time / ((new_time - old_time) / timedelta(days=1))
        # 预计完成时间
        预计完成时间 = timedelta(hours=1) * (task.总数 - current.进度) / 速度
        # 预计可用时间
        预计可用时间 = (task.结束 - now_time) / timedelta(days=1) * 每日用时
        # 差距
        差距 = 预计可用时间 - 预计完成时间
        estimate = TaskEstimate(
            速度=速度,
            采样进度=采样进度,
            采样用时=采样用时,
            每日用时=每日用时,
            预计完成时间=预计完成时间,
            预计可用时间=预计可用时间,
            差距=差距,
        )
        task_stats[task.名称].估计 = estimate
        总每日用时 += 每日用时
    for stats in task_stats.values():
        if stats.估计 is not None:
            # 点数
            stats.估计.点数 = stats.估计.差距 / 总每日用时 * 100
            主要点数 += stats.估计.点数

    # 状态点数
    状态点数 = 0.0
    for status in now_state.状态.values():
        if status.点数 is None:
            continue
        if status.开始 is not None and status.开始 > now_time:
            continue
        if status.结束 is not None and status.结束 < now_time:
            continue
        状态点数 += status.点数

    # 筛选近三天已完成
    todo_finished = [
        x
        for x in now_state.待办事项.values()
        if x.完成 is not None and x.完成 > now_time - timedelta(days=3)
    ]
    todo_finished = sorted(
        todo_finished,
        key=lambda x: x.完成 if x.完成 is not None else datetime.max,
        reverse=True,
    )
    # 其他任务点数
    其他任务点数 = 0.0
    for todo in todo_finished:
        其他任务点数 += todo.点数

    with open(f"data/{tmark}.txt", "w", encoding="utf-8") as f:

        def write(s: str) -> None:
            print(s)
            print(s, file=f)

        write("-- 总览 --")
        write(now_time.strftime("%m/%d %H:%M"))
        write(f"Goldie点数: {pointfmt(主要点数 + 状态点数 + 其他任务点数)}")
        write(f"- 主要: {pointfmt(主要点数)}")
        write(f"- 状态: {pointfmt(状态点数)}")
        write(f"- 其他任务: {pointfmt(其他任务点数)}")
        write("")

        write("-- 主要任务 --")
        # 8小时(时长) * 80%(工作-休息比) ≈ 6.5小时
        推荐用时 = timedelta(hours=6.5)
        write(
            f"平均每日: {deltafmt_unsigned(总每日用时)} (推荐用时的 {总每日用时 / 推荐用时 :.0%})"
        )
        for task in now_state.任务.values():
            tstats = task_stats.get(task.名称, None)
            mark = "?"
            点数str = ""
            if tstats is not None:
                mark = tstats.标记
                if tstats.估计 is not None:
                    点数str = f" [{pointfmt(tstats.估计.点数)}]"
            write(
                f"{mark}{点数str} {task.标题} 开始: {timefmt(task.开始, now_time)} 结束: {timefmt(task.结束, now_time)}"
            )
            if (
                tstats is not None
                and tstats.估计 is not None
                and tstats.进度 is not None
                and task.总数 is not None
            ):
                write(
                    f"  > 已完成: {tstats.进度:g}/{task.总数:g} ({tstats.进度/task.总数:.0%}) 预计完成时间: {deltafmt_signed(tstats.估计.预计完成时间)}"
                )
                # write(
                #     f"  > 速度: {tstats.估计.速度:.3g}/h 采样进度: {tstats.估计.采样进度:g} 采样用时: {deltafmt_signed(tstats.估计.采样用时)}"
                # )
                write(
                    f"  > 平均每日用时: {deltafmt_signed(tstats.估计.每日用时)} 预计可用时间: {deltafmt_signed(tstats.估计.预计可用时间)} 差距: {deltafmt_signed(tstats.估计.差距)}"
                )
            elif task.总数 is not None:
                write(f"  > 已完成: 0/{task.总数:g} (0%)")
            if task.描述 is not None:
                write(indent(task.描述, "    "))
            write("")

        write("-- 其他任务 --")
        for mark, title in [
            ("*", "继续"),
            ("+", "可以进行"),
            ("-", "等待"),
        ]:
            todos = [
                x
                for x in now_state.待办事项.values()
                if x.标记 == mark and x.完成 is None
            ]
            if todos:
                write(f"{title}:")
                todos = sorted(
                    todos, key=lambda x: x.开始 if x.开始 is not None else datetime.max
                )
                for todo in todos:
                    write(
                        f"{mark} (预计{pointfmt(todo.点数)}) {todo.标题}"
                        + (
                            " 开始: " + timefmt(todo.开始, now_time)
                            if todo.开始 is not None
                            else ""
                        )
                        + (
                            " 结束: " + timefmt(todo.结束, now_time)
                            if todo.结束 is not None
                            else ""
                        )
                    )
                    if todo.描述 is not None:
                        write(indent(todo.描述, "    "))
                    write("")
        if todo_finished:
            write("最近完成:")
            for todo in todo_finished:
                write(
                    f"= [{pointfmt(todo.点数)}] {todo.标题}"
                    + (
                        " 开始: " + timefmt(todo.开始, now_time)
                        if todo.开始 is not None
                        else ""
                    )
                    + (
                        " 结束: " + timefmt(todo.结束, now_time)
                        if todo.结束 is not None
                        else ""
                    )
                    + (
                        " 完成: " + timefmt(todo.完成, now_time)
                        if todo.完成 is not None
                        else ""
                    )
                )
                if todo.描述 is not None:
                    write(indent(todo.描述, "    "))
                write("")

        write("-- 提示 --")
        hints = reversed(now_state.提示)
        # 只显示最近一段时间或者最近几条提示
        MAX_HINTS = 5
        MAX_HINTS_TIME = timedelta(days=1)
        hints_n = 0
        for hint in hints:
            if hints_n >= MAX_HINTS and hint.时间 < now_time - MAX_HINTS_TIME:
                break
            hints_n += 1
            write(f"o {hint.标题} {timefmt(hint.时间, now_time)}")
            if hint.描述 is not None:
                write(indent(hint.描述, "    "))
        write("")

        write("-- 状态 --")
        for status in now_state.状态.values():
            if status.点数 is None:
                continue
            if status.开始 is not None and status.开始 > now_time:
                continue
            if status.结束 is not None and status.结束 < now_time:
                continue
            if status.点数 > 0:
                mark = "+"
            elif status.点数 < 0:
                mark = "-"
            else:
                mark = "o"
            write(
                f"{mark} [{pointfmt(status.点数)}] {status.标题}"
                + (
                    " 开始: " + timefmt(status.开始, now_time)
                    if status.开始 is not None
                    else ""
                )
                + (
                    " 结束: " + timefmt(status.结束, now_time)
                    if status.结束 is not None
                    else ""
                )
            )
            if status.描述 is not None:
                write(indent(status.描述, "    "))
        write("")

        # write("-- 今日进度 --")
        # write("T: XX:XX / ? (XX%)")
        # write("X: (点数+X->+Y) Title +X +AA:AA")
        # write("[WIP]")
        # write("")

        # write("-- 昨日进度 --")
        # write("T: XX:XX / ? (XX%)")
        # write("X: (点数+X->+Y) Title +X +AA:AA")
        # write("[WIP]")
        # write("")


if __name__ == "__main__":
    main()
