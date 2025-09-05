from typing import Literal, TypeVar, Optional
from datetime import datetime, timedelta, time as datetime_time

from pydantic import BaseModel, ConfigDict


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


class LongTaskModel(AppendOnly):
    名称: str
    时间: datetime
    # ---
    标题: str
    最晚结束: datetime
    最晚开始: datetime
    总数: float


class ProgressModel(BaseModel):
    时间: datetime
    名称: str
    # ---
    进度: float = 0.0
    用时: timedelta = timedelta(0)


class ShortTaskModel(AppendOnly):
    名称: str
    时间: datetime
    # ---
    标题: str
    最晚结束: datetime
    预计用时: timedelta
    最早开始: datetime
    完成: Optional[datetime] = None
    用时: Optional[timedelta] = None


class WorktimeModel(BaseModel):
    开始: datetime_time
    结束: datetime_time


class PickerModel(BaseModel):
    名称: str
    禁用: Optional[Literal["-"]] = None


AppendOnlyModel = TypeVar("AppendOnlyModel", bound=AppendOnly)
