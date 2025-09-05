@chcp 65001 > nul
@set /p oldt=上一个报告的时间:
@call blueberry.cmd -c -f "%oldt%"
