@echo off
echo �������ɽ�30�� Goldie �����仯����ͼ...
call conda run --no-capture-output -n blueberry python -m blueberry.graph_point
if ERRORLEVEL 1 pause
start goldie_points_trend.png
start loads_trend.png