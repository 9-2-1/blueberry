from typing import Any, TypeVar, Union
from datetime import time as datetime_time
import warnings

from pydantic import BaseModel
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .models import (
    AppendOnlyModel,
    DeleteModel,
    TaskModel,
    ProgressModel,
    StatusModel,
    TodoModel,
    HintModel,
    WorktimeModel,
)

# openpyxl
warnings.simplefilter(action="ignore", category=UserWarning)

T = TypeVar("T")


class Data(BaseModel):
    任务: list[Union[TaskModel, DeleteModel]]
    进度: list[ProgressModel]
    状态: list[Union[StatusModel, DeleteModel]]
    待办事项: list[Union[TodoModel, DeleteModel]]
    提示: list[HintModel]
    工作时段: list[WorktimeModel] = [
        WorktimeModel(开始=datetime_time(hour=0), 结束=datetime_time(hour=0))
    ]


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
) -> list[Union[AppendOnlyModel, DeleteModel]]:
    parsed_table = parse_table(table)
    ret: list[Union[AppendOnlyModel, DeleteModel]] = []
    for x in parsed_table:
        if set(x.keys()) == {"名称", "时间"}:
            ret.append(DeleteModel(**x))
        else:
            ret.append(datatype(**x))
    return ret


def load_data(workbook: str) -> Data:
    wb = load_workbook(workbook)
    任务 = parse_append_only_table(wb["任务"], TaskModel)
    进度 = parse_model_table(wb["进度"], ProgressModel)
    状态 = parse_append_only_table(wb["状态"], StatusModel)
    待办事项 = parse_append_only_table(wb["待办事项"], TodoModel)
    提示 = parse_model_table(wb["提示"], HintModel)
    工作时段 = [WorktimeModel(开始=datetime_time(hour=0), 结束=datetime_time(hour=0))]
    if "工作时段" in wb.sheetnames:
        工作时段 = parse_model_table(wb["工作时段"], WorktimeModel)
    return Data(
        状态=状态, 任务=任务, 进度=进度, 待办事项=待办事项, 提示=提示, 工作时段=工作时段
    )
