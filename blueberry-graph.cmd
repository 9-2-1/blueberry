@echo off
echo �������ɽ�30�� Goldie �����仯����ͼ...
call conda run --no-capture-output -n blueberry python test_graph.py
if ERRORLEVEL 1 pause
start goldie_points_trend.png
