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


class TaskModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标题: str
    描述: Optional[str] = None
    开始: datetime
    结束: datetime
    总数: Optional[float] = None


class ProgressModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    时间: datetime
    名称: str
    # ---
    进度: float = 0.0
    用时: timedelta = timedelta(0)
    描述: Optional[str] = None


class StatusModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标题: str
    描述: Optional[str] = None
    点数: Optional[int] = None  # 点数为None意味着这是一个“取消之前状态”的记录。
    开始: Optional[datetime] = None
    结束: Optional[datetime] = None


class TodoModel(AppendOnly):
    model_config = ConfigDict(extra="forbid")
    名称: str
    时间: datetime
    # ---
    标记: Optional[Literal["+", "*", "-"]] = None  # + 可选，* 重要，- 等待
    标题: str
    描述: Optional[str] = None
    点数: int = 0
    开始: Optional[datetime] = None
    结束: Optional[datetime] = None
    完成: Optional[datetime] = None


class HintModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    时间: datetime
    # ---
    标题: str
    描述: Optional[str] = None


class WorktimeModel(BaseModel):
    开始: datetime_time
    结束: datetime_time


AppendOnlyModel = TypeVar("AppendOnlyModel", bound=AppendOnly)
