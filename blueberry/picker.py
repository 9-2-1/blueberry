from typing import TypeVar, Iterable

from .models import PickerModel, AppendOnly

T = TypeVar("T", bound=AppendOnly)


def isdisabled(task_name: str, preference: list[PickerModel]) -> bool:
    for picker in preference:
        if task_name == picker.名称:
            if picker.禁用 == "-":
                return True
    return False


def priority(item: T, preference: list[PickerModel]) -> int:
    for i, picker in enumerate(preference):
        if item.名称 == picker.名称:
            return i
    return len(preference)


def prefer(items: Iterable[T], preference: list[PickerModel]) -> list[T]:
    filtered_items = filter(lambda x: not isdisabled(x.名称, preference), items)
    sorted_items = sorted(filtered_items, key=lambda x: priority(x, preference))
    return sorted_items
