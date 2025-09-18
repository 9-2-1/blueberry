from typing import TypeVar, Literal, Optional
from datetime import datetime, timedelta


FmtT = TypeVar("FmtT", int, float, datetime, timedelta, str)


def fmt(
    x: FmtT,
    *,
    pos: bool = False,
    p2: bool = False,
) -> str:
    if isinstance(x, int):
        if pos and x != 0:
            return f"{x:+d}"
        else:
            return f"{x:d}"
    elif isinstance(x, float):
        if p2:
            if pos and x != 0.0:
                return f"{x:+.2f}"
            else:
                return f"{x:.2f}"
        else:
            if pos and x != 0.0:
                return f"{x:+g}"
            else:
                return f"{x:g}"
    elif isinstance(x, datetime):
        if pos:
            raise TypeError("datetime无符号")
        else:
            return x.strftime("%m/%d %H:%M")
    elif isinstance(x, timedelta):
        sign = ""
        if x >= timedelta(0):
            if pos and x != timedelta(0):
                sign = "+"
            v = x
        else:
            sign = "-"
            v = -x
        if v > timedelta(days=7):
            vstr = f"{v // timedelta(days=1)}d"
        elif v > timedelta(days=1):
            vstr = f"{v // timedelta(days=1)}d{v // timedelta(hours=1) % 24}h"
        elif v > timedelta(hours=1):
            vstr = f"{v // timedelta(hours=1)}h{v // timedelta(minutes=1) % 60}m"
        elif v > timedelta(minutes=1):
            vstr = f"{v // timedelta(minutes=1)}m"
        else:
            vstr = "0 "
        return sign + vstr
    elif isinstance(x, str):
        return x
    else:
        raise TypeError("未知类型")


ColorMode = Literal["goldie", "shadowzero", "goldiechange", "highlightreach"]


def colorit(
    value: FmtT,
    *,
    colorpts: Optional[int] = None,
    colorchange: Optional[int] = None,
    greyzero: bool = False,
    grey: bool = False,
    blue: bool = False,
    red: bool = False,
) -> str:
    pstr = fmt(value)
    if colorpts is not None:
        color = goldie_color(colorpts)
        pstr = f"{ESC}[{color}m{pstr}{ESC}[0m"
    if colorchange is not None:
        color = goldie_change_color(colorchange)
        pstr = f"{ESC}[{color}m{pstr}{ESC}[0m"
    if greyzero:
        if isinstance(value, str):
            try:
                fv = float(value)
                if fv == 0.0:
                    pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
            except ValueError:
                pass
        elif value in {0, 0.0, timedelta(0)}:
            pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
    if grey:
        pstr = f"{ESC}[{DARKGREY}m{pstr}{ESC}[0m"
    if blue:
        pstr = f"{ESC}[{BLUE}m{pstr}{ESC}[0m"
    if red:
        pstr = f"{ESC}[{RED}m{pstr}{ESC}[0m"
    return pstr


ESC = "\033"
RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
MAGENTA = "35"
CYAN = "36"
WHITE = "37"
ORANGE = "38;5;130"
DARKGREY = "90"

goldie_thresholds = [-100, -50, 0, 50, 100]
goldie_levels = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE]


def goldie_color(goldie: int) -> str:
    for i, threshold in enumerate(goldie_thresholds):
        if goldie < threshold:
            return goldie_levels[i]
    return goldie_levels[-1]


goldie_change_thresholds = [-50, -20, 0, 1, 20, 50]
goldie_change_levels = [RED, ORANGE, YELLOW, DARKGREY, GREEN, CYAN, BLUE]


def goldie_change_color(goldie: int) -> str:
    for i, threshold in enumerate(goldie_change_thresholds):
        if goldie < threshold:
            return goldie_change_levels[i]
    return goldie_change_levels[-1]
