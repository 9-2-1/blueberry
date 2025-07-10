from typing import Literal, TypeVar
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
    描述: str | None = None


class StatusModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标题: str
    描述: str | None = None
    点数: int | None = None  # 点数为None意味着这是一个“取消之前状态”的记录。
    开始: datetime | None = None
    结束: datetime | None = None


class TodoModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标记: Literal["+", "*", "-"] | None = None  # + 未开始，* 继续，- 等待
    标题: str
    描述: str | None = None
    点数: int = 0
    开始: datetime | None = None
    结束: datetime | None = None
    完成: datetime | None = None


class HintModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    时间: datetime
    # ---
    标题: str
    描述: str | None = None


class WorktimeModel(BaseModel):
    开始: datetime_time
    结束: datetime_time


AppendOnlyModel = TypeVar("AppendOnlyModel", bound=AppendOnly)
