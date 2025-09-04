from datetime import datetime
from typing import Union

from pydantic import BaseModel

from .models import (
    AppendOnlyModel,
    DeleteModel,
    TaskModel,
    ProgressModel,
    TodoModel,
    WorktimeModel,
    PickerModel,
)

from .parser import Data


class State(BaseModel):
    任务: dict[str, TaskModel]
    进度: dict[str, list[ProgressModel]]
    待办事项: dict[str, TodoModel]
    工作时段: list[WorktimeModel]
    选择排序偏好: list[PickerModel]


def collect_lines(
    lines: list[Union[AppendOnlyModel, DeleteModel]], now_time: datetime
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


def collect_state(data: Data, now_time: datetime) -> State:
    return State(
        任务=collect_lines(data.任务, now_time),
        进度=collect_progress(data.进度, now_time),
        待办事项=collect_lines(data.待办事项, now_time),
        工作时段=data.工作时段,
        选择排序偏好=data.选择排序偏好,
    )
