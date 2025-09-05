@echo off
echo 正在生成近30天 Goldie 点数变化折线图...
call conda run --no-capture-output -n blueberry python -m blueberry.graph_point
if ERRORLEVEL 1 pause
start goldie_points_trend.png
start loads_trend.png